import logging
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path
from sys import argv, exit, stdin, stdout

from server import server_is_running
from src.cli.cli import JabberwockyCLI
from src.containers.container_manager_client import ContainerManagerClient
from src.system.state import frozen
from src.system.syspath import get_server_info_file


def main():
    logging.basicConfig()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    if not server_is_running():
        if frozen():
            target = Path(sys.executable).parent.parent / "server" / "server"
        else:
            target = f'"{sys.executable}" server.py'

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
    inp = argv[1:]
    cli.parse_cmd(inp)


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        if frozen():
            traceback.print_exception(type(ex), ex, None)
            exit(1)
        else:
            raise ex
