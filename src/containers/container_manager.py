import logging
from typing import Dict
from sys import stdin, stdout

from src.containers.container import Container
from src.containers.exceptions import BootFailure
from src.system.syspath import get_container_dir


class ContainerManager:
    """
    Manages all of the containers that are in use

    :param containers: A dictionary for all of the containers
    """

    containers: Dict[str, Container] = {}
    logger: logging.Logger

    def __init__(self, *, logger: logging.Logger) -> None:
        self.logger = logger

    def start(self, container_name: str, *, in_stream=stdin, out_stream=stdout) -> None:
        """
        Starts a container

        :param container_name: The container being started
        """
        self.logger.debug("Starting container '%s'", container_name)

        if container_name in self.containers:
            out_stream.write(f"The container '{container_name}' is already running\n")
            return

        try:
            self.containers[container_name] = Container(
                container_name, logger=self.logger
            )
        except FileNotFoundError:
            out_stream.write(f"Container is not installed on the system\n")
            return
        except Exception as exc:
            out_stream.write(f"{exc}\n")
            out_stream.write("Something went wrong\n")
            return

        try:
            self.containers[container_name].start()
        except BootFailure as exc:
            out_stream.write(f"{exc}\n")
            out_stream.write(f"Ran into error while booting container\n")
            return
        except Exception as exc:
            out_stream.write(f"{exc}\n")
            out_stream.write("Something went wrong\n")
            return

    def stop(self, container_name: str, *, in_stream=stdin, out_stream=stdout) -> None:
        """
        Stops a container

        :param container_name: The container being stopped
        """
        self.logger.debug("Stopping container '%s'", container_name)

        if container_name not in self.containers:
            out_stream.write(f"There is no running container called '{container_name}'\n")
            return

        try:
            self.containers[container_name].stop()
        except Exception as exc:
            out_stream.write(f"{exc}\n")
            out_stream.write("Something went wrong\n")
            return

        del self.containers[container_name]

    def run_shell(self, container_name: str, *, in_stream=stdin, out_stream=stdout) -> None:
        """
        Starts a shell on the container in question

        :param container_name: The container whose shell is being used
        """
        self.logger.debug("Opening shell on container '%s'", container_name)

        if container_name not in self.containers:
            out_stream.write(f"There is no running container called '{container_name}'\n")
            return
        
        try:
            self.containers[container_name].shell()
        except Exception as exc:
            out_stream.write(f"{exc}\n")
            out_stream.write("Something went wrong\n")
            return

    def run_command(self, container_name: str, cmd: str, *, in_stream=stdin, out_stream=stdout) -> None:
        """
        Runs a command in a contianer

        :param container_name: The container with the command being run
        :param cmd: The command being run
        """
        self.logger.debug("Running command '%s' in '%s'", cmd, container_name)

        if container_name not in self.containers:
            out_stream.write(f"There is no running container called '{container_name}'\n")
            return
        
        try:
            self.containers[container_name].run(cmd)
        except Exception as exc:
            out_stream.write(f"{exc}\n")
            out_stream.write("Something went wrong\n")

    def get_file(self, container_name: str, remote_file: str, local_file: str, *, in_stream=stdin, out_stream=stdout) -> None:
        """
        Gets a file from a container

        :param container_name: The container where the file is obtained from
        :param remote_file: The file obtained from the container
        :param local_file: Where the file obtained from the container is placed
        """
        self.logger.debug(
            "Getting file '%s' to '%s' in '%s'", remote_file, local_file, container_name
        )

        if container_name not in self.containers:
            out_stream.write(f"There is no running container called '{container_name}'\n")
            return
        
        try:
            self.containers[container_name].get(remote_file, local_file)
        except Exception as exc:
            out_stream.write(f"{exc}\n")
            out_stream.write("Something went wrong\n")
            return

    def put_file(self, container_name: str, local_file: str, remote_file: str, *, in_stream=stdin, out_stream=stdout) -> None:
        """
        Puts a file into a container

        :param container_name: The container where the file is placed
        :param local_file: The file being put into the container
        :param remote_file: Where the file will be placed in the container
        """
        self.logger.debug(
            "Putting file '%s' to '%s' in '%s'", local_file, remote_file, container_name
        )

        if container_name not in self.containers:
            out_stream.write(f"There is no running container called '{container_name}'\n")
            return
        
        try:
            self.containers[container_name].put(local_file, remote_file)
        except Exception as exc:
            out_stream.write(f"{exc}\n")
            out_stream.write("Something went wrong\n")
            return
