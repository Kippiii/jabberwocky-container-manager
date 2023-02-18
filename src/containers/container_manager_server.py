"""
The server version of the container manager
"""

import logging
import psutil
import os
import sys
import time
import json
import shutil
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
from src.containers.container_extras import install_container, archive_container
from src.system.syspath import get_container_dir, get_server_info_file
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
    startup_mutex: threading.Lock = threading.Lock()
    halt_event: threading.Event = threading.Event()

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def listen(self) -> None:
        """
        Listens for incoming connections. Blocking function.
        """

        self.address = (socket.gethostbyname("127.0.0.1"), allocate_port(22300))
        self.logger.debug("MAIN THREAD: Starting Container Manager Server @ %s", self.address)
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

        threading.Thread(target=self._listen, daemon=True).start()
        self.halt_event.wait()
        self.logger.debug("MAIN THREAD: HALT event reached. Stopping.")
        self.server_sock.close()
        self.stop()
        self.logger.debug("MAIN THREAD: Exiting NOW.")
        sys.exit()

    def _listen(self):
        try:
            while True:
                client_sock, client_addr = self.server_sock.accept()
                self.logger.debug("MAIN THREAD: Accepted connection from %s", client_addr)
                threading.Thread(
                    target=_SocketConnection(
                        client_sock, client_addr, self
                    ).start_connection, daemon=True
                ).start()
        except Exception as ex:  # pylint: disable=broad-except
            self.logger.exception(ex)
            self.halt_event.set()

    def stop(self) -> None:
        """
        Stops the container manager server
        """
        for name, container in self.containers.items():
            self.logger.debug("STOP: Closing %s", name)
            try:
                container.stop()
                self.logger.debug(f"STOP: Poweroff'd {name} (PID={container.booter.pid}).")
            except (PoweroffBadExitError, SSHException, AttributeError):
                try:
                    self.logger.error(f"STOP: POWEROFF FAILED. Killing {name} (PID={container.booter.pid}).")
                    container.kill()
                except (PermissionError, AttributeError) as exc:
                    msg = f"STOP: COULD NOT KILL {name} (PID={container.booter.pid}). " \
                          f"Reason: {type(exc).__name__}. (The process is probably dead.)"
                    self.logger.error(msg)
                else:
                    self.logger.info(f"STOP: Killed {name}@{container.booter.pid}.")

        os.remove(get_server_info_file())
        self.logger.debug("STOP: STOP complete.")

    def panic(self, reason: Optional[str] = None) -> None:
        """
        Kills indiscriminately all QEMU processes on the system, then calls stop()
        """
        self.logger.error(f"PANICKING!!! Reason given: {reason}")
        for p in psutil.process_iter():
            if "qemu-system-" in p.name().lower():
                p.kill()
                self.logger.error(f"PANIC: KILLED {p.pid}!")
        os.remove(get_server_info_file())
        self.logger.debug("PANIC: Server will ABORT now.")
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
            self.manager.logger.debug("Recieved %s from the client", msg)

            if msg == b"HALT":
                self.manager.halt_event.set()
                return
            if msg == b"PANIC":
                self.manager.panic("Received PANIC command.")
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
                b"INSTALL": self._install,
                b"DELETE": self._delete,
                b"RENAME": self._rename,
                b"STARTED": self._started,
                b"ARCHIVE": self._archive,
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
        self.manager.logger.debug("Responding to ping.")
        self.sock.ok()

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

        stdin, stdout, stderr, pid = self.manager.containers[container_name].run(cli)
        _RunCommandHandler(
            client_sock=self.sock,
            client_addr=self.client_addr,
            manager=self.manager,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            pid=pid,
            container=self.manager.containers[container_name]
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

        self.manager.startup_mutex.acquire()
        try:
            if container_name not in self.manager.containers:
                try:
                    self.manager.logger.debug("Starting container '%s'", container_name)
                    self.manager.containers[container_name] = Container(
                        container_name, logger=self.manager.logger
                    )
                    self.manager.containers[container_name].start()
                    self.manager.logger.debug("Container %s has been started", container_name)
                except BootFailure as exc:
                    self.manager.logger.debug("Container %s failed to boot: %s", container_name, repr(exc))
                    self.manager.containers[container_name].kill()
                    del self.manager.containers[container_name]
                    self.sock.raise_boot_error()
                else:
                    self.sock.ok()
            else:
                self.sock.ok()
        except Exception as exc:  # pylint: disable=broad-except
            self.manager.startup_mutex.release()
            raise exc
        else:
            self.manager.startup_mutex.release()

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

    def _archive(self) -> None:
        """
        Archives a container onto the disk
        """
        self.sock.cont()
        container_name = self.sock.recv().decode('utf-8')
        self.sock.cont()
        path_to_destination: str = self.sock.recv().decode('utf-8')

        if not get_container_dir(container_name).is_dir():
            self.manager.logger.debug("Container %s does not exist", container_name)
            self.sock.raise_no_such_container(container_name)
            return
        if container_name in self.manager.containers:
            self.manager.logger.debug("Attempt to archive started container")
            self.sock.raise_container_started_cannot_modify(container_name)
            return

        try:
            archive_container(container_name, path_to_destination)
        except FileExistsError:
            self.sock.raise_invalid_path(str(path_to_destination))
        else:
            self.sock.ok()

    def _delete(self) -> None:
        """
        Deletes a container from the file system
        """
        self.sock.cont()
        container_name: str = self.sock.recv().decode('utf-8')

        self.manager.logger.debug("Deleting container %s", container_name)

        if not get_container_dir(container_name).is_dir():
            self.manager.logger.debug("Attempt to delete container that does not exist")
            self.sock.raise_no_such_container(container_name)
            return
        if container_name in self.manager.containers:
            self.manager.logger.debug("Attempt to delete started container")
            self.sock.raise_container_started_cannot_modify(container_name)
            return

        shutil.rmtree(get_container_dir(container_name))

        self.sock.ok()
        self.manager.logger.debug("Successfully deleted container %s", container_name)

    def _rename(self) -> None:
        """
        Renames a container on the file system
        """
        self.sock.cont()
        old_name: str = self.sock.recv().decode('utf-8')
        self.sock.cont()
        new_name: str = self.sock.recv().decode('utf-8')

        self.manager.logger.debug("Renaming container '%s' to '%s'", old_name, new_name)

        if not get_container_dir(old_name).is_dir():
            self.manager.logger.debug("Attempt to rename container that does not exist")
            self.sock.raise_no_such_container(old_name)
            return
        if old_name in self.manager.containers:
            self.manager.logger.debug("Attempt to rename started container")
            self.sock.raise_container_started_cannot_modify(old_name)
            return


        os.rename(str(get_container_dir(old_name)), str(get_container_dir(new_name)))

        self.sock.ok()
        self.manager.logger.debug("Successfully renamed container")


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

    container: Container
    pid: int
    stdin: ChannelStdinFile
    stdout: ChannelFile
    stderr: ChannelStderrFile
    mutex: threading.Lock = threading.Lock()

    def __init__(
        self,
        client_sock: socket.socket,
        client_addr: Tuple[str, int],
        manager: ContainerManagerServer,
        stdin: ChannelStdinFile,
        stdout: ChannelFile,
        stderr: ChannelStderrFile,
        pid: int,
        container: Container,
    ):
        self.client_sock = client_sock
        self.client_addr = client_addr
        self.manager = manager
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pid = pid
        self.container = container

    def send_and_recv(self):
        """
        Sends output, receives input. Blocking function.
        """
        t_send_stdout = threading.Thread(target=self._send_stdout, daemon=True)
        t_send_stderr = threading.Thread(target=self._send_stderr, daemon=True)
        t_send_null = threading.Thread(target=self._send_null, daemon=True)
        t_recv = threading.Thread(target=self._recv, daemon=True)
        t_send_stdout.start()
        t_send_stderr.start()
        t_recv.start()
        t_send_null.start()

        while True:
            if not (t_recv.is_alive() and t_send_null.is_alive()):
                break
            if not (t_send_stdout.is_alive() or t_send_stderr.is_alive()):
                break
            time.sleep(1)
        self.client_sock.close()
        self.container.sshi.exec_ssh_command(["kill", "-9", str(self.pid)])

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
                self.mutex.acquire()
                self.client_sock.send(b"\x01" + my_byte)
                self.mutex.release()
        except (ConnectionError, OSError) as ex:
            if self.mutex.locked():
                self.mutex.release()

    def _send_stderr(self):
        try:
            while my_byte := self.stderr.read(1):
                self.mutex.acquire()
                self.client_sock.send(b"\x02" + my_byte)
                self.mutex.release()
        except (ConnectionError, OSError) as ex:
            if self.mutex.locked():
                self.mutex.release()

    def _send_null(self):
        try:
            while True:
                self.mutex.acquire()
                self.client_sock.send(b"\x00\x00")
                self.mutex.release()
                time.sleep(1)
        except (ConnectionError, OSError) as ex:
            if self.mutex.locked():
                self.mutex.release()
