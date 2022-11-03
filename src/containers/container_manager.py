import logging
from typing import Dict

from src.containers.container import Container
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

    def start(self, container_name: str) -> None:
        """
        Starts a container

        :param container_name: The container being started
        """
        self.logger.debug("Starting container '%s'", container_name)
        if container_name in self.containers:
            return  # Raise exception
        self.containers[container_name] = Container(
            container_name, logger=self.logger
        )
        self.containers[container_name].start()

    def stop(self, container_name: str) -> None:
        """
        Stops a container

        :param container_name: The container being stopped
        """
        self.logger.debug("Stopping container '%s'", container_name)
        if container_name not in self.containers:
            return  # Raise exception
        self.containers[container_name].stop()
        del self.containers[container_name]

    def run_shell(self, container_name: str) -> None:
        """
        Starts a shell on the container in question

        :param container_name: The container whose shell is being used
        """
        self.logger.debug("Opening shell on container '%s'", container_name)
        if container_name not in self.containers:
            return # Raise exception
        self.containers[container_name].shell()

    def run_command(self, container_name: str, cmd: str, *args, **kwargs) -> None:
        """
        Runs a command in a contianer

        :param container_name: The container with the command being run
        :param cmd: The command being run
        """
        self.logger.debug("Running command '%s' in '%s'", cmd, container_name)
        if container_name not in self.containers:
            return  # Raise exception
        self.containers[container_name].run(cmd, *args, **kwargs)

    def get_file(self, container_name: str, remote_file: str, local_file: str) -> None:
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
            return  # Raise exception
        self.containers[container_name].get(remote_file, local_file)

    def put_file(self, container_name: str, local_file: str, remote_file: str) -> None:
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
            return  # Raise exception
        self.containers[container_name].put(local_file, remote_file)
