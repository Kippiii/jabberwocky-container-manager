from enum import Enum
from sys import platform


class OS(Enum):
    """
    The type of operating system
    """

    WINDOWS = 1
    MACOS = 2
    LINUX = 3


def get_os() -> OS:
    if platform in ["linux", "linux2"]:
        return OS.LINUX
    if platform == "darwin":
        return OS.MACOS
    if platform == "win32":
        return OS.WINDOWS
    raise ValueError(f"Unknown platform: {platform}")
