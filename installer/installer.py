import subprocess
import threading
import shutil
import os
import sys
from pathlib import Path
from sys import platform, exit
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
    exit(1)


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
    if platform == "win32":
        qemu_system_x86_64 = Path("C:\\Program Files\\qemu\\qemu-system-x86_64.exe")
        if not qemu_system_x86_64.exists():
            print(f"Could not find QEMU installed at {qemu_system_x86_64.parent}.")
            inp = input(f"QEMU is required to continue, would you like to install it now? [y/N] ")
            if inp.lower() not in ("y", "yes"):
                abort()

            installer_url = "https://qemu.weilnetz.de/w64/2022/qemu-w64-setup-20221117.exe"
            checksum_url = "https://qemu.weilnetz.de/w64/2022/qemu-w64-setup-20221117.sha512"
            installer_file = ".\\qemu-setup.exe"

            do_long_task("Downloading QEMU installer", request.urlretrieve, (installer_url, installer_file))
            print("Please complete the QEMU installation.")
            subprocess.run([installer_file], shell=True, check=True)

    elif platform == "darwin":
        if not shutil.which("qemu-system-x86_64"):
            print("QEMU is not installed. The installation cannot continue.")
            print("For information on how to install QEMU on macOS, see https://www.qemu.org/download/#macos")
            abort()


    elif shutil.which("apt-get"):
        if not shutil.which("qemu-system-x86_64"):
            inp = input("qemu-system is required to continue, would you like to install it now? [y/N] ")
            if inp.lower() not in ("y", "yes"):
                abort()

            subprocess.run(["sudo", "apt-get", "update"], check=True)
            subprocess.run(["sudo", "apt-get", "install", "qemu-system" ,"-y"], check=True)

    else:
        if not shutil.which("qemu-system-x86_64"):
            print("QEMU is not installed. The installation cannot continue.")
            print("For information on how to install QEMU on Linux, see https://www.qemu.org/download/#linux")
            abort()


def copy_files() -> Path:
    install_src = Path(os.path.dirname(sys.executable))
    install_dir = {
        "win32": Path.home() / "AppData\\Local\\Programs\\VDevBox",
        "linux": Path.home() / ".local/share/VDevBox",
        "darwin": Path.home() / ".local/share/VDevBox",
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
    bin = str(install_dir / "cman")

    if platform == "win32":
        path = environ["PATH"].split(";")
        if bin.upper() not in map(lambda s: s.upper(), path):
            path.append(bin)
            PATH = ";".join(path)
            subprocess.run(f"setx PATH \"{PATH}\" > NUL", shell=True, check=True)

    else:
        path = environ["PATH"].split(":")
        if bin not in path:
            with open(Path.home() / ".bashrc", "a") as bashrc:
                bashrc.write(f"\n")
                bashrc.write(f"# Added by VDevBoxInstaller\n")
                bashrc.write(f"PATH=\"$PATH:{bin}\"")


if __name__ == "__main__":
    if platform not in ("win32", "linux", "darwin"):
        print(f"{platform} not supported.")
        abort()

    project_root = Path(__file__).parent.parent
    chdir(project_root)

    install_qemu()
    install_dir = copy_files()
    update_PATH(install_dir)

    print("The installation completed successfully!")
    getpass("Press Enter to exit. ")