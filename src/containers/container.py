"""
Manages the individual container objects
"""

import json
import logging
from io import BytesIO
from pathlib import Path
from signal import SIGABRT
from typing import Optional, Tuple, List

from paramiko.channel import ChannelFile, ChannelStderrFile, ChannelStdinFile
from pexpect import ExceptionPexpect, popen_spawn

from src.containers.exceptions import PortAllocationError, gen_boot_exception
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
    logging_file_path: Path
    logging_file: BytesIO

    def __init__(self, name: str, logger: logging.Logger) -> None:
        if not syspath.get_container_dir(name).is_dir():
            raise FileNotFoundError(syspath.get_container_dir(name))
        if not syspath.get_container_config(name).is_file():
            raise FileNotFoundError(syspath.get_container_config(name))

        self.logging_file_path = syspath.get_container_dir(name) / "pexpect.log"

        self.name = name
        with open(
            syspath.get_container_config(name), "r", encoding="utf-8"
        ) as config_file:
            self.config = json.load(config_file)
        self.arch = self.config["arch"]
        self.logger = logger

    def start(self) -> None:
        """
        Starts a container
        """
        self.logging_file = open(  # pylint: disable=consider-using-with
            self.logging_file_path, "wb"
        )
        for _ in range(self.max_retries):
            self.ex_port = allocate_port()
            cmd = self.__generate_start_cmd__()
            self.logger.debug(f"Executing {cmd}")
            self.booter = popen_spawn.PopenSpawn(
                cmd, logfile=self.logging_file, cwd=syspath.get_container_dir(self.name)
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
            "127.0.0.1",
            self.username,
            self.ex_port,
            self.password,
            self.name,
            self.logger,
        )
        self.sshi.open_all()
        self.sshi.update_hostkey()

    def run(self, cmd: List[str]) -> Tuple[ChannelStdinFile, ChannelFile, ChannelStderrFile, int]:
        """
        Runs a command in the container

        :param cmd: The command run in the container
        """
        return self.sshi.exec_ssh_command(cmd)

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

    def kill(self) -> None:
        """
        Kills the QEMU process of the container.
        This is like yanking the power cord. Only use when you have no other choice.
        """
        self.booter.kill(SIGABRT)
        self.sshi.close_all()
        self.logging_file.close()

    def __generate_start_cmd__(self) -> str:
        """
        Build command-line from JSON config file for QEMU system

        :return: The cmd command to start qemu
        """
        qemu_system = Path.joinpath(
            syspath.get_qemu_bin(), f'qemu-system-{self.config["arch"]}'
        )

        cl_args = [
            "-monitor null",
            "-net nic",
            f"-net user,hostfwd=tcp::{self.ex_port}-:22",
        ]

        if ("disableGraphics" not in self.config) or (
            self.config["disableGraphics"] is True
        ):
            cl_args.append("-serial stdio")
            cl_args.append("-nographic")

        for flag, val in self.config["arguments"].items():
            if not isinstance(val, list):
                cl_args.append(f"-{flag} {val}")
            else:
                for _ in val:
                    cl_args.append(f"-{flag} {val}")

        return f'"{qemu_system}" {" ".join(cl_args)}'
