"""
The server version of the container manager
"""

import logging
import os
import time
import json
import socket
import threading
from typing import Dict, Optional, Tuple
from signal import SIGABRT

from paramiko.channel import ChannelFile, ChannelStderrFile, ChannelStdinFile
from paramiko import SSHException

from src.containers.container import Container
from src.containers.port_allocation import allocate_port
from src.containers.exceptions import BootFailure, PoweroffBadExitError
from src.system.syspath import get_container_dir, get_server_info_file


class ContainerManagerServer:
    """
    Class for managing container objects. Accessed by ContainerManagerClient.

    :param backlog: Amount of socket connections the server will accept simultaneously.
    :param address: (IP, PORT) of the server.
    :param server_sock: Socket of the server.
    :param containers: A dictionary for all of the containers
    :param logger: Logger
    """

    backlog: int = 20
    address: Tuple[str, int]
    server_sock: Optional[socket.socket] = None
    containers: Dict[str, Container] = {}
    logger: logging.Logger

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def listen(self) -> None:
        """
        Listens for incoming connections. Blocking function.
        """

        self.address = (socket.gethostbyname("localhost"), allocate_port(22300))
        self.logger.debug("Starting Container Manager Server @ %s", self.address)
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.bind(self.address)
        self.server_sock.listen(self.backlog)

        server_info = {
            "addr": self.address[0],
            "port": self.address[1],
            "pid":  os.getpid(),
            "boot": time.time(),
        }

        with open(get_server_info_file(), "w", encoding="utf-8") as f:
            json.dump(server_info, f)

        try:
            while True:
                client_sock, client_addr = self.server_sock.accept()
                self.logger.debug("Accepted connection from %s", client_addr)
                threading.Thread(
                    target=_SocketConnection(
                        client_sock, client_addr, self
                    ).start_connection
                ).start()
        except (OSError, ConnectionError):
            pass

    def stop(self) -> None:
        """
        Stops the container manager server
        """

        self.logger.debug("Stopping the server")
        self.server_sock.close()
        os.remove(get_server_info_file())
        for _, container in self.containers.items():
            self.logger.debug("Closing %s", container.name)
            try:
                container.stop()
            except (PoweroffBadExitError, SSHException):
                container.kill()

        os.kill(os.getpid(), SIGABRT)


