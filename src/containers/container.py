import json
import logging
from io import BytesIO
from pathlib import Path
from time import sleep
from typing import Optional

import pexpect
from pexpect import ExceptionPexpect, popen_spawn

from src.containers.exceptions import (BootFailure, PortAllocationError,
                                       gen_boot_exception)
from src.containers.port_allocation import allocate_port
from src.system import ssh, syspath


class Container:
    """
    Class for storing container objects

    :param booter: Popen that stores the boot of the instance
    :param ex_port: The ssh port of the system
    :param arch: The arch of the container
    """

    logger: logging.Logger
    booter: Optional[popen_spawn.PopenSpawn] = None
    ex_port: int
    name: str
    arch: str = "x86_64"
    config: dict
    sshi: ssh.SSHInterface
    username: str = "root"
    password: str = "root"
    timeout: int = 360
    max_retries: int = 25
    logging_file_path: str = "pexpect.log"
    logging_file: BytesIO

    def __init__(self, name: str, logger: logging.Logger) -> None:
        if not syspath.container_root(name).is_dir():
            raise FileNotFoundError(syspath.container_root(name))
        if not syspath.container_config(name).is_file():
            raise FileNotFoundError(syspath.container_config(name))

        with open(syspath.container_config(name), "r") as config_file:
            self.name = name
            self.config = json.load(config_file)
            self.arch = self.config["arch"]
            self.logger = logger

    def start(self) -> None:
        """
        Starts a container
        """
        self.logging_file = open(self.logging_file_path, "wb")
        for i in range(self.max_retries):
            self.ex_port = allocate_port()
            cmd = self.__generate_start_cmd__()
            self.logger.info(f"Executing {cmd}")
            self.booter = popen_spawn.PopenSpawn(
                cmd, logfile=self.logging_file, cwd=syspath.container_root(self.name)
            )
            try:
                self.booter.expect("debian login: ", timeout=360)
            except ExceptionPexpect as exc:
                my_exc = gen_boot_exception(exc, self.logging_file_path)
                if not isinstance(my_exc, PortAllocationError):
                    raise my_exc from exc
            else:
                break
        else:
            raise PortAllocationError
        try:
            self.booter.sendline(self.username)
            self.booter.expect("Password: ")
            self.booter.sendline(self.password)
            self.booter.expect("debian:~#")
        except ExceptionPexpect as exc:
            my_exc = gen_boot_exception(exc, self.logging_file_path)
            raise my_exc from exc

        self.sshi = ssh.SSHInterface(
            "localhost",
            self.username,
            self.ex_port,
            self.password,
            self.name,
            self.logger,
        )
        self.sshi.open_all()

    def run(self, cmd: str) -> None:
        """
        Runs a command in the container

        :param cmd: The command run in the container
        """
        self.sshi.exec_ssh_command([cmd])

    def get(self, remote_file_path: str, local_file_path: str):
        """
        Gets a file from the container

        :param remote_file_path: Path to remote file to grab from container
        :param local_file_path: Local path to store file
        """
        self.sshi.get(remote_file_path, local_file_path)

    def put(self, local_file_path: str, remote_file_path: str):
        """
        Sends a file to the container

        :param local_file_path: Path to the local file to send to the container
        :param remote_file_path: Remote path to store file
        """
        self.sshi.put(local_file_path, remote_file_path)

    def stop(self) -> None:
        """
        Stops the container
        """
        self.sshi.send_poweroff()
        self.sshi.close_all()
        self.logging_file.close()

    def __generate_start_cmd__(self) -> str:
        qemu_system = Path.joinpath(
            syspath.qemu_bin(), f'qemu-system-{self.config["arch"]}'
        )

        """
        Build command-line from JSON config file for QEMU system
        """
        cl_args = [
            "-monitor null",
            "-net nic",
            f"-net user,hostfwd=tcp::{self.ex_port}-:22",
        ]

        if ("disableGraphics" not in self.config) or (
            self.config["disableGraphics"] == True
        ):
            cl_args.append(f"-serial stdio")
            cl_args.append("-nographic")

        for flag, val in self.config["arguments"].items():
            if type(val) is not list:
                cl_args.append(f"-{flag} {val}")
            else:
                for v in val:
                    cl_args.append(f"-{flag} {val}")

        return f'"{qemu_system}" {" ".join(cl_args)}'
