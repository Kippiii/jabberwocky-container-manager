import socket
import logging
import threading
from src.containers.container_manager_server import ContainerManagerServer
from src.containers.container_manager_client import ContainerManagerClient


logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

server = ContainerManagerServer(logger)
t = threading.Thread(target=server.start_server)
t.start()

client = ContainerManagerClient()

try:
    client.start('ct')
    client.run_command('ct', ['rm', '-f', 'echo.c', 'a.out'])
    client.put_file('ct', 'echo.c', 'echo.c')
    client.run_command('ct', ['sparc-linux-gcc', 'echo.c'])
    client.run_command('ct', ['./a.out'])
    client.run_command('ct', ['./a.out'])
    client.get_file('ct', 'a.out', 'a.out')
except Exception as ex:
    client.stop('ct')
    print(ex)
else:
    client.stop('ct')
finally:
    client.server_halt()

print('Program Finished')