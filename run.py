import logging
from sys import stdin, stdout, argv
from pathlib import Path
import subprocess
import time
import os
import sys

from src.containers.container_manager_client import ContainerManagerClient
from src.system.syspath import get_server_info_file
from server import server_is_running
from src.cli.cli import JabberwockyCLI


def main():
    logging.basicConfig()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    if not server_is_running():
        logger.debug("Starting server...")

        if getattr(sys, 'frozen', False):
            target = Path(sys.executable).parent.parent / "server" / "server"
        else:
            target = f"\"{sys.executable}\" server.py"

        if os.name == "nt":
            subprocess.Popen(
                str(target),
                shell=True,
                stdin=None,
                stdout=None,
                stderr=None,
                creationflags=subprocess.DETACHED_PROCESS,
            )
        else:
            subprocess.Popen(
                str(target),
                shell=True,
                stdin=None,
                stdout=None,
                stderr=None,
            )

        # Wait for server to start
        timeout = 10
        begin = time.time()
        while not get_server_info_file().is_file():
            if time.time() - begin > timeout:
                raise TimeoutError("Server took too long to start.")
            else:
                time.sleep(0.5)


    cli = JabberwockyCLI(stdin, stdout)
    cli.container_manager = ContainerManagerClient()
    inp = " ".join(argv[1:])
    cli.parse_cmd(inp)


if __name__ == "__main__":
    main()
