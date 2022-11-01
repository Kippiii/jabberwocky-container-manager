import re

from src.containers.container_manager import ContainerManager

CONTAINER_NAME_REGEX = r"""[a-zA-Z_]+"""

class JabberwockyCLI:
    """
    Represents an instance of the command-line interface
    """
    cm: ContainerManager

    def __init__(self) -> None:
        pass

    def parse_cmd(self, cmd: str) -> None:
        """
        Parses the cmd sent from script
        """
        subcmd_dict = {
            "help": self.help,
            "interact": self.interact,
            "start": self.start,
            "stop": self.stop,
            "send-file": self.send_file,
            "get-file": self.get_file,
            "install": self.install,
            "delete": self.delete,
            "download": self.download,
            "archive": self.archive,
            "add-repo": self.add_repo,
            "update-repo": self.update_repo,
            "create": self.create,
        }

        command, rest = cmd.split(None, 1)
        if command not in subcmd_dict:
            pass # TODO Error
        subcmd_dict[command](rest)

    def help(self, cmd: str) -> None:
        """
        Prints the basic help menu for the CLI

        :param cmd: The rest of command sent
        """
        pass

    def interact(self, cmd: str) -> None:
        """
        Allows user to directly interact with shell

        :param cmd: The rest of the command sent
        """
        pass

    def start(self, cmd: str) -> None:
        """
        Starts a container

        :param cmd: The rest of the command sent
        """
        comp = re.compile(CONTAINER_NAME_REGEX)
        if not comp.match(cmd.strip()):
            pass # TODO Error
        self.cm.start(cmd)

    def stop(self, cmd: str) -> None:
        """
        Stops a container

        :param cmd: The rest of the command sent
        """
        pass

    def send_file(self, cmd: str) -> None:
        """
        Sends a file to a container

        :param cmd: The rest of the command sent
        """
        pass

    def get_file(self, cmd: str) -> None:
        """
        Gets a file from a container

        :param cmd: The rest of the command sent
        """
        pass

    def install(self, cmd: str) -> None:
        """
        Installs a container from an archive

        :param cmd: The rest of the command sent
        """
        pass

    def delete(self, cmd: str) -> None:
        """
        Deletes a container from the file system

        :param cmd: The rest of the command sent
        """
        pass

    def download(self, cmd: str) -> None:
        """
        Downloads a container from an archive

        :param cmd: The rest of the command sent
        """
        pass

    def archive(self, cmd: str) -> None:
        """
        Sends a container to an archive

        :param cmd: The rest of the command sent
        """
        pass

    def add_repo(self, cmd: str) -> None:
        """
        Adds an archive to the system

        :param cmd: The rest of the command sent
        """
        pass

    def update_repo(self, cmd: str) -> None:
        """
        Updates an archive

        :param cmd: The rest of the command sent
        """
        pass

    def create(self, cmd: str) -> None:
        """
        Runs the container creation wizard

        :param cmd: The rest of the command sent
        """
        pass