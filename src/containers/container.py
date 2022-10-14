from typing import Optional
from pathlib import Path
import pexpect
from pexpect import popen_spawn
from fabric import Connection


class Container:
    """
    Class for storing container objects

    :param booter: Popen that stores the boot of the instance
    :param ex_port: The ssh port of the system
    :param qemu_file: The file containing the qemu hard disk
    :param arch: The arch of the container
    :param conn: The ssh connection to the container
    """

    booter: Optional[popen_spawn.PopenSpawn] = None
    ex_port: int = 10023
    qemu_file: Path
    arch: str
    conn: Optional[Connection] = None

    def __init__(self, arch: str, qemu_file_path: str) -> None:
        self.qemu_file = Path(qemu_file_path)
        if not self.qemu_file.is_file():
            raise FileNotFoundError(qemu_file_path)
        self.arch = arch

    def start(self) -> None:
        """
        Starts a container
        """
        self.booter = popen_spawn.PopenSpawn(
            f"qemu-system-{self.arch} -M SS-20 -drive file={self.qemu_file},format=qcow2 -net user,hostfwd=tcp::{self.ex_port}-:22 -net nic -m 1G -nographic"
        )
        self.booter.expect("debian login: ", timeout=360)
        self.booter.sendline("root")
        self.booter.expect("Password: ")
        self.booter.sendline("root")
        self.booter.expect("debian:~#")

        self.conn = Connection("localhost", user="root", port=self.ex_port, connect_kwargs={"password": "root"})
        self.conn.open()

    def run(self, cmd: str) -> None:
        """
        Runs a command in the container

        :param cmd: The command run in the container
        """
        print(self.conn.run(cmd).stdout)

    def get_file(self, remote_file_path: str, local_file_path: str):
        """
        Gets a file from the container

        :param remote_file_path: Path to remote file to grab from container
        :param local_file_path: Local path to store file
        """
        self.conn.get(remote_file_path, local_file_path)

    def send_file(self, local_file_path: str, remote_file_path: str):
        """
        Sends a file to the container

        :param local_file_path: Path to the local file to send to the container
        :param remote_file_path: Remote path to store file
        """
        self.conn.put(local_file_path, remote_file_path)

    def stop(self) -> None:
        """
        Stops the container
        """
        self.conn.close()
        self.booter.kill(0)
