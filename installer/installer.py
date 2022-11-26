import subprocess
import threading
import shutil
import os
import sys
from pathlib import Path
from sys import platform
from time import sleep
from urllib import request
from typing import Callable, Iterable, Dict
from getpass import getpass
from os import makedirs, chdir, environ


def abort() -> None:
    print()
    print("The installation has been aborted.")
    print("If this is an error, please report an issue at https://github.com/Kippiii/jabberwocky")
    getpass("Press Enter to exit. ")


def do_long_task(prompt: str, target: Callable[[], None], args: Iterable = ()) -> None:
    thread = threading.Thread(target=target, args=args)
    thread.start()

    spinner = ("|", "/", "-", "\\")
    idx = 0

    while thread.is_alive():
        print(f"\r{prompt}... {spinner[idx]}", end="\r")
        idx = (idx + 1) % len(spinner)
        sleep(0.1)

    print(f"\r{prompt}... Done!")

def install_qemu() -> None:
    # Check if QEMU is already installed.
    qemu_bin = {
        "win32": Path("C:\\Program Files\\qemu")
    }[platform]

    if (qemu_bin / "qemu-system-x86_64.exe").exists():
        return

    print(f"Could not find QEMU installed at {qemu_bin}.")
    inp = input(f"QEMU is required to continue, would you like to install it now? [y/N] ")
    if inp.lower() not in ("y", "yes"):
        abort()


    if platform == "win32":
        installer_url = "https://qemu.weilnetz.de/w64/2022/qemu-w64-setup-20221117.exe"
        checksum_url = "https://qemu.weilnetz.de/w64/2022/qemu-w64-setup-20221117.sha512"
        installer_file = ".\\qemu-setup.exe"

        do_long_task("Downloading QEMU installer", request.urlretrieve, (installer_url, installer_file))
        print("Please complete the QEMU installation.")
        subprocess.run([installer_file], shell=True, check=True)


def copy_files() -> Path:
    install_src = Path(os.path.dirname(sys.executable))
    install_dir = {
        "win32": Path.home() / "AppData\\Local\\Programs\\VDevBox"
    }[platform]

    inp = input(f"The software will be installed to {install_dir}. Is this OK? [y/N] ")
    if inp.lower() not in ("y", "yes"):
        abort()

    def do_copy():
        if not (Path.home() / ".containers").exists():
            makedirs(Path.home() / ".containers/")
        if install_dir.exists():
            shutil.rmtree(install_dir)

        makedirs(install_dir)
        shutil.copytree(install_src / "cman/",   install_dir / "cman/")
        shutil.copytree(install_src / "server/", install_dir / "server/")

    do_long_task("Copying files", do_copy)

    return install_dir


def update_PATH(install_dir: Path) -> None:
    path = environ["PATH"].split(";")
    bin = str(install_dir / "cman")

    if platform == "win32":
        if bin.upper() not in map(lambda s: s.upper(), path):
            path.append(bin)
            PATH = ";".join(path)
            subprocess.run(f"setx PATH \"{PATH}\" > NUL", shell=True, check=True)

    else:
        raise NotImplementedError(platform)


if __name__ == "__main__":
    if platform not in ("win32", ):
        print(f"{platform} not supported.")
        abort()

    project_root = Path(__file__).parent.parent
    chdir(project_root)

    install_qemu()
    install_dir = copy_files()
    update_PATH(install_dir)

    print("The installation completed successfully!")
    getpass("Press Enter to exit. ")