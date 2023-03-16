"""
Manages the file system used by the container manager
"""

import os
import sys
from pathlib import Path
from shutil import which
from os.path import abspath, expanduser
from src.system.state import frozen


def get_full_path(path: str):
    return abspath(expanduser(path))


def get_scripts_path() -> Path:
    if frozen():
        return Path(sys.executable).parent.parent / "scripts"
    else:
        return Path(__file__).parent.parent.parent / "scripts"


def get_qemu_bin() -> Path:
    """
    Returns the path to qemu

    :return: The path to qemu
    """
    if os.name == "nt":
        return Path("C:\\Program Files\\qemu")
    if os.name == "posix":
        return Path(which("qemu-system-x86_64")).absolute().parent
    raise OSError(f'Unsupported platform "{os.name}"')


def get_dev_null() -> Path:
    """
    Returns the path to the null directory

    :return: The path to null
    """
    if os.name == "nt":
        return Path("NUL")
    if os.name == "posix":
        return Path("/dev/null")
    raise OSError(f'Unsupported platform "{os.name}"')


def get_container_home() -> Path:
    """
    Returns the path to the containers folder

    :return: The path to the containers folder
    """
    return Path.home() / ".containers"


def get_server_info_file() -> Path:
    """
    Returns the path to the server address file

    :return: The path to the server address file
    """
    return get_container_home() / "server_info.json"

def get_server_log_file() -> Path:
    """
    Returns the path to the server log file

    :return: The path to the server log file
    """
    return get_container_home() / "server.log"

def get_repo_file() -> Path:
    """
    Returns the path to the repo json file

    :return: The path to the repo json file
    """
    return get_container_home() / "repo.json"

def get_container_dir(container_name: str) -> Path:
    """
    Returns the path to the folder of a current container

    :param container_name: The name of the container
    :return: The folder of that container
    """
    return get_container_home() / container_name


def get_container_config(container_name: str) -> Path:
    """
    Returns the path to the container configuration

    :param container_name: The name of the container
    :return: The path to the json for the container
    """
    return get_container_dir(container_name) / "config.json"


def get_get_container_id_rsa_pub(container_name: str) -> Path:
    """
    Returns the public key of a container

    :param container_name: The name of the container
    :return: The path to the container's public key
    """
    return get_container_dir(container_name) / "id_rsa.pub"


def get_container_id_rsa(container_name: str) -> Path:
    """
    Returns the private key of a container

    :param container_name: The name of the container
    :return: The path to the container's private key
    """
    return get_container_dir(container_name) / "id_rsa"
