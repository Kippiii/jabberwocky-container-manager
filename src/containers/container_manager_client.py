"""
The client version of the container manager
"""

import subprocess
import socket
import sys
import threading
import time
import json
import os as pyos
import requests
from os.path import abspath
from typing import List, Tuple
if sys.platform == "win32":
    import msvcrt
else:
    import select
from github import Github

from src.system.syspath import get_server_info_file, get_server_log_file, get_container_id_rsa, get_container_home
from src.globals import VERSION
from src.system.os import get_os, OS


class ContainerManagerClient:
    """
    Sends requests to the ContainerManagerServer

    :param server_address: (IP, PORT) of the server.
    """

    server_address: Tuple[str, int]

    def __init__(self):
        with open(get_server_info_file(), "r", encoding="utf-8") as f:
            info = json.load(f)
            self.server_address = (info["addr"], info["port"])

    def ping(self) -> None:
        """
        Pings the server
        """
        sock = self._make_connection()
        sock.send(b"PING")
        self._recv_expect(sock, 1024, b"PONG")

    def ssh_address(self, container_name: str) -> Tuple[str, str, str]:
        """
        Return the address (ip, port, username) needed to connect to a container's ssh

        :param container_name: The container whose shell is being used
        :return: The address
        """
        sock = self._make_connection()
        sock.send(b"SSH-ADDRESS")
        self._recv_expect(sock, 1024, b"CONT")
        sock.send(bytes(container_name, "utf-8"))
        host, port, user = sock.recv(1024).decode("utf-8").split(":")
        sock.close()
        return (host, port, user)

    def update_hostkey(self, container_name: str) -> None:
        """
        Asks the server tp generate a new id_rsa and updates the container

        :param container_name: The container to generate the keys for
        """
        sock = self._make_connection()
        sock.send(b"UPDATE-HOSTKEY")
        self._recv_expect(sock, 1024, b"CONT")
        sock.send(bytes(container_name, "utf-8"))
        self._recv_expect(sock, 1024, b"OK")

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
        self.run_command(container_name, ["cat /etc/motd"])

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

    def kill(self, container_name: str) -> None:
        """
        KIlls a container

        :param container_name: The container being stopped
        """
        sock = self._make_connection()
        sock.send(b"KILL")
        self._recv_expect(sock, 1024, b"CONT")
        sock.send(bytes(container_name, "utf-8"))
        self._recv_expect(sock, 1024, b"OK")
        sock.close()

    def run_shell(self, container_name: str) -> None:
        """
        Starts a shell on the container in question

        :param container_name: The container whose shell is being used
        """
        if not get_container_id_rsa(container_name).is_file():
            self.update_hostkey(container_name)

        host, port, user = self.ssh_address(container_name)
        subprocess.run([
            "ssh" if sys.platform == "win32" else "/usr/bin/ssh",
            "-oStrictHostKeyChecking=no",
            "-oLogLevel=ERROR",
            "-oPasswordAuthentication=no",
            f"-i{get_container_id_rsa(container_name)}",
            f"-p{port}",
            f"{user}@{host}"
        ], shell=sys.platform == "win32")

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

    def install(self, archive_path_str: str, container_name: str) -> None:
        """
        Installs a new container from a given archive path

        :param archive_path_str: The path to the archive
        :param container_name: The name of the container
        """
        absolute_archive_path = abspath(archive_path_str)

        sock = self._make_connection()
        sock.send(b"INSTALL")
        self._recv_expect(sock, 1024, b"CONT")
        sock.send(bytes(archive_path_str, "utf-8"))
        self._recv_expect(sock, 1024, b"CONT")
        sock.send(bytes(container_name, "utf-8"))
        self._recv_expect(sock, 1024, b"OK")
        sock.close()

    def server_halt(self) -> None:
        """
        Tells the server to halt
        """
        sock = self._make_connection()
        sock.send(b"HALT")
        sock.close()

    def update(self) -> None:
        """
        Searches for updates and installs them if needed
        """
        # Search for latest release
        g = Github()
        repo = g.get_repo('Kippiii/jabberwocky-container-manager')
        latest = repo.get_latest_release()

        # Compare release versions
        latest_version_num = latest.title.strip()
        if latest_version_num == VERSION:
            print("You currently have the latest version :)")
            return

        # Download release
        try:
            os = get_os()
        except ValueError as exc:
            raise ValueError(f"Unsupported platform for updates") from exc
        match os:
            case OS.WINDOWS:
                search_for = '.exe'
            case OS.MACOS:
                search_for = 'darwin'
            case OS.LINUX:
                search_for = 'linux'
            case _:
                pass
        assets = latest.get_assets()
        pos_asset = list(filter(lambda x : search_for in x.name, list(assets)))
        if len(pos_asset) == 0:
            raise ValueError("Operating system not supported by latest release :(")
        asset = pos_asset[0]
        r = requests.get(asset.browser_download_url)
        file_path = str(get_container_home() / asset.name)
        with open(file_path, 'wb') as f:
            f.write(r.content)

        # Installs update
        self.server_halt()
        if os != OS.WINDOWS:
            subprocess.run(["chmod", "+x", file_path], shell=False)
        subprocess.run([file_path], shell=sys.platform == "win32")

        # Delete executable
        pyos.remove(file_path)

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
            msg = msg.decode()
            if msg == "UNKNOWN_REQUEST":
                raise RuntimeError("Recieved invalid request")
            if msg == "NO_SUCH_CONATINER":
                raise RuntimeError("Container does not exist")
            if msg == "CONTAINER_NOT_STARTED":
                raise RuntimeError("Container has not been started")
            if msg == "BOOT_FAILURE":
                raise RuntimeError("Container failed while booting")
            if msg == "EXCEPTION_OCCURED":
                raise RuntimeError(f"An exception occured! Please check {get_server_log_file()} for more information")
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
                    buffer = bytes(sys.stdin.readline(), "utf-8")
                    while buffer:
                        msg = buffer[:255]
                        self.sock.send(bytes([len(msg)]) + msg)
                        buffer = buffer[255:]
                else:
                    self.sock.send(b"\x00")
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
                        buffer = bytes(msg + "\n", "utf-8")
                        while buffer:
                            msg = buffer[:255]
                            self.sock.send(bytes([len(msg)]) + msg)
                            buffer = buffer[255:]
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
