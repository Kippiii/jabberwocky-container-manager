"""
Manages the individual container objects
"""

import json
import psutil
import logging
from os import cpu_count
from math import floor
from io import BytesIO
from pathlib import Path
from signal import SIGABRT
from typing import Optional, Tuple, List, Union

from paramiko.channel import ChannelFile, ChannelStderrFile, ChannelStdinFile
from pexpect import ExceptionPexpect, popen_spawn

from src.containers.container_config import ContainerConfig
from src.containers.exceptions import PortAllocationError, gen_boot_exception
from src.containers.port_allocation import allocate_port
from src.system import ssh, syspath


class Container(ContainerConfig):
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
    sshi: ssh.SSHInterface
    timeout: int = 180
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
        self.logger = logger

        with open(syspath.get_container_config(name), "r", encoding="utf-8") as config_file:
            super().__init__(json.load(config_file))

    def start(self) -> None:
        """
        Starts a container
        """
        self.logging_file = open(  # pylint: disable=consider-using-with
            self.logging_file_path, "wb"
        )
        for _ in range(self.max_retries):
            self.ex_port = allocate_port()
            cmd = self._generate_start_cmd()
            self.logger.debug(f"Executing {cmd}")
            self.booter = popen_spawn.PopenSpawn(
                cmd, logfile=self.logging_file, cwd=syspath.get_container_dir(self.name)
            )
            try:
                self.booter.expect(f"{self.hostname} login: ", timeout=self.timeout)
            except ExceptionPexpect as exc:
                my_exc = gen_boot_exception(exc, self.logging_file_path)
                if not isinstance(my_exc, PortAllocationError):
                    raise my_exc from exc
            else:
                break
        else:
            raise PortAllocationError

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
        self.sshi.send_poweroff(self.booter.pid)
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

    def _generate_start_cmd(self) -> List[Union[str, Path]]:
        """
        Build command-line from ContainerConfig file for QEMU system

        :return: The cmd command to start qemu
        """
        def max_smp(smp: int) -> int:
            return min(smp, floor(0.75 * cpu_count()))
        def max_mem(mem: int) -> int:
            return min(1000000 * mem, 0.75 * psutil.virtual_memory().total) // 1000000

        qemu_system = Path.joinpath(
            syspath.get_qemu_bin(), f'qemu-system-{self.arch}'
        )

        arch_specific_args = {
            "x86_64": [
                "-serial",
                "mon:stdio",
                "-smp",
                str(max_smp(self.smp)),
                *(["-append",
                   "console=ttyS0 root=/dev/sda1"]
                  if not self.legacy else []),
            ],
            "aarch64": [
                "-M",
                "virt",
                "-cpu",
                "cortex-a53",
                "-smp",
                str(max_smp(self.smp)),
                "-append",
                "console=ttyAMA0 root=/dev/vda1",
            ],
            "mipsel": [
                "-M",
                "malta",
                "-smp",
                "1",
                "-append",
                "rootwait root=/dev/sda1"
            ],
        }[self.arch]

        hostfwds = [f"hostfwd=tcp::{hport}-:{vport}" for vport, hport in self.portfwd]
        hostfwds.append(f"hostfwd=tcp::{self.ex_port}-:22")
        hostfwd = "user," + ",".join(hostfwds)

        kernel = ["-kernel", "vmlinuz", "-initrd", "initrd.img"] if not self.legacy else []

        return [
            qemu_system,
            *arch_specific_args,
            *kernel,
            "-monitor",
            "null",
            "-net",
            "nic",
            "-nographic",
            "-m",
            "{}M".format(max_mem(self.memory)),
            "-drive",
            "file=hdd.qcow2,format=qcow2",
            "-net",
            hostfwd,
        ]
