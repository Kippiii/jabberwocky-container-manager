from src.containers.container_manager_server import ContainerManagerServer
from src.system.syspath import get_server_log_file, get_server_info_file
import logging
import psutil
import json
import os


def server_is_running() -> bool:
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
    
    if boot > psutil.boot_time() and psutil.pid_exists(pid):
        return True
    else:
        os.remove(get_server_info_file())
        return False


if __name__ == "__main__":
    logging.basicConfig(filename=get_server_log_file(), filemode="w")
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    server = ContainerManagerServer(logger=logger)

    try:
        server.listen()
    except Exception as ex:
        raise ex
