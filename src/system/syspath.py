import os
from pathlib import Path


def get_qemu_bin() -> Path:
    """
    Returns the path to qemu

    :return: The path to qemu
    """
    if os.name == "nt":
        return Path("C:\\Program Files\\qemu")
    elif os.name == "posix":
        return Path("/usr/bin")
    else:
        raise OSError(f'Unsupported platform "{os.name}"')


def get_dev_null() -> Path:
    """
    Returns the path to the null directory

    :return: The path to null
    """
    if os.name == "nt":
        return Path("NUL")
    elif os.name == "posix":
        return Path("/dev/null")
    else:
        raise OSError(f'Unsupported platform "{os.name}"')


def get_container_home() -> Path:
    """
    Returns the path to the containers folder

    :return: The path to the containers folder
    """
    return Path.home() / ".containers"


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
