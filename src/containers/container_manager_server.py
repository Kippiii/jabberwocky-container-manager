"""
The server version of the container manager
"""

import logging
import psutil
import os
import time
import json
import socket
import threading
from typing import Dict, Optional, Tuple
from signal import SIGABRT
from pathlib import Path

from paramiko.channel import ChannelFile, ChannelStderrFile, ChannelStdinFile
from paramiko import SSHException

from src.containers.container import Container
from src.containers.port_allocation import allocate_port
from src.containers.exceptions import BootFailure, PoweroffBadExitError
from src.system.syspath import get_container_dir, get_server_info_file, install_container
from src.system.socket import ClientServerSocket


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

        self.address = (socket.gethostbyname("127.0.0.1"), allocate_port(22300))
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
        for name, container in self.containers.items():
            self.logger.debug("Closing %s", name)
            try:
                container.stop()
                self.logger.info(f"Shut down {name}@{container.booter.pid}.")
            except (PoweroffBadExitError, SSHException):
                container.kill()
                self.logger.info(f"Killed {name}@{container.booter.pid}.")

        self.logger.info("Server going down NOW!")
        os.kill(os.getpid(), SIGABRT)

    def panic(self, reason: Optional[str] = None) -> None:
        """
        Kills indiscriminately all QEMU processes on the system, then calls stop()
        """
        self.logger.error(f"PANICKING!!! Reason given: {reason}")
        for p in psutil.process_iter():
            if "qemu-system-" in p.name().lower():
                p.kill()
                self.logger.error(f"KILLED {p.pid}!")
        self.logger.info("Server going down NOW!")
        os.kill(os.getpid(), SIGABRT)


