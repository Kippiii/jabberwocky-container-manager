import hashlib
import shutil
import subprocess
import sys
import tempfile
import threading
import traceback
from getpass import getpass
from os import chdir, environ, makedirs, pathsep
from pathlib import Path
from sys import exit, platform
from time import sleep
from typing import Callable, Iterable, List, Optional
from urllib import request
from typing import Callable, Iterable, Optional, List
from getpass import getpass
from os import makedirs, listdir, remove, rmdir, environ, pathsep
from server import server_is_running

if platform == "win32":
    import winreg

from src.system.multithreading import SpinningTask
from src.system.state import frozen

PYINSTALLER_DATA_PATH = Path(__file__).absolute().parent


def abort() -> None:
    """
    Aborts the installation
    """
    print()
    print("The installation has been aborted.")
    print(
        "If this is an error, please report an issue at https://github.com/Kippiii/jabberwocky"
    )
    getpass("Press Enter to exit. ")
    exit(1)


def ask_permission(msg: str) -> None:
    inp = input(f"{msg} [y/N] ")
    if inp.lower() not in ("y", "yes"):
        abort()


def install_qemu() -> None:
    """
    Checks is QEMU is already installed. If it isn't, install it.
    If the user refuses the install, abort the installation.
    """
    if platform == "win32":
        qemu_system_x86_64 = Path("C:\\Program Files\\qemu\\qemu-system-x86_64.exe")
        if not qemu_system_x86_64.exists():
            print(f"Could not find QEMU installed at {qemu_system_x86_64.parent}.")
            ask_permission(f"QEMU is required to continue, would you like to install it now?")

            installer_url = (
                "https://qemu.weilnetz.de/w64/2022/qemu-w64-setup-20221117.exe"
            )
            checksum_url = (
                "https://qemu.weilnetz.de/w64/2022/qemu-w64-setup-20221117.sha512"
            )
            installer_file = Path(tempfile.gettempdir()) / "qemu-setup.exe"
            checksum_file = Path(tempfile.gettempdir()) / "qemu-setup.sha512"

            t = SpinningTask(
                "Downloading QEMU installer",
                request.urlretrieve,
                (installer_url, installer_file),
            )
            t.exec()

            def verify():
                request.urlretrieve(checksum_url, checksum_file)
                with open(installer_file, "rb") as inst, open(
                    checksum_file, "r"
                ) as chksm:
                    bytes = inst.read()
                    hash = hashlib.sha512(bytes).hexdigest()
                    assert hash.upper() == chksm.read().split()[0].upper()

            t = SpinningTask("Verifying QEMU installer", verify)
            t.exec()

            print("Please complete the QEMU installation.")
            subprocess.run([installer_file], shell=True, check=True)

    elif platform == "darwin":
        if not shutil.which("qemu-system-x86_64"):
            print("QEMU is not installed. The installation cannot continue.")
            print(
                "For information on how to install QEMU on macOS, see https://www.qemu.org/download/#macos"
            )
            abort()

    elif shutil.which("apt-get"):
        if not shutil.which("qemu-system-x86_64"):
            ask_permission("qemu-system is required to continue, would you like to install it now?")
            subprocess.run(["sudo", "apt-get", "update"], check=True)
            subprocess.run(
                ["sudo", "apt-get", "install", "qemu-system", "-y"], check=True
            )

    else:
        if not shutil.which("qemu-system-x86_64"):
            print("QEMU is not installed. The installation cannot continue.")
            print(
                "For information on how to install QEMU on Linux, see https://www.qemu.org/download/#linux"
            )
            abort()


def license_agreement() -> None:
    """
    Prompt the user to accept the license agreement.
    """
    with open(PYINSTALLER_DATA_PATH / "LICENSE", "r") as f:
        print("Please review the following license agreement carefully.")
        print("========================================================")
        print(f.read())
        ask_permission("Do you accept these terms?")


def get_install_dir() -> Path:
    return {
        "win32": Path.home() / "AppData\\Local\\Programs\\Jabberwocky",
        "linux": Path.home() / ".local/share/Jabberwocky",
        "darwin": Path.home() / ".local/share/Jabberwocky",
    }[platform]


