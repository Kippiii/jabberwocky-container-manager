import logging
import os
import subprocess
from typing import Optional

import paramiko

from src.system import syspath


class PoweroffBadExitError(RuntimeError):
    """
    Raised when poweroff fails
    """


class SSHBadExitError(RuntimeError):
    """
    Raised when ssh has an error on exit
    """


class FailedToAuthorizeKeyError(RuntimeError):
    """
    Raised during failure to authorize keys
    """


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
    logger: Optional[logging.Logger]
    ssh_client: Optional[paramiko.SSHClient] = None
    ftp_client: Optional[paramiko.SFTPClient] = None

    def __init__(
        self,
        host: str,
        user: str,
        port: int,
        passwd: str,
        container_name: str,
        logger: Optional[logging.Logger] = None,
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
        self.__update_hostkey__()

    def put(self, local_file_path: str, remote_file_path: str) -> None:
        """
        Puts a file into SSH

        :param local_file_path: The local file to be inserted
        :param remote_file_path: The remote path in SSH
        """
        if self.logger:
            self.logger.info(f"Attempting put({local_file_path}, {remote_file_path})")

        self.ftp_client.put(local_file_path, remote_file_path)

    def get(self, remote_file_path: str, local_file_path: str) -> None:
        """
        Gets a file from the SSH

        :param remote_file_path: The path to file in the SSH machine
        :param local_file_path: The path to the local file
        """
        if self.logger:
            self.logger.info(f"Attempting get({local_file_path}, {remote_file_path})")

        self.ftp_client.get(remote_file_path, local_file_path)

    def exec_ssh_command(self, cli: list) -> None:
        """
        Executes a command in the SSH

        :param cli: The command run in the SSH as an array
        """
        _CMD = [
            "ssh",
            "-oStrictHostKeyChecking=no",
            "-oLogLevel=ERROR",
            "-oPasswordAuthentication=no",
            "-i",
            str(syspath.get_container_id_rsa(self.container_name)),
            "-p",
            str(self.port),
            f"{self.user}@{self.host}",
            *cli,
        ]

        if self.logger:
            self.logger.info(f'Executing {" ".join(_CMD)}')

        completed_process = subprocess.run(_CMD, shell=True)

        if completed_process.returncode:
            raise SSHBadExitError(
                f"{completed_process.returncode}. You may need to run __update_hostkey__."
            )

    def exec_ssh_shell(self) -> None:
        """
        Executes a shell in the SSH
        """
        self.exec_ssh_command([])

    def send_poweroff(self) -> None:
        """
        Sends a poweroff signal through the SSH connection
        """
        if self.logger:
            self.logger.info("Attempting to poweroff")

        _, stdout, _ = self.ssh_client.exec_command("poweroff")
        if stdout.channel.recv_exit_status():
            raise PoweroffBadExitError(stdout.channel.exit_status)

    def close_all(self) -> None:
        """
        Closes the SSH and FTP connections
        """
        self.ftp_client.close()
        self.ssh_client.close()
        self.ssh_client = None
        self.ftp_client = None

    def __update_hostkey__(self) -> None:
        """
        Updates the keys used for the SSH
        """
        if not self.ssh_client:
            raise OSError("ssh client not opened")

        if syspath.get_container_id_rsa(self.container_name).is_file():
            os.remove(syspath.get_container_id_rsa(self.container_name))
        if syspath.get_get_container_id_rsa_pub(self.container_name).is_file():
            os.remove(syspath.get_get_container_id_rsa_pub(self.container_name))

        key = paramiko.RSAKey.generate(1024)
        key.write_private_key_file(syspath.get_container_id_rsa(self.container_name))
        with open(
            syspath.get_get_container_id_rsa_pub(self.container_name), "w"
        ) as pub:
            pub.write(f"ssh-rsa {key.get_base64()}\n")

        _, stdout, _ = self.ssh_client.exec_command(
            f'echo "ssh-rsa {key.get_base64()}" > $HOME/.ssh/authorized_keys'
        )

        if stdout.channel.recv_exit_status():
            raise FailedToAuthorizeKeyError(stdout.channel.exit_status)
