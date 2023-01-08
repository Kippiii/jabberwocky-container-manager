from pathlib import Path
from os import makedirs
from shutil import unpack_archive, rmtree

from src.system.syspath import *
from src.containers.exceptions import ContainerAlreadyExistsError

def install_container(archive: Path, name: str = ""):
    """
    CoInstalls a container from a tar archive

    :param archive: Path (relative or absolute) to the archive
    :param name: The new name of the container. Takes the name of the archive is none is provided.
    """

    if not name:
        name = archive.stem

    # Some basic guard clauses
    if not archive.exists():
        raise FileNotFoundError(archive.absolute())
    if not archive.is_file():
        raise IsADirectoryError(archive.absolute())
    if get_container_dir(name).exists():
        raise ContainerAlreadyExistsError(name)

    try:
        makedirs(get_container_dir(name))
        unpack_archive(archive, get_container_dir(name), "tar")
    except Exception as ex:
        rmtree(get_container_dir(name))
        raise ex
