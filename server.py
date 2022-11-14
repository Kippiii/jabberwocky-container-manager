from src.containers.container_manager_server import ContainerManagerServer
from src.system.syspath import get_server_addr_file
import logging
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
server = ContainerManagerServer(logger=logger)

try:
    server.listen()
except Exception as ex:
    os.remove(get_server_addr_file())
    raise ex
