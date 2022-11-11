import socket
import threading
import logging
from paramiko.channel import ChannelStdinFile, ChannelFile, ChannelStderrFile
from typing import Optional, Tuple, Dict, List

from src.containers.container import Container
from src.containers.exceptions import BootFailure
from src.system.syspath import get_container_dir


class ContainerManagerServer:
    backlog: int = 20
    address: Tuple[str, int] = (socket.gethostname(), 35053)
    server_sock: Optional[socket.socket] = None
    containers: Dict[str, Container] = {}
    logger: logging.Logger


    def __init__(self, logger: logging.Logger):
        self.logger = logger


    def listen(self) -> None:
        logging.debug(f'Starting Container Manager Server @ {self.address}')
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.bind(self.address)
        self.server_sock.listen(self.backlog)

        try:
            while True:
                client_sock, client_addr = self.server_sock.accept()
                logging.debug(f'Accepted connection from {client_addr}')
                threading.Thread(
                    target=_SocketConnection(client_sock, client_addr, self).start_connection
                ).start()
        except OSError:
            pass # TODO: shut down all containers


class _SocketConnection:
    manager: ContainerManagerServer
    client_sock: socket.socket
    client_addr: Tuple[str, int]


    def __init__(self, client_sock: socket.socket, client_addr: Tuple[str, int], manager: ContainerManagerServer):
        self.client_sock = client_sock
        self.client_addr = client_addr
        self.manager = manager


    def start_connection(self) -> None:
        self.client_sock.send(b'READY')

        try:
            msg = self.client_sock.recv(1024)

            if msg == b'HALT':
                self.client_sock.close()
                self.manager.server_sock.close()
                return

            {
                b'RUN-COMMAND': self._run_command,
                b'GET-FILE': self._get,
                b'PUT-FILE': self._put,
                b'START': self._start,
                b'STOP': self._stop,
            }[msg]()

        except KeyError:
            self.client_sock.send(b'UNKNOWN_REQUEST')
        except ConnectionError:
            pass
        except Exception as ex:
            self.client_sock.send(b'EXCEPTION_OCCURED')
            self.manager.logger.exception(ex)

        self.client_sock.close()


    def _run_command(self) -> None:
        self.client_sock.send(b'CONT')
        container_name = self.client_sock.recv(1024).decode('utf-8')
        self.client_sock.send(b'CONT')
        cli_len = int(self.client_sock.recv(1024))

        cli = []
        for _ in range(cli_len):
            self.client_sock.send(b'CONT')
            cli.append(self.client_sock.recv(1024).decode('utf-8'))

        if not get_container_dir(container_name).is_dir():
            self.client_sock.send(b'NO_SUCH_CONATINER')
            return

        self.client_sock.send(b'BEGIN')

        stdin, stdout, stderr = self.manager.containers[container_name].run(' '.join(cli))
        _RunCommandHandler(
            client_sock=self.client_sock,
            client_addr=self.client_addr,
            manager=self.manager,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr
        ).send_and_recv()


    def _start(self) -> None:
        self.client_sock.send(b'CONT')
        container_name = self.client_sock.recv(1024).decode('utf-8')

        if not get_container_dir(container_name).is_dir():
            self.client_sock.send('NO_SUCH_CONTAINER')

        elif container_name not in self.manager.containers:
            try:
                self.manager.logger.debug("Starting container '%s'", container_name)
                self.manager.containers[container_name] = Container(
                    container_name, logger=self.manager.logger
                )
                self.manager.containers[container_name].start()
            except BootFailure:
                self.client_sock.send(b'BOOT_FAILURE')
            else:
                self.client_sock.send(b'OK')


    def _stop(self) -> None:
        self.client_sock.send(b'CONT')
        container_name = self.client_sock.recv(1024).decode('utf-8')

        if container_name not in self.manager.containers:
            self.client_sock.send('NO_SUCH_CONTAINER')
        else:
            self.manager.logger.debug("Stopping container '%s'", container_name)
            self.manager.containers[container_name].stop()
            del self.manager.containers[container_name]
            self.client_sock.send(b'OK')


    def _get(self) -> None:
        self.client_sock.send(b'CONT')
        container_name = self.client_sock.recv(1024).decode('utf-8')
        self.client_sock.send(b'CONT')
        remote_file = self.client_sock.recv(1024).decode('utf-8')
        self.client_sock.send(b'CONT')
        local_file = self.client_sock.recv(1024).decode('utf-8')

        self.manager.logger.debug(
            "Getting file '%s' to '%s' in '%s'", remote_file, local_file, container_name
        )

        if container_name not in self.manager.containers:
            self.client_sock.send(b'CONTAINER_NOT_STARTED')
        else:
            self.manager.containers[container_name].get(remote_file, local_file)
            self.client_sock.send(b'OK')


    def _put(self) -> None:
        self.client_sock.send(b'CONT')
        container_name = self.client_sock.recv(1024).decode('utf-8')
        self.client_sock.send(b'CONT')
        local_file = self.client_sock.recv(1024).decode('utf-8')
        self.client_sock.send(b'CONT')
        remote_file = self.client_sock.recv(1024).decode('utf-8')

        self.manager.logger.debug(
            "Putting file '%s' to '%s' in '%s'", local_file, remote_file, container_name
        )


        if container_name not in self.manager.containers:
            self.client_sock.send(b'CONTAINER_NOT_STARTED')
        else:
            self.manager.containers[container_name].put(local_file, remote_file)
            self.client_sock.send(b'OK')



class _RunCommandHandler:
    manager: ContainerManagerServer
    client_sock: socket.socket
    client_addr: Tuple[str, int]

    stdin:  Optional[ChannelStdinFile] = None
    stdout: Optional[ChannelFile] = None
    stderr: Optional[ChannelStderrFile] = None
    stdout_closed: Optional[bool] = None
    stderr_closed: Optional[bool] = None

    def __init__(self, client_sock: socket.socket, client_addr: Tuple[str, int], manager: ContainerManagerServer, stdin: ChannelStdinFile, stdout: ChannelFile, stderr: ChannelStderrFile):
        self.client_sock = client_sock
        self.client_addr = client_addr
        self.manager = manager
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

    def send_and_recv(self):
        self.stdout_closed = False
        self.stderr_closed = False

        t_send_stdout = threading.Thread(target=self._send_stdout)
        t_send_stderr = threading.Thread(target=self._send_stderr)
        t_recv        = threading.Thread(target=self._recv)
        t_send_stdout.start()
        t_send_stderr.start()
        t_recv.start()
        t_send_stdout.join()
        t_send_stderr.join()
        t_recv.join()


    def _recv(self):
        try:
            while msg := self.client_sock.recv(1024):
                self.stdin.write(msg)
        except ConnectionError:
            pass

    def _send_stdout(self):
        try:
            while b := self.stdout.read(1):
                self.client_sock.send(b)
        except ConnectionError as ex:
            self.manager.logger.exception(ex)
        finally:
            self.stdout_closed = True
            if self.stderr_closed:
                self.client_sock.close()

    def _send_stderr(self):
        try:
            while b := self.stderr.read(1):
                self.client_sock.send(b)
        except ConnectionError as ex:
            self.manager.logger.exception(ex)
        finally:
            self.stderr_closed = True
            if self.stdout_closed:
                self.client_sock.close()
