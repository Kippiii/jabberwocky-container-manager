import logging
from sys import stdin, stdout, argv
from subprocess import Popen
import time

from src.containers.container_manager_client import ContainerManagerClient
from src.system.syspath import get_server_addr_file
from src.cli.cli import JabberwockyCLI


def main():
    logging.basicConfig()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # Start the server
    if not get_server_addr_file().is_file():
        logger.debug('Starting Server...')
        Popen('python server.py', shell=True)
        time.sleep(1)


    cli = JabberwockyCLI(stdin, stdout)
    cli.container_manager = ContainerManagerClient()
    inp = " ".join(argv[1:])
    cli.parse_cmd(inp)

    # Halt server
    # TODO


if __name__ == "__main__":
    main()
