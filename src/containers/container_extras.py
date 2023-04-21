"""
Various extra tools used by containers
"""

import tarfile
from os.path import isdir, isfile
from pathlib import Path
from shutil import rmtree
from typing import Union

from src.system.syspath import get_container_config, get_container_dir


def install_container(archive_path: Path, container_name: str) -> None:
    """
    Installs a container from an archive

    :param archive_path: The path to the archive
    """
    if not tarfile.is_tarfile(archive_path):
        raise TypeError(f"'{archive_path}' is not a tar archive")
    with tarfile.open(archive_path) as tar:
        tar.extractall(path=get_container_dir(container_name))
        # TODO Sanity check this extraction


def delete_container(container_name: Path) -> None:
    """
    Deletes a currently installed container

    :param container_name: The container being deleted
    """
    container_path = Path(get_container_dir(container_name))
    if not container_path.is_dir():
        raise FileNotFoundError(str(container_path))

    rmtree(str(container_path))


def archive_container(
    container_name: str, path_to_destination: Union[str, Path]
) -> None:
    """
    Saves a container as an archive

    :param container_name: The name of the container being archived
    :param path_to_destination: The path where the archive will be saved
    """
    if isinstance(path_to_destination, Path):
        path_to_destination = str(path_to_destination)

    if isdir(path_to_destination):
        raise IsADirectoryError(str(path_to_destination))
    if isfile(path_to_destination):
        raise FileExistsError(str(path_to_destination))

    with tarfile.open(path_to_destination, "w:gz") as tar:
        tar.add(get_container_config(container_name), arcname="config.json")
        tar.add(get_container_dir(container_name) / "hdd.qcow2", arcname="hdd.qcow2")
