import logging
from sys import stdin, stdout
from subprocess import Popen
import time

from src.containers.container_manager_client import ContainerManagerClient
from src.containers.container_manager_server import ContainerManagerServer
from src.system.syspath import get_server_addr_file
from src.cli.cli import JabberwockyCLI


class MyInStream:
    logger: logging.Logger

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def read(self, *args, **kwargs):
        inp = stdin.read(*args, **kwargs)
        # inp = self.file.read(*args, **kwargs)
        if len(inp) > 0 and ord(inp) == 4:
            return ""
        self.logger.info("Read %d", ord(inp) if len(inp) == 1 else -1)
        return inp


def main():
    logging.basicConfig()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # Start the server
    logger.debug('Starting Server...')

    if not get_server_addr_file().is_file():
        Popen('python server.py')
        time.sleep(1)


    logger.info("Please input commands: ")
    cli = JabberwockyCLI(stdin, stdout)
    cli.container_manager = ContainerManagerClient()
    while True:
        stdout.write("> ")
        stdout.flush()
        inp = stdin.readline()
        cli.parse_cmd(inp)

    # Halt server
    # TODO


if __name__ == "__main__":
    main()
