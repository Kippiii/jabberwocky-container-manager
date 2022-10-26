from pathlib import Path
import os


def qemu_bin() -> Path:
    if os.name == 'nt':
        return Path('C:\\Program Files\\qemu')
    elif os.name == 'posix':
        return Path('/usr/bin')
    else:
        raise OSError(f'Unsupported platform "{os.name}"')


def dev_null() -> Path:
    if os.name == 'nt':
        return Path('NUL')
    elif os.name == 'posix':
        return Path('/dev/null')
    else:
        raise OSError(f'Unsupported platform "{os.name}"')


def dot_containers() -> Path:
    return Path.joinpath(Path.home(), '.containers')


def container_root(container_name: str) -> Path:
    return Path.joinpath(dot_containers(), container_name)


def container_config(container_name: str) -> Path:
    return Path.joinpath(container_root(container_name), 'config.json')
