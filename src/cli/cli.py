"""
Defines the CLI that takes user input and dispatches the container manager
"""

import re
from sys import stdin, stdout
from typing import List

from src.containers.container_manager_client import ContainerManagerClient

CONTAINER_NAME_REGEX = r"""\w+"""
FILE_NAME_REGEX = r"""[^<>:;,?"*|/]+"""


class JabberwockyCLI:
    """
    Represents an instance of the command-line interface
    """

    container_manager: ContainerManagerClient
    out_stream = stdout
    in_stream = stdin

    def __init__(self, in_stream=stdin, out_stream=stdout) -> None:
        self.in_stream = in_stream
        self.out_stream = out_stream

    def parse_cmd(self, cmd: List[str]) -> None:
        """
        Parses the cmd sent from script
        """
        subcmd_dict = {
            "help": self.help,
            "interact": self.interact,
            "start": self.start,
            "stop": self.stop,
            "kill": self.kill,
            "run": self.run,
            "send-file": self.send_file,
            "get-file": self.get_file,
            "install": self.install,
            "delete": self.delete,
            "download": self.download,
            "archive": self.archive,
            "add-repo": self.add_repo,
            "update-repo": self.update_repo,
            "create": self.create,
            "server-halt": self.server_halt,
            "ping": self.ping,
            "ssh-address": self.ssh_address,
        }

        if len(cmd) == 0:
            command = "help"
            rest = []
        else:
            command = cmd[0]
            rest = cmd[1:]

        if command not in subcmd_dict:
            self.out_stream.write(f"Command of '{command}' is not valid\n")
            return
        subcmd_dict[command](rest)

    def help(self, cmd: List[str]) -> None:  # pylint: disable=unused-argument
        """
        Prints the basic help menu for the CLI

        :param cmd: The rest of command sent
        """
        help_str = """Manages containers installed on this system.
Usage: jabberwocky [subcommand] {args}

interact [container_name]
Open the shell of the container

start [container_name]
Boots a container and allows it to idle in the background

stop [container_name]
Powers off a container

send-file [container_name] [path_to_source] [path_to_destination]
Copy a file from the host to the container

get-file [container_name] [path_to_source] [path_to_destination]
Copy a file from the container to the host

install [path_to_archive] [name]
Installs a container archive on the computer

download [container_name] [name]
Downloads a container to your computer

archive [container_name] [path_to_destination]
Sends a container to a downloadable archive

add-repo [URL]
remove-repo [URL]
Adds or a removes a repository

update-repo [URL]
Download index files for a repository

delete [container_name]
Deletes a container from the file system

create
Starts the container creation wizard
"""
        self.out_stream.write(help_str)

    def interact(self, cmd: List[str]) -> None:
        """
        Allows user to directly interact with shell

        :param cmd: The rest of the command sent
        """
        name = cmd[0]
        comp = re.compile(CONTAINER_NAME_REGEX)
        if not comp.match(name):
            self.out_stream.write(f"'{name}' is not a valid container name\n")
            return
        self.container_manager.run_shell(name)

    def start(self, cmd: List[str]) -> None:
        """
        Starts a container

        :param cmd: The rest of the command sent
        """
        name = cmd[0]
        comp = re.compile(CONTAINER_NAME_REGEX)
        if not comp.match(name):
            self.out_stream.write(f"'{name}' is not a valid container name\n")
            return
        self.container_manager.start(name)

    def stop(self, cmd: List[str]) -> None:
        """
        Stops a container

        :param cmd: The rest of the command sent
        """
        name = cmd[0]
        comp = re.compile(CONTAINER_NAME_REGEX)
        if not comp.match(name):
            self.out_stream.write(f"'{name}' is not a valid container name\n")
            return
        self.container_manager.stop(name)

    def kill(self, cmd: List[str]) -> None:
        """
        Kills a container

        :param cmd: The rest of the command sent
        """
        name = cmd[0]
        comp = re.compile(CONTAINER_NAME_REGEX)
        if not comp.match(name):
            self.out_stream.write(f"'{name}' is not a valid container name\n")
            return
        self.container_manager.kill(name)

    def run(self, cmd: List[str]) -> None:
        """
        Runs a command in the container

        :param cmd: The rest of the command sent
        """
        if len(cmd) < 2:
            self.out_stream.write("Command requires two arguments\n")
            return
        container_name, command = cmd[0], cmd[1:]
        comp = re.compile(CONTAINER_NAME_REGEX)
        if not comp.match(container_name):
            self.out_stream.write(f"'{container_name}' is not a valid container name\n")
            return
        self.container_manager.run_command(container_name, command)

    def send_file(self, cmd: List[str]) -> None:
        """
        Sends a file to a container

        :param cmd: The rest of the command sent
        """
        if len(cmd) < 3:
            self.out_stream.write("Command requires three arguments\n")
            return
        container_name, local_file, remote_file = cmd[0], cmd[1], cmd[2]
        comp = re.compile(CONTAINER_NAME_REGEX)
        if not comp.match(container_name):
            self.out_stream.write(f"'{container_name}' is not a valid container name\n")
            return
        comp = re.compile(FILE_NAME_REGEX)
        if not comp.match(local_file):
            self.out_stream.write(f"'{local_file}' is not a valid file name")
            return
        if not comp.match(remote_file):
            self.out_stream.write(f"'{remote_file}' is not a valid file name")
            return
        self.container_manager.put_file(container_name, local_file, remote_file)

    def get_file(self, cmd: List[str]) -> None:
        """
        Gets a file from a container

        :param cmd: The rest of the command sent
        """
        if len(cmd) < 3:
            self.out_stream.write("Command requires three arguments\n")
            return
        container_name, remote_file, local_file = cmd[0], cmd[1], cmd[2]
        comp = re.compile(CONTAINER_NAME_REGEX)
        if not comp.match(container_name):
            self.out_stream.write(f"'{container_name}' is not a valid container name\n")
            return
        comp = re.compile(FILE_NAME_REGEX)
        if not comp.match(remote_file):
            self.out_stream.write(f"'{remote_file}' is not a valid file name")
            return
        if not comp.match(local_file):
            self.out_stream.write(f"'{local_file}' is not a valid file name")
            return
        self.container_manager.get_file(container_name, remote_file, local_file)

    def install(self, cmd: List[str]) -> None:
        """
        Installs a container from an archive

        :param cmd: The rest of the command sent
        """
        if len(cmd) != 2:
            self.out_stream.write("Command requires two arguments\n")
            return
        archive_path_str, container_name = cmd[0], cmd[1]
        comp = re.compile(CONTAINER_NAME_REGEX)
        if not comp.match(container_name):
            self.out_stream.write(f"'{container_name}' is not a valid container name\n")
            return
        self.container_manager.install(archive_path_str, container_name)

    def delete(self, cmd: List[str]) -> None:
        """
        Deletes a container from the file system

        :param cmd: The rest of the command sent
        """
        container_name = cmd[0]
        comp = re.compile(CONTAINER_NAME_REGEX)
        if not comp.match(container_name):
            self.out_stream.write(f"'{container_name}' is not a valid container name\n")
            return
        self.container_manager.delete(container_name)

    def download(self, cmd: List[str]) -> None:  # pylint: disable=unused-argument
        """
        Downloads a container from an archive

        :param cmd: The rest of the command sent
        """
        self.out_stream.write("Command not yet supported")

    def archive(self, cmd: List[str]) -> None:  # pylint: disable=unused-argument
        """
        Sends a container to an archive

        :param cmd: The rest of the command sent
        """
        self.out_stream.write("Command not yet supported")

    def add_repo(self, cmd: List[str]) -> None:  # pylint: disable=unused-argument
        """
        Adds an archive to the system

        :param cmd: The rest of the command sent
        """
        self.out_stream.write("Command not yet supported")

    def update_repo(self, cmd: List[str]) -> None:  # pylint: disable=unused-argument
        """
        Updates an archive

        :param cmd: The rest of the command sent
        """
        self.out_stream.write("Command not yet supported")

    def create(self, cmd: List[str]) -> None:  # pylint: disable=unused-argument
        """
        Runs the container creation wizard

        :param cmd: The rest of the command sent
        """
        self.out_stream.write("Command not yet supported")

    def server_halt(self, cmd: List[str]) -> None:  # pylint: disable=unused-argument
        """
        Tells the server to halt

        :param cmd: The rest of the command sent
        """
        self.container_manager.server_halt()

    def ping(self, cmd: List[str]) -> None:  # pylint: disable=unused-argument
        """
        Pings the server

        :param cmd: The rest of the command sent
        """
        self.container_manager.ping()

    def ssh_address(self, cmd: List[str]) -> None:  # pylint: disable=unused-argument
        """
        Prints the information necessary to SSH into the container's shell

        :param cmd: The rest of the command sent
        """
        container_name = cmd.strip()
        comp = re.compile(CONTAINER_NAME_REGEX)
        if not comp.match(container_name):
            self.out_stream.write(f"'{container_name}' is not a valid container name\n")
            return
        self.out_stream.write(str(self.container_manager.ssh_address(container_name)))