class _SocketConnection:
    """
    Internal class used by ContaienrManagerServer to handle an individual connection.

    :param manager: The parent ContainerManagerServer object
    :param client_sock: Client socket
    :param client_addr: (IP, PORT) of the client
    """

    manager: ContainerManagerServer
    sock: ClientServerSocket
    client_addr: Tuple[str, int]

    def __init__(
        self,
        client_sock: socket.socket,
        client_addr: Tuple[str, int],
        manager: ContainerManagerServer,
    ):
        self.sock = ClientServerSocket(client_sock)
        self.client_addr = client_addr
        self.manager = manager

    def start_connection(self) -> None:
        """
        Facilitates the communication between the server and the inidivual client.
        Blocking function.
        """

        self.sock.send(b"READY")

        try:
            msg = self.sock.recv(1024)
            self.manager.logger.debug("Recieves %s from the client", msg)

            if msg == b"HALT":
                self.manager.stop()
                return
            if msg == b"PANIC":
                self.manager.panic("Received PANIC command.")

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
                b"INSTALL": self._install,
                b"STARTED": self._started,
            }[msg]()

        except KeyError:
            self.sock.raise_unknown_request(msg)
        except (ConnectionError, OSError) as ex:
            self.manager.logger.exception(ex)
            self.sock.raise_exception()
        except Exception as ex:  # pylint: disable=broad-except
            self.manager.logger.exception(ex)
            self.sock.raise_exception()
        finally:
            self.sock.close()

    def _ping(self) -> None:
        """
        Pong!
        """
        self.manager.logger.debug("Ponging the client")
        self.sock.send(b"PONG")

    def _started(self) -> None:
        self.sock.cont()
        container_name = self.sock.recv().decode("utf-8")
        self.manager.logger.debug("Checking if container %s is started", container_name)

        if container_name in self.manager.containers:
            self.sock.yes()
        else:
            self.sock.no()

    def _address(self) -> None:
        """
        Sends the information necessary to SSH into the container's shell
        in the form of "HOSTNAME:PORT:USERNAME"
        """
        self.sock.cont()
        container_name = self.sock.recv().decode("utf-8")

        if container_name not in self.manager.containers:
            self.manager.logger.debug("Attempt to get SSH info for container %s, but it was not started", container_name)
            self.sock.raise_container_not_started(container_name)
        else:
            host = "127.0.0.1"
            pswd = self.manager.containers[container_name].password
            port = self.manager.containers[container_name].ex_port
            user = self.manager.containers[container_name].username
            self.manager.logger.debug(f"Container {container_name} SSH info: ({user}:{pswd}@{host}:{port})")
            self.sock.send(f"{user}:{pswd}:{host}:{port}".encode("utf-8"))

    def _update_hostkey(self) -> None:
        """
        Generates a new id_rsa and updates the container
        """
        self.sock.cont()
        container_name = self.sock.recv()
        self.manager.logger.debug("Updating hostkey of container %s", container_name)

        if container_name not in self.manager.containers:
            self.sock.raise_container_not_started(container_name)
        else:
            self.manager.containers[container_name].sshi.update_hostkey()
            self.sock.ok()

    def _run_command(self) -> None:
        """
        Runs a command in a contianer
        """
        self.sock.cont()
        container_name = self.sock.recv().decode("utf-8")
        self.sock.cont()
        cli_len = int(self.sock.recv())

        cli = []
        for _ in range(cli_len):
            self.sock.cont()
            cli.append(self.sock.recv().decode("utf-8"))

        if container_name not in self.manager.containers:
            self.sock.raise_container_not_started()
            return

        self.manager.logger.debug("On container %s, running %s", container_name, ' '.join(cli))

        self.sock.send(b"BEGIN")

        stdin, stdout, stderr = self.manager.containers[container_name].run(
            " ".join(cli)
        )
        _RunCommandHandler(
            client_sock=self.sock,
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
        self.sock.cont()
        container_name = self.sock.recv().decode("utf-8")
        self.manager.logger.debug("Attempting to start container %s", container_name)

        if not get_container_dir(container_name).is_dir():
            self.manager.logger.debug("Container %s does not exist", container_name)
            self.sock.raise_no_such_container(container_name)

        elif container_name not in self.manager.containers:
            try:
                self.manager.logger.debug("Starting container '%s'", container_name)
                self.manager.containers[container_name] = Container(
                    container_name, logger=self.manager.logger
                )
                self.manager.containers[container_name].start()
                self.manager.logger.debug("Container %s has been started", container_name)
            except BootFailure as exc:
                self.manager.logger.debug("Container %s failed to boot: %s", container_name, repr(exc))
                self.sock.raise_boot_error()
            else:
                self.sock.ok()

    def _stop(self) -> None:
        """
        Stops a container
        """
        self.sock.cont()
        container_name = self.sock.recv().decode("utf-8")

        if container_name not in self.manager.containers:
            self.manager.logger.debug("Attempt to stop nonexistent container %s", container_name)
            self.sock.raise_container_not_started(container_name)
            return

        self.manager.logger.debug("Stopping container '%s'", container_name)
        self.manager.containers[container_name].stop()
        del self.manager.containers[container_name]
        self.sock.ok()
        self.manager.logger.debug("Container %s successfully stopped", container_name)

    def _kill(self) -> None:
        """
        Kills the QEMU process of the container.
        This is like yanking the power cord. Only use when you have no other choice.
        """
        self.sock.cont()
        container_name = self.sock.recv().decode("utf-8")

        if container_name not in self.manager.containers:
            self.manager.logger.debug("Attempt to kill nonexistent container %s", container_name)
            self.sock.raise_container_not_started(container_name)
            return

        self.manager.logger.debug("Killing container '%s'", container_name)
        self.manager.containers[container_name].kill()
        del self.manager.containers[container_name]
        self.sock.ok()
        self.manager.logger.debug("Container %s successfully killed", container_name)

    def _get(self) -> None:
        """
        Gets a file from a container
        """
        self.sock.cont()
        container_name = self.sock.recv().decode("utf-8")
        self.sock.cont()
        remote_file = self.sock.recv().decode("utf-8")
        self.sock.cont()
        local_file = self.sock.recv().decode("utf-8")

        self.manager.logger.debug(
            "Getting file '%s' to '%s' in '%s'", remote_file, local_file, container_name
        )

        if container_name not in self.manager.containers:
            self.manager.logger.debug("Attempt to get file from nonexistent container %s", container_name)
            self.sock.raise_container_not_started(container_name)
            return

        try:
            self.manager.containers[container_name].get(remote_file, local_file)
        except FileNotFoundError:
            self.sock.raise_invalid_path(remote_file)
        except IsADirectoryError:
            self.sock.raise_is_a_directory(remote_file)
        else:
            self.sock.ok()

    def _put(self) -> None:
        """
        Puts a file into a container
        """
        self.sock.cont()
        container_name = self.sock.recv().decode("utf-8")
        self.sock.cont()
        local_file = self.sock.recv().decode("utf-8")
        self.sock.cont()
        remote_file = self.sock.recv().decode("utf-8")

        self.manager.logger.debug(
            "Putting file '%s' to '%s' in '%s'", local_file, remote_file, container_name
        )

        if container_name not in self.manager.containers:
            self.manager.logger.debug("Attempt to put file into nonexistent container %s", container_name)
            self.sock.raise_container_not_started(container_name)
            return
        try:
            self.manager.containers[container_name].put(local_file, remote_file)
        except FileNotFoundError:
            self.sock.raise_invalid_path(local_file)
        except IsADirectoryError:
            self.sock.raise_is_a_directory(local_file)
        else:
            self.sock.ok()

    def _install(self) -> None:
        """
        Installs a container on the system
        """
        self.sock.cont()
        archive_path_str = self.sock.recv().decode("utf-8")
        self.sock.cont()
        container_name = self.sock.recv().decode("utf-8")

        self.manager.logger.debug(
            "Installing container '%s' from '%s'", archive_path_str, container_name
        )

        archive_path = Path(archive_path_str)
        if not archive_path.is_file():
            self.manager.logger.debug("Attempt to install container from invalid path")
            self.sock.raise_invalid_path(archive_path_str)
            return
        install_container(archive_path, container_name)

        self.sock.ok()
        self.manager.logger.debug("Successfully installed container %s", container_name)


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
            while msg := self.client_sock.recv(1 << 16):
                while msg:
                    size = msg[0]
                    self.stdin.write(msg[1:size + 1])
                    msg = msg[size + 1:]
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
                time.sleep(0.25)
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
                time.sleep(0.25)
                self.client_sock.close()