def delete_previous_installation(install_dir: Path) -> None:
    if not install_dir.exists():
        return

    def do_delete_previous_installation():
        # Delete previous installation, keep track of deleted files.
        files_deleted: List[Path] = []
        def do_delete(cur: Path = Path()) -> None:
            if (install_dir / cur).is_file():
                remove(install_dir / cur)
                files_deleted.append(cur)
            elif (install_dir / cur).is_dir():
                for child in listdir(install_dir / cur):
                    do_delete(cur / child)
                rmdir(install_dir / cur)

        # Back up previous installation
        prev_install_backup = Path(tempfile.mkdtemp()) / "Jabberwocky"
        shutil.copytree(install_dir, prev_install_backup)

        try:
            do_delete()
        except (OSError, PermissionError):
            # Deletion failed, restore previous installation.
            for file in files_deleted:
                makedirs(install_dir / file.parent, exist_ok=True)
                shutil.copy(prev_install_backup / file, install_dir / file)
            raise PermissionError("Could not remove previous installation")
        else:
            shutil.rmtree(prev_install_backup)

    t = SpinningTask("Deleting previous installation", do_delete_previous_installation)
    t.exec()


def copy_files(install_dir: Path) -> Path:
    """
    Write the program files in the install directory.
    """
    def do_copy():
        # Create .containers if not exists
        if not (Path.home() / ".containers").exists():
            makedirs(Path.home() / ".containers/")

        # Prepare install directory
        makedirs(install_dir)
        makedirs(install_dir / "contrib")
        makedirs(install_dir / "scripts")

        # Copy files
        shutil.unpack_archive(PYINSTALLER_DATA_PATH / "dist.tar", install_dir)
        shutil.unpack_archive(
            PYINSTALLER_DATA_PATH / "contrib.tar", install_dir / "contrib"
        )
        shutil.unpack_archive(
            PYINSTALLER_DATA_PATH / "scripts.tar", install_dir / "scripts"
        )

    t = SpinningTask("Copying files", do_copy)
    t.exec()


def update_PATH(install_dir: Path) -> None:
    """
    Update the user's PATH variable
    """
    bin = str(install_dir / "jab")

    if platform == "win32":
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, "Environment", access=winreg.KEY_ALL_ACCESS
        )
        path: List[str] = winreg.QueryValueEx(key, "Path")[0].split(pathsep)

        if bin.upper() not in map(lambda s: s.upper(), path):
            path.append(bin)
            PATH = pathsep.join(path) + pathsep
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, PATH)

    elif platform == "darwin":
        path = environ["PATH"].split(pathsep)
        if bin not in path:
            with open(Path.home() / ".bash_profile", "a") as bashrc:
                bashrc.write(f"\n")
                bashrc.write(f"# Added by Jabberwocky Installer\n")
                bashrc.write(f'export PATH="$PATH{pathsep}{bin}"')

    else:
        path = environ["PATH"].split(pathsep)
        if bin not in path:
            with open(Path.home() / ".bashrc", "a") as bashrc:
                bashrc.write(f"\n")
                bashrc.write(f"# Added by Jabberwocky Installer\n")
                bashrc.write(f'PATH="$PATH{pathsep}{bin}"')


if __name__ == "__main__":
    if not frozen():
        print("The installer cannot be run unless it is built with PyInstaller.")
        print("See the README for building instructions.")
        abort()

    if platform not in ("win32", "linux", "darwin"):
        print(f"{platform} not supported.")
        abort()

    if server_is_running():
        print("Install cannot continue while the Jabberwocky server is running.")
        print("Please run `jab server-halt` and then run this installer again.")
        abort()

    try:
        install_qemu()
        license_agreement()

        install_dir = get_install_dir()
        ask_permission(f"The software will be installed to \"{install_dir}\". Is this OK?")

        delete_previous_installation(install_dir)
        copy_files(install_dir)
        update_PATH(install_dir)
    except Exception:
        traceback.print_exc(limit=0)
        abort()
    else:
        print("The installation completed successfully!")
        print(
            "You may need to restart your computer for the changes to take full effect."
        )
        getpass("Press Enter to exit. ")
