"""
The client version of the container manager
"""

import msvcrt
import select
import socket
import sys
import threading
import time
from os.path import abspath
from typing import List, Tuple

from src.system.syspath import get_server_addr_file


class ContainerManagerClient:
    """
    Sends requests to the ContainerManagerServer

    :param server_address: (IP, PORT) of the server.
    """

    server_address: Tuple[str, int]

    def __init__(self):
        with open(get_server_addr_file(), "r", encoding="utf-8") as server_addr:
            addr, port = server_addr.read().split("\n")
            self.server_address = (addr, int(port))

    def start(self, container_name: str) -> None:
        """
        Starts a container

        :param container_name: The container being started
        """
        sock = self._make_connection()
        sock.send(b"START")
        self._recv_expect(sock, 1024, b"CONT")
        sock.send(bytes(container_name, "utf-8"))
        self._recv_expect(sock, 1024, b"OK")
        sock.close()

    def stop(self, container_name: str) -> None:
        """
        Stops a container

        :param container_name: The container being stopped
        """
        sock = self._make_connection()
        sock.send(b"STOP")
        self._recv_expect(sock, 1024, b"CONT")
        sock.send(bytes(container_name, "utf-8"))
        self._recv_expect(sock, 1024, b"OK")
        sock.close()

    def run_shell(self, cli: List[str]) -> None:
        """
        Starts a shell on the container in question

        :param container_name: The container whose shell is being used
        """
        raise NotImplementedError()

    def get_file(self, container_name: str, remote_file: str, local_file: str) -> None:
        """
        Gets a file from a container

        :param container_name: The container where the file is obtained from
        :param remote_file: The file obtained from the container
        :param local_file: Where the file obtained from the container is placed
        """
        absolute_local_path = abspath(local_file)

        sock = self._make_connection()
        sock.send(b"GET-FILE")
        self._recv_expect(sock, 1024, b"CONT")
        sock.send(bytes(container_name, "utf-8"))
        self._recv_expect(sock, 1024, b"CONT")
        sock.send(bytes(remote_file, "utf-8"))
        self._recv_expect(sock, 1024, b"CONT")
        sock.send(bytes(absolute_local_path, "utf-8"))
        self._recv_expect(sock, 1024, b"OK")
        sock.close()

    def put_file(self, container_name: str, local_file: str, remote_file: str) -> None:
        """
        Puts a file into a container

        :param container_name: The container where the file is placed
        :param local_file: The file being put into the container
        :param remote_file: Where the file will be placed in the container
        """
        absolute_local_path = abspath(local_file)

        sock = self._make_connection()
        sock.send(b"PUT-FILE")
        self._recv_expect(sock, 1024, b"CONT")
        sock.send(bytes(container_name, "utf-8"))
        self._recv_expect(sock, 1024, b"CONT")
        sock.send(bytes(absolute_local_path, "utf-8"))
        self._recv_expect(sock, 1024, b"CONT")
        sock.send(bytes(remote_file, "utf-8"))
        self._recv_expect(sock, 1024, b"OK")
        sock.close()

    def run_command(self, container_name: str, cli: List[str]) -> None:
        """
        Runs a command in a contianer

        :param container_name: The container with the command being run
        :param cmd: The command being run, as a list of arguments
        """
        sock = self._make_connection()
        sock.send(b"RUN-COMMAND")
        self._recv_expect(sock, 1024, b"CONT")
        sock.send(bytes(container_name, "utf-8"))
        self._recv_expect(sock, 1024, b"CONT")

        sock.send(bytes(str(len(cli)), "utf-8"))
        for arg in cli:
            self._recv_expect(sock, 1024, b"CONT")
            sock.send(bytes(arg, "utf-8"))

        self._recv_expect(sock, 1024, b"BEGIN")
        _RunCommandClient(sock)

    def server_halt(self) -> None:
        """
        Tells the server to halt
        """
        sock = self._make_connection()
        sock.send(b"HALT")
        sock.close()

    def _make_connection(self) -> socket.socket:
        """
        Creates a connection to the server.

        :return: The socket connection to the server.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(self.server_address)
        self._recv_expect(sock, 1024, b"READY")
        return sock

    def _recv_expect(self, sock: socket.socket, bufsize: int, expected: bytes) -> bytes:
        """
        Receives data from a socket, then checks if the data it receives is
        equal to the expected data. If it gets the expected response, return it.
        If not, raise an exception.

        :param sock: The server socket object
        :param bufsize: Buffer size to be passed to socket.recv
        :param expected: The expected data
        :return: The data received
        """
        if (msg := sock.recv(bufsize)) != expected:
            sock.close()
            raise RuntimeError(
                f'Got Unexpected Response "{msg}" from {self.server_address}'
            )
        return msg


class _RunCommandClient:
    """
    Internal class used only for run_command. This class' __init__ is
    a blocking function.

    :param sock: The server socket object
    """

    sock: socket.socket
    recv_closed: bool

    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.recv_closed = False

        t_recv = threading.Thread(target=self._recv)
        t_send = threading.Thread(
            target=self._send_msvcrt if sys.platform == "win32" else self._send_select
        )
        t_recv.start()
        t_send.start()
        t_recv.join()
        t_send.join()

    def _send_select(self) -> None:
        """
        Sends data read from stdin to the sever. POSIX only.
        """
        try:
            while not self.recv_closed:
                if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                    self.sock.send(bytes(sys.stdin.readline(), "utf-8"))
                time.sleep(0.1)
        except (ConnectionError, OSError):
            pass
        finally:
            self.sock.close()

    def _send_msvcrt(self) -> None:
        """
        Sends data read from stdin to the sever. Windows only.
        """
        try:
            msg = ""
            while not self.recv_closed:
                while msvcrt.kbhit():
                    char = msvcrt.getwche()

                    if char == "\r":
                        print(end="\n")
                        self.sock.send(bytes(msg + "\n", "utf-8"))
                        msg = ""

                    elif char == "\b":
                        print(" ", end="\b", flush=True)
                        msg = msg[:-1]

                    else:
                        msg += char

                time.sleep(0.1)
        except (ConnectionError, OSError):
            pass
        finally:
            self.sock.close()

    def _recv(self) -> None:
        """
        Receives and outputs data read from the server.
        """
        try:
            while msg := self.sock.recv(1024):
                sys.stdout.buffer.write(msg)
                sys.stdout.flush()
        except (ConnectionError, OSError):
            pass
        finally:
            self.sock.close()
            self.recv_closed = True
