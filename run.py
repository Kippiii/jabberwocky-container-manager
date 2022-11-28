import logging
from sys import stdin, stdout, argv
from pathlib import Path
import subprocess
import psutil
import time
import os
import sys
import json

from src.containers.container_manager_client import ContainerManagerClient
from src.system.syspath import get_server_info_file
from src.cli.cli import JabberwockyCLI


def _server_is_running() -> bool:
    """
    Determines if the server is running.

    :return: True is sever is running, False if not.
    """
    if not get_server_info_file().is_file():
        return False

    with open(get_server_info_file(), "r", encoding="utf-8") as f:
        info = json.load(f)
        pid  = info["pid"]
        boot = info["boot"]
        return boot > psutil.boot_time() and psutil.pid_exists(pid)


def main():
    logging.basicConfig()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    if not _server_is_running():
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
