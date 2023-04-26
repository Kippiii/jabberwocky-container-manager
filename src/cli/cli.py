"""
Defines the CLI that takes user input and dispatches the container manager
"""

import os
import re
from getpass import getpass
from pathlib import Path
from sys import stdin, stdout
from typing import List

from github.GithubException import RateLimitExceededException

import src.containers.container_builder as builder
from src.containers.container_manager_client import ContainerManagerClient
from src.globals import VERSION
from src.repo.repo_manager import RepoManager
from src.system.multithreading import InterruptibleTask, SpinningTask
from src.system.state import frozen
from src.system.update import get_newest_supported_version, update

CONTAINER_NAME_REGEX = r"""\w+"""


class JabberwockyCLI:  # pylint: disable=too-many-public-methods
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
        self.repo_manager = RepoManager(in_stream=in_stream, out_stream=out_stream)
        self.container_manager = ContainerManagerClient(in_stream, out_stream)

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
            "rename": self.rename,
            "download": self.download,
            "archive": self.archive,
            "export": self.archive,
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
            "build-init": self.build_init,
            "build": self.build,
            "list": self.list_containers,
            "ls": self.list_containers,
            "clean": self.clean,
            "build-clean": self.clean,
        }

        if len(cmd) == 0:
            command = "help"
            rest = []
        else:
            command = cmd[0]
            rest = cmd[1:]

        if command not in subcmd_dict:
            self.out_stream.write(
                f"Command of '{command}' is not valid\nUse 'jab help' to see"
                " a list of commands\n"
            )
            return
        subcmd_dict[command.lower()](rest)

    def version(self, cmd: List[str]) -> None:  # pylint: disable=unused-argument
        """
        Gets the version of the container manager

        :param cmd: The command-line args sent
        """
        self.out_stream.write(f"{VERSION}\n")

    def list_containers(
        self, cmd: List[str]  # pylint: disable=unused-argument
    ) -> None:
        """
        Sends a list of all the containers installed on the system

        :param cmd: The command-line args sent
        """
        print("    ".join(self.container_manager.list_containers()))

    def build_init(self, cmd: List[str]) -> None:
        """
        Initializes the directories for building

        :param cmd: The command-line args sent
        """
        builder.make_skeleton(Path(cmd[0]) if cmd else Path.cwd())

    def clean(self, cmd: List[str]) -> None:
        """
        Cleans up a build directory

        :param cmd: The command-line args sent
        """
        builder.clean(
            Path(cmd[0]) if cmd else Path.cwd(),
            self.in_stream,
            self.out_stream,
            self.out_stream,
        )

    def build(self, cmd: List[str]) -> None:
        """
        Starts a build of a new container

        :param cmd: The command-line args sent
        """
        if "--uncompressed" in cmd:
            cmd.remove("--uncompressed")
            compress = False
        else:
            compress = True

        work_dir = Path(cmd[0]) if cmd else Path.cwd()
        builder.do_debootstrap(
            work_dir, self.in_stream, self.out_stream, self.out_stream
        )
        SpinningTask(
            "Exporting build to archive",
            builder.do_export,
            (work_dir, compress),
            self.out_stream,
        ).exec()

    def help(self, cmd: List[str]) -> None:  # pylint: disable=unused-argument
        """
        Prints the basic help menu for the CLI

        :param cmd: The rest of command sent
        """
        help_str = """Usage: jabberwocky [subcommand] {args}

Using your container:
ls                     - List your installed containers
start [container_name] - Power on the virtual environment
shell [container_name] - Open the shell of the container
sftp  [container_name] - Open an sftp shell
files [container_name] - View the virtual filesystem
stop  [container_name] - Power off the virtual environment
kill  [container_name] - Kill the virtual environment in the event of a crash
run   [container_name] - Execute a single command in the shell.

Container Building:
build-init  (directory)? - Prepare a directory for building.
build       (directory)? - Build a container.
build-clean (directory)? - Delete temporary files.

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
rename [old_container_name] [new_container_name]
    - Rename a container in your file system
update
    - Downloads and installs the newest version of the container manager tool
version
    - Gets the currently running version of the container manager tool

Managing your repositories:
download [container_name] [name] - Download a container from your list of repos
add-repo [URL]                   - Adds a repo to the repo list
remove-repo [URL]                - Removes a repo from the repo list
update-repo [URL]?               - Gets what archives are in a repo (or all of them)

Local server:
server-halt   - Gracefully halts the local server
panic         - Ungracefully stops the local server
"""
        self.out_stream.write(help_str)

    def sftp(self, cmd: List[str]) -> None:
        """
        Opens up an sftp session with a running container

        :param cmd: The command-line args
        """
        name = cmd[0]
        comp = re.compile(CONTAINER_NAME_REGEX)
        if not comp.match(name):
            self.out_stream.write(f"'{name}' is not a valid container name.\n")
            return
        if not self.container_manager.started(name):
            self.start([name])
        self.container_manager.sftp(name)

    def view_files(self, cmd: List[str]) -> None:
        """
        Opens a FileZilla session with the container

        :param cmd: The command-line args
        """
        name = cmd[0]
        comp = re.compile(CONTAINER_NAME_REGEX)
        if not comp.match(name):
            self.out_stream.write(f"'{name}' is not a valid container name.\n")
            return
        if not self.container_manager.started(name):
            self.start([name])
        try:
            self.container_manager.view_files(name)
        except (FileNotFoundError, PermissionError):
            if frozen():
                self.out_stream.write("Could not find a local FileZilla instance.\n")
                self.out_stream.write("Your platform may not support this command.\n")
            else:
                self.out_stream.write("Could not find a local FileZilla instance.\n")
                self.out_stream.write(
                    "You may want to run download_prerequisites.py.\n"
                )

    def interact(self, cmd: List[str]) -> None:
        """
        Allows user to directly interact with shell

        :param cmd: The rest of the command sent
        """
        name = cmd[0]
        comp = re.compile(CONTAINER_NAME_REGEX)
        if not comp.match(name):
            self.out_stream.write(f"'{name}' is not a valid container name.\n")
            return
        if not self.container_manager.started(name):
            self.start([name])
        self.container_manager.run_shell(name)

    def start(self, cmd: List[str]) -> None:
        """
        Starts a container

        :param cmd: The rest of the command sent
        """
        name = cmd[0]
        comp = re.compile(CONTAINER_NAME_REGEX)
        if not comp.match(name):
            self.out_stream.write(f"'{name}' is not a valid container name.\n")
            return

        task = SpinningTask(
            f"Starting {name}", self.container_manager.start, (name,), self.out_stream
        )
        task.exec()

    def stop(self, cmd: List[str]) -> None:
        """
        Stops a container

        :param cmd: The rest of the command sent
        """
        name = cmd[0]
        comp = re.compile(CONTAINER_NAME_REGEX)
        if not comp.match(name):
            self.out_stream.write(f"'{name}' is not a valid container name.\n")
            return
        if not self.container_manager.started(name):
            self.out_stream.write(f"{name} is not started.\n")
        else:
            self.container_manager.stop(name)
            self.out_stream.write("Done.\n")

    def kill(self, cmd: List[str]) -> None:
        """
        Kills a container

        :param cmd: The rest of the command sent
        """
        name = cmd[0]
        comp = re.compile(CONTAINER_NAME_REGEX)
        if not comp.match(name):
            self.out_stream.write(f"'{name}' is not a valid container name.\n")
            return
        if not self.container_manager.started(name):
            self.out_stream.write(f"{name} is not started.\n")
        else:
            self.container_manager.kill(name)
            self.out_stream.write("Done.\n")

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
            self.out_stream.write(
                f"'{container_name}' is not a valid container name.\n"
            )
            return
        if not self.container_manager.started(container_name):
            self.start([container_name])
        InterruptibleTask(
            self.container_manager.run_command, (container_name, command)
        ).exec()

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
            self.out_stream.write(
                f"'{container_name}' is not a valid container name.\n"
            )
            return
        if not self.container_manager.started(container_name):
            self.start([container_name])

        string = f"Copying '{local_file}' -> '{remote_file if remote_file else '~'}'"
        task = SpinningTask(
            string,
            self.container_manager.put_file,
            (container_name, local_file, remote_file),
        )
        task.exec()

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
            self.out_stream.write(
                f"'{container_name}' is not a valid container name.\n"
            )
            return
        if not self.container_manager.started(container_name):
            self.start([container_name])

        string = f"Copying '{remote_file}' -> '{local_file if local_file else '.'}'"
        task = SpinningTask(
            string,
            self.container_manager.get_file,
            (container_name, remote_file, local_file),
        )
        task.exec()

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
            self.out_stream.write(
                f"'{container_name}' is not a valid container name.\n"
            )
            return
        task = SpinningTask(
            f"Installing {container_name}. This may take several minutes",
            self.container_manager.install,
            (archive_path_str, container_name),
        )
        task.exec()

    def delete(self, cmd: List[str]) -> None:
        """
        Deletes a container from the file system

        :param cmd: The rest of the command sent
        """
        container_name = cmd[0]

        comp = re.compile(CONTAINER_NAME_REGEX)
        if not comp.match(container_name):
            self.out_stream.write(
                f"'{container_name}' is not a valid container name.\n"
            )
            return

        if self.container_manager.started(container_name):
            self.out_stream.write(
                f"Please stop {container_name} before trying to delete it."
            )
        else:
            self.container_manager.delete(container_name)

    def rename(self, cmd: List[str]) -> None:
        """
        Renames a container on the file system

        :param cmd: The rest of the command sent
        """
        if len(cmd) != 2:
            self.out_stream.write("Command requires two arguments\n")
            return

        old_name, new_name = cmd[0], cmd[1]
        comp = re.compile(CONTAINER_NAME_REGEX)
        if not comp.match(old_name):
            self.out_stream.write(f"'{old_name}' is not a valid container name.\n")
            return
        if not comp.match(new_name):
            self.out_stream.write(f"'{new_name}' is not a valid container name.\n")
            return

        if self.container_manager.started(old_name):
            self.out_stream.write(
                f"Please stop '{old_name}' before trying to rename it.\n"
            )
            return

        self.container_manager.rename(old_name, new_name)

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

        task = SpinningTask(
            f"Exporting {container_name}. This will take a long time",
            self.container_manager.archive,
            (container_name, path_to_destination),
        )
        task.exec()

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

        self.out_stream.write("Username: ")
        self.out_stream.flush()
        username: str = self.in_stream.readline()
        if self.in_stream != stdin:
            password: str = self.in_stream.readline()
        else:
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
        time = self.container_manager.ping()
        self.out_stream.write(f"Got OK in {time:.5f} seconds.\n")

    def ssh_address(self, cmd: List[str]) -> None:  # pylint: disable=unused-argument
        """
        Prints the information necessary to SSH into the container's shell

        :param cmd: The rest of the command sent
        """
        container_name = cmd[0]
        comp = re.compile(CONTAINER_NAME_REGEX)
        if not comp.match(container_name):
            self.out_stream.write(
                f"'{container_name}' is not a valid container name.\n"
            )
            return
        if not self.container_manager.started(container_name):
            self.out_stream.write(f"{container_name} is not started.\n")
        self.out_stream.write(str(self.container_manager.ssh_address(container_name)))

    def update(self, cmd: List[str]) -> None:  # pylint: disable=unused-argument
        """
        Checks for updates of the tool and installs them if needed

        :param cmd: The rest of the command sent
        """
        try:
            release, asset = get_newest_supported_version()
        except RateLimitExceededException:
            self.out_stream.write(
                "Cannot fetch updates right now. Try again later or update manually.\n"
            )
            return

        if not release:
            self.out_stream.write("You already have the newest version.\n")

        else:
            self.out_stream.write("\033[93m========\nWARNING!\n========\n")
            self.out_stream.write(
                "UPDATING WILL HALT ALL OF YOUR CURRENTLY OPEN CONTAINERS.\n"
            )
            self.out_stream.write("ALL RUNNING PROCESSES WILL BE TERMINATED.\n")
            self.out_stream.write("ALL UNSAVED DATA WILL BE LOST.\033[0m\n")
            inp = input("Are you sure you want to continue? [y/N] ")

            if inp.lower() not in ("y", "yes"):
                self.out_stream.write("Update cancelled.")
            else:
                update(release, asset)
