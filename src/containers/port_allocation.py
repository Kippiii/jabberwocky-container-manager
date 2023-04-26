"""
Used for allocating ports
"""
from os import popen
from sys import platform

import psutil

from src.containers.exceptions import PortAllocationError


def allocate_port(low: int = 12300, high: int = 65535) -> int:
    """
    Allocates a port in range [low, high]

    :low: Minimum port number permitted (low >= 1)
    :high: Highest port number permitted (high <= 65535)
    :return: The port allocated
    """

    if platform == "darwin":
        for port in range(low, high + 1):
            if not popen(f"lsof -i :{port}").read():
                return port
            port += 1

    else:
        occupied_ports = {conn.laddr.port for conn in psutil.net_connections()}

        for port in range(low, high + 1):
            if port not in occupied_ports:
                return port
            port += 1

    raise PortAllocationError(f"All ports in range [{low}, {high}] are unusable.")