class _SocketConnection:
    """
    Internal class used by ContaienrManagerServer to handle an individual connection.

    :param manager: The parent ContainerManagerServer object
    :param client_sock: Client socket
    :param client_addr: (IP, PORT) of the client
    """

    manager: ContainerManagerServer
    client_sock: socket.socket
    client_addr: Tuple[str, int]

    def __init__(
        self,
        client_sock: socket.socket,
        client_addr: Tuple[str, int],
        manager: ContainerManagerServer,
    ):
        self.client_sock = client_sock
        self.client_addr = client_addr
        self.manager = manager

    def start_connection(self) -> None:
        """
        Facilitates the communication between the server and the inidivual client.
        Blocking function.
        """

        self.client_sock.send(b"READY")

        try:
            msg = self.client_sock.recv(1024)

            if msg == b"HALT":
                self.manager.stop()
                return

            {
                b"UPDATE-HOSTKEY": self._update_hostkey,
                b"RUN-COMMAND": self._run_command,
                b"SSH-ADDRESS": self._address,
                b"GET-FILE": self._get,
                b"PUT-FILE": self._put,
                b"START": self._start,
                b"STOP": self._stop,
                b"KILL": self._kill,
                b"PING": self._ping,
            }[msg]()

        except KeyError:
            self.client_sock.send(b"UNKNOWN_REQUEST")
        except (ConnectionError, OSError) as ex:
            self.client_sock.send(b"EXCEPTION_OCCURED")
            self.manager.logger.exception(ex)
        except Exception as ex:  # pylint: disable=broad-except
            self.client_sock.send(b"EXCEPTION_OCCURED")
            self.manager.logger.exception(ex)
        finally:
            self.client_sock.close()

    def _ping(self) -> None:
        """
        Pong!
        """
        self.client_sock.send(b"PONG")

    def _address(self) -> None:
        """
        Sends the information necessary to SSH into the container's shell
        in the form of "HOSTNAME:PORT:USERNAME"
        """
        self.client_sock.send(b"CONT")
        container_name = self.client_sock.recv(1024).decode("utf-8")

        if container_name not in self.manager.containers:
            self.client_sock.send(b"CONTAINER_NOT_STARTED")
        else:
            host = "localhost"
            port = self.manager.containers[container_name].ex_port
            user = self.manager.containers[container_name].username
            self.client_sock.send(f"{host}:{port}:{user}".encode("utf-8"))

    def _update_hostkey(self) -> None:
        """
        Generates a new id_rsa and updates the container
        """
        self.client_sock.send(b"CONT")
        container_name = self.client_sock.recv(1024).decode("utf-8")

        if container_name not in self.manager.containers:
            self.client_sock.send(b"CONTAINER_NOT_STARTED")
        else:
            self.manager.containers[container_name].sshi.update_hostkey()
            self.client_sock.send(b"OK")

    def _run_command(self) -> None:
        """
        Runs a command in a contianer
        """
        self.client_sock.send(b"CONT")
        container_name = self.client_sock.recv(1024).decode("utf-8")
        self.client_sock.send(b"CONT")
        cli_len = int(self.client_sock.recv(1024))

        cli = []
        for _ in range(cli_len):
            self.client_sock.send(b"CONT")
            cli.append(self.client_sock.recv(1024).decode("utf-8"))

        if container_name not in self.manager.containers:
            self.client_sock.send(b"CONTAINER_NOT_STARTED")
            return

        self.client_sock.send(b"BEGIN")

        stdin, stdout, stderr = self.manager.containers[container_name].run(
            " ".join(cli)
        )
        _RunCommandHandler(
            client_sock=self.client_sock,
            client_addr=self.client_addr,
            manager=self.manager,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
        ).send_and_recv()

    def _start(self) -> None:
        """
        Starts a container
        """
        self.client_sock.send(b"CONT")
        container_name = self.client_sock.recv(1024).decode("utf-8")

        if not get_container_dir(container_name).is_dir():
            self.client_sock.send("NO_SUCH_CONTAINER")

        elif container_name not in self.manager.containers:
            try:
                self.manager.logger.debug("Starting container '%s'", container_name)
                self.manager.containers[container_name] = Container(
                    container_name, logger=self.manager.logger
                )
                self.manager.containers[container_name].start()
            except BootFailure:
                self.client_sock.send(b"BOOT_FAILURE")
            else:
                self.client_sock.send(b"OK")

    def _stop(self) -> None:
        """
        Stops a container
        """
        self.client_sock.send(b"CONT")
        container_name = self.client_sock.recv(1024).decode("utf-8")

        if container_name not in self.manager.containers:
            self.client_sock.send("CONTAINER_NOT_STARTED")
            return

        self.manager.logger.debug("Stopping container '%s'", container_name)
        self.manager.containers[container_name].stop()
        del self.manager.containers[container_name]
        self.client_sock.send(b"OK")

    def _kill(self) -> None:
        """
        Kills the QEMU process of the container.
        This is like yanking the power cord. Only use when you have no other choice.
        """
        self.client_sock.send(b"CONT")
        container_name = self.client_sock.recv(1024).decode("utf-8")

        if container_name not in self.manager.containers:
            self.client_sock.send("CONTAINER_NOT_STARTED")
            return

        self.manager.logger.debug("Killing container '%s'", container_name)
        self.manager.containers[container_name].kill()
        del self.manager.containers[container_name]
        self.client_sock.send(b"OK")

    def _get(self) -> None:
        """
        Gets a file from a container
        """
        self.client_sock.send(b"CONT")
        container_name = self.client_sock.recv(1024).decode("utf-8")
        self.client_sock.send(b"CONT")
        remote_file = self.client_sock.recv(1024).decode("utf-8")
        self.client_sock.send(b"CONT")
        local_file = self.client_sock.recv(1024).decode("utf-8")

        self.manager.logger.debug(
            "Getting file '%s' to '%s' in '%s'", remote_file, local_file, container_name
        )

        if container_name not in self.manager.containers:
            self.client_sock.send(b"CONTAINER_NOT_STARTED")
        else:
            self.manager.containers[container_name].get(remote_file, local_file)
            self.client_sock.send(b"OK")

    def _put(self) -> None:
        """
        Puts a file into a container
        """
        self.client_sock.send(b"CONT")
        container_name = self.client_sock.recv(1024).decode("utf-8")
        self.client_sock.send(b"CONT")
        local_file = self.client_sock.recv(1024).decode("utf-8")
        self.client_sock.send(b"CONT")
        remote_file = self.client_sock.recv(1024).decode("utf-8")

        self.manager.logger.debug(
            "Putting file '%s' to '%s' in '%s'", local_file, remote_file, container_name
        )

        if container_name not in self.manager.containers:
            self.client_sock.send(b"CONTAINER_NOT_STARTED")
            return
        self.manager.containers[container_name].put(local_file, remote_file)
        self.client_sock.send(b"OK")


class _RunCommandHandler:
    """
    Internal class used only for run_command.

    :param manager: The parent ContainerManagerServer class
    :param client_sock: Client socket object
    :param client_addr: Client (IP, PORT)
    :param stdin: Container's stdin
    :param stdout: Container's stdout
    :param stderr: Container's stderr
    """

    manager: ContainerManagerServer
    client_sock: socket.socket
    client_addr: Tuple[str, int]

    stdin: Optional[ChannelStdinFile] = None
    stdout: Optional[ChannelFile] = None
    stderr: Optional[ChannelStderrFile] = None
    stdout_closed: Optional[bool] = None
    stderr_closed: Optional[bool] = None

    def __init__(
        self,
        client_sock: socket.socket,
        client_addr: Tuple[str, int],
        manager: ContainerManagerServer,
        stdin: ChannelStdinFile,
        stdout: ChannelFile,
        stderr: ChannelStderrFile,
    ):
        self.client_sock = client_sock
        self.client_addr = client_addr
        self.manager = manager
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

    def send_and_recv(self):
        """
        Sends output, receives input. Blocking function.
        """
        self.stdout_closed = False
        self.stderr_closed = False

        t_send_stdout = threading.Thread(target=self._send_stdout)
        t_send_stderr = threading.Thread(target=self._send_stderr)
        t_recv = threading.Thread(target=self._recv)
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
        except (ConnectionError, OSError):
            pass

    def _send_stdout(self):
        try:
            while my_byte := self.stdout.read(1):
                self.client_sock.send(my_byte)
        except (ConnectionError, OSError) as ex:
            self.manager.logger.exception(ex)
        finally:
            self.stdout_closed = True
            if self.stderr_closed:
                self.client_sock.close()

    def _send_stderr(self):
        try:
            while my_byte := self.stderr.read(1):
                self.client_sock.send(my_byte)
        except (ConnectionError, OSError) as ex:
            self.manager.logger.exception(ex)
        finally:
            self.stderr_closed = True
            if self.stdout_closed:
                self.client_sock.close()
