import logging
from sys import stdin, stdout, argv
import subprocess
import time
import os

from src.containers.container_manager_client import ContainerManagerClient
from src.system.syspath import get_server_addr_file
from src.cli.cli import JabberwockyCLI


def main():
    logging.basicConfig()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    if not get_server_addr_file().is_file():
        if os.name == "nt":
            subprocess.Popen(
                "pythonw server.py",
                shell=True,
                stdin=None,
                stdout=None,
                stderr=None,
                creationflags=subprocess.DETACHED_PROCESS,
            )
        else:
            subprocess.Popen(
                "python3 server.py",
                shell=True,
                stdin=None,
                stdout=None,
                stderr=None,
            )
        time.sleep(1)

    cli = JabberwockyCLI(stdin, stdout)
    cli.container_manager = ContainerManagerClient()
    inp = " ".join(argv[1:])
    cli.parse_cmd(inp)

    # Halt server
    # TODO


if __name__ == "__main__":
    main()
