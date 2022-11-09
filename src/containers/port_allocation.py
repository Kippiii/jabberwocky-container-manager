"""
Manages allocating ports for connecting the containers
"""

from typing import Optional


class PortAllocator:
    """
    Class for dealing with the allocation of ports

    :param cur_port: The next port to be allocated
    """

    cur_port: int = 12300

    def __init__(self) -> None:
        pass

    def allocate(self) -> int:
        """
        Returns a port to allocate

        :return: The port allocated
        """
        self.cur_port += 1
        return self.cur_port - 1


PORT_ALLOCATOR: Optional[PortAllocator] = None


def allocate_port() -> int:
    """
    Allocates a port

    :return: The port allocated
    """
    global PORT_ALLOCATOR  # pylint: disable=global-statement
    if PORT_ALLOCATOR is None:
        PORT_ALLOCATOR = PortAllocator()
    return PORT_ALLOCATOR.allocate()
