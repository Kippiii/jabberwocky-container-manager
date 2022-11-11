from src.containers.container_manager_server import ContainerManagerServer
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
server = ContainerManagerServer(logger=logger)

server.listen()