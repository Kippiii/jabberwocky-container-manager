import socket
from typing import Union, List

from src.containers.exceptions import get_server_error

class ClientServerSocket:
    """
    """
    def __init__(self, sock: socket.socket) -> None:
        self._sock = sock

    def send(self, data: Union[bytes, str]) -> None:
        if isinstance(data, str):
            data = data.encode()
        self._sock.send(data)

    def recv(self, bufsize=1024) -> bytes:
        return self._sock.recv(bufsize)

    def recv_expect(self, expected: Union[bytes, List[bytes]], bufsize: int = 1024) -> None:
        msg = self.recv(bufsize)

        if type(expected) is bytes:
            match = msg == expected
        else:
            match = msg in expected

        if not match:
            msg = msg.decode()
            get_server_error(msg, self)

        return msg

    def close(self) -> None:
        self._sock.close()

    def cont(self) -> None:
        self.send(b"CONT")

    def yes(self) -> None:
        self.send(b"YES")

    def no(self) -> None:
        self.send(b"NO")

    def begin(self) -> None:
        self.send(b"BEGIN")

    def ok(self) -> None:
        self.send(b"OK")

    def raise_exception(self) -> None:
        self.send(b"EXCEPTION_OCCURED")

    def raise_unknown_request(self, request: str) -> None:
        self.send(b"UNKNOWN_REQUEST")
        self.recv()
        self.send(request)

    def raise_container_not_started(self, container_name: str) -> None:
        self.send(b"CONTAINER_NOT_STARTED")
        self.recv()
        self.send(container_name)

    def raise_no_such_container(self, container_name: str) -> None:
        self.send(b"NO_SUCH_CONTAINER")
        self.recv()
        self.send(container_name)

    def raise_boot_error(self) -> None:
        self.send(b"BOOT_FAILURE")

    def raise_invalid_path(self, path: str) -> None:
        self.send(b"INVALID_PATH")
        self.recv()
        self.send(path)
