from src.containers.container_manager_server import ContainerManagerServer
from src.system.syspath import get_server_addr_file, get_server_log_file
import logging
import os

logging.basicConfig(filename=get_server_log_file(), filemode="a")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
server = ContainerManagerServer(logger=logger)

try:
    server.listen()
except Exception as ex:
    os.remove(get_server_addr_file())
    raise ex
