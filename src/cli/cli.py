"""
Defines the CLI that takes user input and dispatches the container manager
"""

import re
import os
from sys import stdin, stdout
from typing import List
from pathlib import Path
from getpass import getpass
from github.GithubException import RateLimitExceededException

from src.containers.container_manager_client import ContainerManagerClient
from src.system.update import update, get_newest_supported_version
from src.system.state import frozen
from src.globals import VERSION
from src.repo.repo_manager import RepoManager

CONTAINER_NAME_REGEX = r"""\w+"""

class JabberwockyCLI:
    """
    Represents an instance of the command-line interface
    """

    container_manager: ContainerManagerClient
    repo_manager: RepoManager
    out_stream = stdout
    in_stream = stdin

    def __init__(self, in_stream=stdin, out_stream=stdout) -> None:
        self.in_stream = in_stream
        self.out_stream = out_stream
        self.repo_manager = RepoManager()

    def parse_cmd(self, cmd: List[str]) -> None:
        """
        Parses the cmd sent from script
        """
        subcmd_dict = {
            "help": self.help,
            "files": self.view_files,
            "interact": self.interact,
            "shell": self.interact,
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
            "upload": self.upload,
            "add-repo": self.add_repo,
            "update-repo": self.update_repo,
            "create": self.create,
            "server-halt": self.server_halt,
            "ping": self.ping,
            "ssh-address": self.ssh_address,
            "update": self.update,
            "sftp": self.sftp,
            "panic": self.server_panic,
            "version": self.version,
        }

        if len(cmd) == 0:
            command = "help"
            rest = []
        else:
            command = cmd[0]
            rest = cmd[1:]

        if command not in subcmd_dict:
            self.out_stream.write(f"Command of '{command}' is not valid\nUse 'jab help' to see a list of commands\n")
            return
        subcmd_dict[command.lower()](rest)

    def version(self, cmd: List[str]) -> None:  # pylint: disable=unused-argument
        self.out_stream.write(f"{VERSION}\n")

    def help(self, cmd: List[str]) -> None:  # pylint: disable=unused-argument
        """
        Prints the basic help menu for the CLI

        :param cmd: The rest of command sent
        """
        help_str = """Usage: jabberwocky [subcommand] {args}

Using your container:
start [container_name] - Power on the virtual environment
shell [container_name] - Open the shell of the container
sftp  [container_name] - Open an sftp shell
files [container_name] - View the virtual filesystem
stop  [container_name] - Power off the virtual environment
kill  [container_name] - Kill the virtual environment in the event of a crash
run   [container_name] - Execute a single command in the shell.

File Transfer:
send-file [container_name] [path_to_source] [path_to_destination]
get-file  [container_name] [path_to_source] [path_to_destination]

Managing your containers:
install [path_to_archive] [name]
    - Install a container from a tar archive.
archive [container_name] [path_to_destination]
    - Send a container to an installable tar archive.
delete [container_name]
    - Delete a container from your system. (~/.containers)
create
    - Start the container creation process.

Managing your repositories:
download [container_name] [name]
add-repo [URL]
remove-repo [URL]
update-repo [URL]
"""
        self.out_stream.write(help_str)

    def sftp(self, cmd: List[str]) -> None:
        name = cmd[0]
        comp = re.compile(CONTAINER_NAME_REGEX)
        if not comp.match(name):
            self.out_stream.write(f"'{name}' is not a valid container name\n")
            return
        self.container_manager.sftp(name)

    def view_files(self, cmd: List[str]) -> None:
        name = cmd[0]
        comp = re.compile(CONTAINER_NAME_REGEX)
        if not comp.match(name):
            self.out_stream.write(f"'{name}' is not a valid container name\n")
            return
        try:
            self.container_manager.view_files(name)
        except (FileNotFoundError, PermissionError):
            if frozen():
                self.out_stream.write("Could not find a local FileZilla instance.\n")
                self.out_stream.write("Your platform may not support this command.\n")
            else:
                self.out_stream.write("Could not find a local FileZilla instance.\n")
                self.out_stream.write("You may want to run download_prerequisites.py.\n")

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
        self.container_manager.run_command(name, ["cat", "/etc/motd"])

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
        if len(cmd) < 2:
            self.out_stream.write("Command requires two or three arguments\n")
            return
        if len(cmd) > 2:
            container_name, local_file, remote_file = cmd[0], cmd[1], cmd[2]
        else:
            container_name, local_file, remote_file = cmd[0], cmd[1], None

        comp = re.compile(CONTAINER_NAME_REGEX)
        if not comp.match(container_name):
            self.out_stream.write(f"'{container_name}' is not a valid container name\n")
            return

        self.container_manager.put_file(container_name, local_file, remote_file)

    def get_file(self, cmd: List[str]) -> None:
        """
        Gets a file from a container

        :param cmd: The rest of the command sent
        """
        if len(cmd) < 2:
            self.out_stream.write("Command requires two or three arguments\n")
            return
        if len(cmd) > 2:
            container_name, remote_file, local_file = cmd[0], cmd[1], cmd[2]
        else:
            container_name, remote_file, local_file = cmd[0], cmd[1], None

        comp = re.compile(CONTAINER_NAME_REGEX)
        if not comp.match(container_name):
            self.out_stream.write(f"'{container_name}' is not a valid container name\n")
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
        if len(cmd) != 2:
            self.out_stream.write("Command requires two arguments\n")
            return
        archive_name: str = cmd[0]
        container_name: str = cmd[1]
        comp = re.compile(CONTAINER_NAME_REGEX)
        if not comp.match(container_name):
            self.out_stream.write(f"'{container_name}' is not a valid container name\n")
            return
        
        download_path: Path = self.repo_manager.download(archive_name)
        if download_path is not None:
            self.container_manager.install(str(download_path), container_name)
            download_path.unlink()

    def archive(self, cmd: List[str]) -> None:  # pylint: disable=unused-argument
        """
        Sends a container to an archive

        :param cmd: The rest of the command sent
        """
        if len(cmd) == 0:
            self.out_stream.write("Command requires at leas one argument\n")
            return

        container_name: str = cmd[0]
        path_to_destination: str = cmd[1] if len(cmd) > 1 else os.getcwd()

        comp = re.compile(CONTAINER_NAME_REGEX)
        if not comp.match(container_name):
            self.out_stream.write(f"'{container_name}' is not a valid container name\n")
            return

        self.container_manager.archive(container_name, path_to_destination)

    def upload(self, cmd: List[str]) -> None:
        """
        Upload a container to a repo

        :param cmd: The rest of the command sent
        """
        if len(cmd) != 2:
            self.out_stream.write("Command requires two arguments\n")
            return
        container_name: str = cmd[0]
        repo_url: str = cmd[1]

        comp = re.compile(CONTAINER_NAME_REGEX)
        if not comp.match(container_name):
            self.out_stream.write(f"'{container_name}' is not a valid container name\n")
            return

        stdout.write("Username: ")
        stdout.flush()
        username: str = stdin.readline()
        password: str = getpass("Password: ")

        save_path: Path = Path(f"{container_name}.tar.gz")
        self.container_manager.archive(container_name, str(save_path))
        self.repo_manager.upload(save_path, repo_url, username, password)
        save_path.unlink()

    def add_repo(self, cmd: List[str]) -> None:  # pylint: disable=unused-argument
        """
        Adds an archive to the system

        :param cmd: The rest of the command sent
        """
        if len(cmd) != 1:
            self.out_stream.write("Command requires two arguments\n")
            return
        repo_url: str = cmd[0]
        self.repo_manager.add_repo(repo_url)

    def update_repo(self, cmd: List[str]) -> None:  # pylint: disable=unused-argument
        """
        Updates an archive

        :param cmd: The rest of the command sent
        """
        if len(cmd) > 1:
            self.out_stream.write("Command requires zero or one argument\n")
            return
        if len(cmd) == 1:
            repo_url: str = cmd[0]
            self.repo_manager.update_repo(repo_url)
            return
        self.repo_manager.update_all()

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

    def server_panic(self, cmd: List[str]) -> None:  # pylint: disable=unused-argument
        """
        Tells the server to PANIC!

        :param cmd: The rest of the command sent
        """
        self.container_manager.server_panic()

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
        container_name = cmd[0]
        comp = re.compile(CONTAINER_NAME_REGEX)
        if not comp.match(container_name):
            self.out_stream.write(f"'{container_name}' is not a valid container name\n")
            return
        self.out_stream.write(str(self.container_manager.ssh_address(container_name)))

    def update(self, cmd: List[str]) -> None:
        """
        Checks for updates of the tool and installs them if needed

        :param cmd: The rest of the command sent
        """
        try:
            release, asset = get_newest_supported_version()
        except RateLimitExceededException:
            self.out_stream.write("Cannot fetch updates right now. Try again later or update manually.\n")
            return

        if not release:
            self.out_stream.write("You already have the newest version.\n")

        else:
            self.out_stream.write("\033[93m========\nWARNING!\n========\n")
            self.out_stream.write("UPDATING WILL HALT ALL OF YOUR CURRENTLY OPEN CONTAINERS.\n")
            self.out_stream.write("ALL RUNNING PROCESSES WILL BE TERMINATED.\n")
            self.out_stream.write("ALL UNSAVED DATA WILL BE LOST.\033[0m\n")
            inp = input("Are you sure you want to continue? [y/N] ")

            if inp.lower() not in ("y", "yes"):
                self.out_stream.write("Update cancelled.")
            else:
                update(release, asset)
