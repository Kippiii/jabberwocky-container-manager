"""
Manages SSH connections (with containers)
"""

import logging
import os
import shlex
import signal
import time
from os.path import basename, isdir
from os.path import join as joindir
from posixpath import basename as posixbasename
from posixpath import join as posixjoin
from stat import S_ISDIR
from typing import Optional, Tuple

import paramiko
import psutil
from paramiko.channel import ChannelFile, ChannelStderrFile, ChannelStdinFile

from src.containers.exceptions import (FailedToAuthorizeKeyError,
                                       PoweroffTimeoutExceededError)
from src.system import syspath


class SSHInterface:
    """
    Represents a connection to SSH

    :param host: The host being connected to for the connection
    :param user: The name of the SSH user
    :param port: The port for the SSH connection
    :param passwd: The password for the SSH user
    :param container_name: The name of the container
    :param logger: The logger used for logging
    :param ssh_client: The SSH client
    :param ftp_client: The client for file transfer
    """

    host: str
    user: str
    port: int
    passwd: str
    container_name: str
    logger: logging.Logger
    ssh_client: Optional[paramiko.SSHClient] = None
    ftp_client: Optional[paramiko.SFTPClient] = None

    def __init__(
        self,
        host: str,
        user: str,
        port: int,
        passwd: str,
        container_name: str,
        logger: logging.Logger,
    ):
        self.host = host
        self.user = user
        self.port = port
        self.passwd = passwd
        self.container_name = container_name
        self.logger = logger

    def open_all(self) -> None:
        """
        Opens the SSH and FTP connections
        """
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.MissingHostKeyPolicy())
        self.ssh_client.connect(
            hostname=self.host, username=self.user, port=self.port, password=self.passwd
        )
        self.ftp_client = self.ssh_client.open_sftp()

    def put(self, local_file_path: str, remote_file_path: str) -> None:
        """
        Puts a file into SSH
        Will raise a FileNotFoundError, IsADirectoryError

        :param local_file_path: The local file to be inserted
        :param remote_file_path: The remote path in SSH
        """
        if isdir(local_file_path):
            raise IsADirectoryError(local_file_path)

        # If destination is a directory, put file with basename(local) in said directory
        try:
            if S_ISDIR(self.ftp_client.lstat(remote_file_path).st_mode):
                remote_file_path = posixjoin(
                    remote_file_path, basename(local_file_path)
                )
        except FileNotFoundError:
            pass

        # Attempt put
        self.logger.debug(f"Attempting put({local_file_path}, {remote_file_path})")
        self.ftp_client.put(local_file_path, remote_file_path)

    def get(self, remote_file_path: str, local_file_path: str) -> None:
        """
        Gets a file from the SSH
        Raises IsADirectoryError, FileNotFoundError

        :param remote_file_path: The path to file in the SSH machine
        :param local_file_path: The path to the local file
        """
        if isdir(local_file_path):
            local_file_path = joindir(local_file_path, posixbasename(remote_file_path))

        if S_ISDIR(self.ftp_client.lstat(remote_file_path).st_mode):
            raise IsADirectoryError(remote_file_path)

        self.logger.debug(f"Attempting get({local_file_path}, {remote_file_path})")

        self.ftp_client.get(remote_file_path, local_file_path)

    def exec_ssh_command(
        self, cli: list
    ) -> Tuple[ChannelStdinFile, ChannelFile, ChannelStderrFile, int]:
        """
        Executes a command in the SSH

        :param cli: The command run in the SSH as an array
        """
        command = "echo $$ && exec " + " ".join(map(shlex.quote, cli))
        self.logger.debug(f'Exec "{command}" -> {self.container_name}')
        stdin, stdout, stderr = self.ssh_client.exec_command(command)
        pid = int(stdout.readline())
        return stdin, stdout, stderr, pid

    def send_poweroff(self, pid: int) -> None:
        """
        Sends a poweroff signal through the SSH connection
        """
        self.logger.debug("Attempting to poweroff")

        _, stdout, _ = self.ssh_client.exec_command("poweroff")
        stdout.channel.recv_exit_status()

        for _ in range(15):  # Max timeout: 15 seconds
            if psutil.pid_exists(pid):
                if os.name != "nt" and psutil.Process(pid).status() == "zombie":
                    os.kill(pid, signal.SIGKILL)
                    break
                time.sleep(1)
            else:
                break
        else:
            raise PoweroffTimeoutExceededError(f"PID={pid}")

    def close_all(self) -> None:
        """
        Closes the SSH and FTP connections
        """
        self.ftp_client.close()
        self.ssh_client.close()
        self.ssh_client = None
        self.ftp_client = None

    def update_hostkey(self) -> None:
        """
        Updates the keys used for the SSH
        """
        if not self.ssh_client:
            raise OSError("ssh client not opened")

        if syspath.get_container_id_rsa(self.container_name).is_file():
            os.remove(syspath.get_container_id_rsa(self.container_name))
        if syspath.get_get_container_id_rsa_pub(self.container_name).is_file():
            os.remove(syspath.get_get_container_id_rsa_pub(self.container_name))

        key = paramiko.RSAKey.generate(2048)
        key.write_private_key_file(syspath.get_container_id_rsa(self.container_name))
        with open(
            syspath.get_get_container_id_rsa_pub(self.container_name),
            "w",
            encoding="utf-8",
        ) as pub:
            pub.write(f"ssh-rsa {key.get_base64()}\n")

        _, stdout, _ = self.ssh_client.exec_command(
            f'echo "ssh-rsa {key.get_base64()}" > $HOME/.ssh/authorized_keys'
        )

        if stdout.channel.recv_exit_status():
            raise FailedToAuthorizeKeyError(stdout.channel.exit_status)
