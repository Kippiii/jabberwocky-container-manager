import logging
from sys import stdin, stdout, argv
from pathlib import Path
import subprocess
import time
import os
import sys

from src.containers.container_manager_client import ContainerManagerClient
from src.system.syspath import get_server_addr_file
from src.cli.cli import JabberwockyCLI

PYTHON_PATH = "C:\\Users\\iworz\\AppData\\Local\\pypoetry\\Cache\\virtualenvs\\jabberwocky-container-manager-TNO-nxlu-py3.10\\Scripts\\pythonw.exe"
def main():
    logging.basicConfig()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    if not get_server_addr_file().is_file():
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
        time.sleep(1)

    cli = JabberwockyCLI(stdin, stdout)
    cli.container_manager = ContainerManagerClient()
    inp = " ".join(argv[1:])
    cli.parse_cmd(inp)


if __name__ == "__main__":
    main()
