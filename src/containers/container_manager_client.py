import socket
import threading
from typing import Tuple, List, Optional
from os.path import abspath
import msvcrt
import sys
import time


class ContainerManagerClient:
    server_address: Tuple[str, int] = (socket.gethostname(), 35053)

    def __init__(self):
        pass

    def start(self, container_name: str) -> None:
        sock = self._make_connection()
        sock.send(b'START')
        self._recv_expect(sock, 1024, b'CONT')
        sock.send(bytes(container_name, 'utf-8'))
        self._recv_expect(sock, 1024, b'OK')
        sock.close()

    def stop(self, container_name: str) -> None:
        sock = self._make_connection()
        sock.send(b'STOP')
        self._recv_expect(sock, 1024, b'CONT')
        sock.send(bytes(container_name, 'utf-8'))
        self._recv_expect(sock, 1024, b'OK')
        sock.close()

    def run_shell(self, cli: List[str]) -> None:
        raise NotImplementedError()

    def run_command(self, cli: List[str]) -> None:
        raise NotImplementedError()

    def get_file(self, container_name: str, remote_file: str, local_file: str) -> None:
        absolute_local_path = abspath(local_file)

        sock = self._make_connection()
        sock.send(b'GET-FILE')
        self._recv_expect(sock, 1024, b'CONT')
        sock.send(bytes(container_name, 'utf-8'))
        self._recv_expect(sock, 1024, b'CONT')
        sock.send(bytes(remote_file, 'utf-8'))
        self._recv_expect(sock, 1024, b'CONT')
        sock.send(bytes(absolute_local_path, 'utf-8'))
        self._recv_expect(sock, 1024, b'OK')
        sock.close()

    def put_file(self, container_name: str, local_file: str, remote_file: str) -> None:
        absolute_local_path = abspath(local_file)

        sock = self._make_connection()
        sock.send(b'PUT-FILE')
        self._recv_expect(sock, 1024, b'CONT')
        sock.send(bytes(container_name, 'utf-8'))
        self._recv_expect(sock, 1024, b'CONT')
        sock.send(bytes(absolute_local_path, 'utf-8'))
        self._recv_expect(sock, 1024, b'CONT')
        sock.send(bytes(remote_file, 'utf-8'))
        self._recv_expect(sock, 1024, b'OK')
        sock.close()

    def run_command(self, container_name: str, cli: List[str]) -> None:
        sock = self._make_connection()
        sock.send(b'RUN-COMMAND')
        self._recv_expect(sock, 1024, b'CONT')
        sock.send(bytes(container_name, 'utf-8'))
        self._recv_expect(sock, 1024, b'CONT')

        sock.send(bytes(str(len(cli)), 'utf-8'))
        for arg in cli:
            self._recv_expect(sock, 1024, b'CONT')
            sock.send(bytes(arg, 'utf-8'))
        
        self._recv_expect(sock, 1024, b'BEGIN')
        _RunCommandClient(sock)

    def server_halt(self) -> None:
        sock = self._make_connection()
        sock.send(b'HALT')
        sock.close()

    def _make_connection(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(self.server_address)
        self._recv_expect(sock, 1024, b'READY')
        return sock

    def _recv_expect(self, sock: socket.socket, bufsize: int, expected: bytes) -> bytes:
        if (msg := sock.recv(bufsize)) != expected:
            sock.close()
            raise RuntimeError(f'Got Unexpected Response "{msg}" from {self.server_address}')
        else:
            return msg


class _RunCommandClient:
    sock: socket.socket
    recv_closed: bool

    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.recv_closed = False

        t_recv = threading.Thread(target=self._recv)
        t_send = threading.Thread(target=self._send_msvcrt)
        t_recv.start()
        t_send.start()
        t_recv.join()
        t_send.join()

    def _send_msvcrt(self):
        try:
            msg = ''
            while not self.recv_closed:
                while msvcrt.kbhit():
                    char = msvcrt.getwche()

                    if char == '\r':
                        print(end='\n')
                        self.sock.send(bytes(msg + '\n', 'utf-8'))
                        msg = ''

                    elif char == '\b':
                        print(' ', end='\b', flush=True)
                        msg = msg[:-1]

                    else:
                        msg += char
                
                time.sleep(0.1)
        except ConnectionError:
            pass
        finally:
            self.sock.close()

    def _recv(self):
        try:
            while msg := self.sock.recv(1024):
                sys.stdout.buffer.write(msg)
                sys.stdout.flush()
        except ConnectionError:
            pass
        finally:
            self.sock.close()
            self.recv_closed = True
