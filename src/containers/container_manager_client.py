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
from os import getcwd, listdir
from os.path import abspath, basename, join as joinpath, isfile, isdir
from typing import List, Tuple, Union, Optional
if sys.platform == "win32":
    import msvcrt
else:
    import select
from src.system.syspath import get_full_path

from src.system.syspath import *
from src.globals import VERSION
from src.system.os import get_os, OS
from src.containers.exceptions import *
from src.system.socket import ClientServerSocket
from src.system.filezilla import filezilla, sftp


class ContainerManagerClient:
    """
    Sends requests to the ContainerManagerServer

    :param server_address: (IP, PORT) of the server.
    """

    server_address: Tuple[str, int]

    def __init__(self, in_stream=sys.stdin, out_stream=sys.stdout):
        with open(get_server_info_file(), "r", encoding="utf-8") as f:
            info = json.load(f)
            self.server_address = (info["addr"], info["port"])
        self.in_stream = in_stream
        self.out_stream = out_stream

    def ping(self) -> float:
        """
        Pings the server

        :return: The time it took to send PING and get OK back
        """
        t = time.time()
        sock = self._make_connection()
        sock.send(b"PING")
        sock.recv_expect(b"OK")
        return time.time() - t

    def list(self) -> List[str]:
        return list(filter(
            lambda p: (get_container_home() / p).is_dir(),
            listdir(get_container_home())
        ))

    def started(self, container_name: str) -> bool:
        sock = self._make_connection()
        sock.send(b"STARTED")
        sock.recv_expect(b"CONT")
        sock.send(bytes(container_name, "utf-8"))
        response = sock.recv_expect([b"YES", b"NO"])

        if response == b"YES":
            return True
        if response == b"NO":
            return False

    def view_files(self, container_name: str) -> None:
        filezilla(*self.ssh_address(container_name))


    def sftp(self, container_name: str) -> None:
        user, pswd, host, port = self.ssh_address(container_name)
        sftp(user, pswd, host, port, container_name)

    def ssh_address(self, container_name: str) -> Tuple[str, str, str, str]:
        """
        Return the address (user, passwd, host, port) needed to connect to a container's ssh

        :param container_name: The container whose shell is being used
        :return: The address
        """
        sock = self._make_connection()
        sock.send(b"SSH-ADDRESS")
        sock.recv_expect(b"CONT")
        sock.send(bytes(container_name, "utf-8"))
        user, passwd, host, port = sock.recv().decode("utf-8").split(":")
        sock.close()
        return (user, passwd, host, port)

    def update_hostkey(self, container_name: str) -> None:
        """
        Asks the server tp generate a new id_rsa and updates the container

        :param container_name: The container to generate the keys for
        """
        sock = self._make_connection()
        sock.send(b"UPDATE-HOSTKEY")
        sock.recv_expect(b"CONT")
        sock.send(bytes(container_name, "utf-8"))
        sock.recv_expect(b"OK")

    def start(self, container_name: str) -> None:
        """
        Starts a container

        :param container_name: The container being started
        """
        sock = self._make_connection()
        sock.send(b"START")
        sock.recv_expect(b"CONT")
        sock.send(bytes(container_name, "utf-8"))
        sock.recv_expect(b"OK")
        sock.close()

    def stop(self, container_name: str) -> None:
        """
        Stops a container

        :param container_name: The container being stopped
        """
        sock = self._make_connection()
        sock.send(b"STOP")
        sock.recv_expect(b"CONT")
        sock.send(bytes(container_name, "utf-8"))
        sock.recv_expect(b"OK")
        sock.close()

    def kill(self, container_name: str) -> None:
        """
        KIlls a container

        :param container_name: The container being stopped
        """
        sock = self._make_connection()
        sock.send(b"KILL")
        sock.recv_expect(b"CONT")
        sock.send(bytes(container_name, "utf-8"))
        sock.recv_expect(b"OK")
        sock.close()

    def run_shell(self, container_name: str) -> None:
        """
        Starts a shell on the container in question

        :param container_name: The container whose shell is being used
        """
        if not get_container_id_rsa(container_name).is_file():
            self.update_hostkey(container_name)

        user, _, host, port = self.ssh_address(container_name)
        subprocess.run(
            [
                "ssh" if sys.platform == "win32" else "/usr/bin/ssh",
                "-oNoHostAuthenticationForLocalhost=yes",
                "-oStrictHostKeyChecking=no",
                "-oLogLevel=ERROR",
                "-oPasswordAuthentication=no",
                f"-i{get_container_id_rsa(container_name)}",
                f"-p{port}",
                f"{user}@{host}",
            ]
        )

    def get_file(self, container_name: str, remote_file: str, local_file: Optional[str] = None) -> None:


        """
        Gets a file from a container

        :param container_name: The container where the file is obtained from
        :param remote_file: The file obtained from the container
        :param local_file: Where the file obtained from the container is placed
        """
        if local_file in (None, "."):
            local_file = joinpath(getcwd(), basename(remote_file))

        absolute_local_path = get_full_path(local_file)

        sock = self._make_connection()
        sock.send(b"GET-FILE")
        sock.recv_expect(b"CONT")
        sock.send(bytes(container_name, "utf-8"))
        sock.recv_expect(b"CONT")
        sock.send(bytes(remote_file, "utf-8"))
        sock.recv_expect(b"CONT")
        sock.send(bytes(absolute_local_path, "utf-8"))
        sock.recv_expect(b"OK")
        sock.close()

    def put_file(self, container_name: str, local_file: str, remote_file: Optional[str] = None) -> None:
        """
        Puts a file into a container

        :param container_name: The container where the file is placed
        :param local_file: The file being put into the container
        :param remote_file: Where the file will be placed in the container
        """
        absolute_local_path = get_full_path(local_file)

        if remote_file in (None, ".", "~"):
            remote_file = basename(absolute_local_path)

        sock = self._make_connection()
        sock.send(b"PUT-FILE")
        sock.recv_expect(b"CONT")
        sock.send(bytes(container_name, "utf-8"))
        sock.recv_expect(b"CONT")
        sock.send(bytes(absolute_local_path, "utf-8"))
        sock.recv_expect(b"CONT")
        sock.send(bytes(remote_file, "utf-8"))
        sock.recv_expect(b"OK")
        sock.close()

    def run_command(self, container_name: str, cli: List[str]) -> None:
        """
        Runs a command in a contianer

        :param container_name: The container with the command being run
        :param cmd: The command being run, as a list of arguments
        """
        sock = self._make_connection()
        sock.send(b"RUN-COMMAND")
        sock.recv_expect(b"CONT")
        sock.send(bytes(container_name, "utf-8"))
        sock.recv_expect(b"CONT")

        sock.send(bytes(str(len(cli)), "utf-8"))
        for arg in cli:
            sock.recv_expect(b"CONT")
            sock.send(bytes(arg, "utf-8"))

        sock.recv_expect(b"BEGIN")
        _RunCommandClient(sock, self.in_stream, self.out_stream)

    def install(self, archive_path_str: str, container_name: str) -> None:
        """
        Installs a new container from a given archive path

        :param archive_path_str: The path to the archive
        :param container_name: The name of the container
        """
        absolute_archive_path = get_full_path(archive_path_str)

        sock = self._make_connection()
        sock.send(b"INSTALL")
        sock.recv_expect(b"CONT")
        sock.send(bytes(absolute_archive_path, "utf-8"))
        sock.recv_expect(b"CONT")
        sock.send(bytes(container_name, "utf-8"))
        sock.recv_expect(b"OK")
        sock.close()

    def archive(self, container_name: str, path_to_destination: str) -> None:
        """
        Archives a container onto the disk

        :param container_name: The name of the container
        :param path_to_destination: Path where archive will be saved
        """
        absolute_path = get_full_path(path_to_destination)
        if isdir(absolute_path):
            absolute_path = joinpath(absolute_path, f"{container_name}.tar.gz")
        if isfile(absolute_path):
            raise FileExistsError(f"{absolute_path} already exists.")
        if not absolute_path.endswith(".tar.gz"):
            absolute_path += ".tar.gz"

        sock = self._make_connection()
        sock.send(b"ARCHIVE")
        sock.recv_expect(b"CONT")
        sock.send(bytes(container_name, 'utf-8'))
        sock.recv_expect(b"CONT")
        sock.send(bytes(absolute_path, 'utf-8'))
        sock.recv_expect(b"OK")
        sock.close()

    def delete(self, container_name: str) -> None:
        """
        Deletes a container from the file system

        :param container_name: The name of the container to delete
        """
        sock = self._make_connection()
        sock.send(b"DELETE")
        sock.recv_expect(b"CONT")
        sock.send(bytes(container_name, 'utf-8'))
        sock.recv_expect(b"OK")
        sock.close()

    def rename(self, old_name: str, new_name: str) -> None:
        """
        Renames a container on the file system

        :param old_name: The old name of the container
        :param new_name: The name that the container will be renamed to
        """
        sock = self._make_connection()
        sock.send(b"RENAME")
        sock.recv_expect(b"CONT")
        sock.send(bytes(old_name, 'utf-8'))
        sock.recv_expect(b"CONT")
        sock.send(bytes(new_name, 'utf-8'))
        sock.recv_expect(b"OK")
        sock.close()

    def server_halt(self) -> None:
        """
        Tells the server to halt
        """
        sock = self._make_connection()
        sock.send(b"HALT")
        sock.close()

    def server_panic(self) -> None:
        """
        Tells the server to PANIC!
        """
        sock = self._make_connection()
        sock.send(b"PANIC")
        sock.close()

    def _make_connection(self) -> ClientServerSocket:
        """
        Creates a connection to the server.

        :return: The socket connection to the server.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(self.server_address)
        my_sock = ClientServerSocket(sock)
        my_sock.recv_expect(b"READY")
        return my_sock


class _RunCommandClient:
    """
    Internal class used only for run_command. This class' __init__ is
    a blocking function.

    :param sock: The server socket object
    """

    sock: ClientServerSocket
    recv_closed: bool

    def __init__(self, sock: socket.socket, in_stream = sys.stdin, out_stream = sys.stdout):
        self.sock = sock
        self.recv_closed = False
        self.in_stream = in_stream
        self.out_stream = out_stream

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
            last_send = time.time()
            while not self.recv_closed:
                if select.select([self.in_stream], [], [], 0) == ([self.in_stream], [], []):
                    buffer = bytes(self.in_stream.readline(), "utf-8")
                    while buffer:
                        msg = buffer[:255]
                        self.sock.send(bytes([len(msg)]) + msg)
                        buffer = buffer[255:]
                    last_send = time.time()
                elif time.time() - last_send > 1:
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
            while msg := self.sock.recv():
                i = 0
                while i < len(msg):
                    stream = msg[i]
                    mybyte = msg[i + 1]
                    i += 2
                    if stream == 0:
                        pass
                    elif stream == 1:
                        self.out_stream.write(bytes((mybyte, )).decode('utf-8'))
                        self.out_stream.flush()
                    elif stream == 2:
                        self.out_stream.write(bytes((mybyte, )).decode('utf-8'))
                        self.out_stream.flush()
                    else:
                        raise RuntimeError("recv'd bad data")
        except (ConnectionError, OSError):
            pass
        finally:
            self.sock.close()
            self.recv_closed = True
