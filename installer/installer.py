import subprocess
import threading
import shutil
import base64
import os
import hashlib
import tempfile
from pathlib import Path
from sys import platform, exit
from time import sleep
from urllib import request
from typing import Callable, Iterable, Optional, List
from getpass import getpass
from os import makedirs, chdir, environ
if platform == "win32":
    import winreg

BUILD_BASE64 = ""   # Base64 encoded tar file containing the program's files
BUILD_LICENSE = ""  # License agreement


def abort() -> None:
    """
    Aborts the installation
    """
    print()
    print("The installation has been aborted.")
    print("If this is an error, please report an issue at https://github.com/Kippiii/jabberwocky")
    getpass("Press Enter to exit. ")
    exit(1)


class LongTask:
    """
    Perform a task that takes a long time. Provides a progress spinner.

    :param exception: Exception raised by thread, if any.
    :param prompt: The prompt showed to the user while the task is being performed.
    :param target: The function to be executed.
    :param args: Arguments to the function.
    """
    exception: Optional[Exception] = None
    prompt : str
    target: Callable[[], None]
    args: Iterable

    def __init__(self, prompt: str, target: Callable[[], None], args: Iterable = ()) -> None:
        self.prompt = prompt
        self.target = target
        self.args = args

    def exec(self):
        """
        Execute the target task.
        """
        thread = threading.Thread(target=self._task)
        thread.start()

        spinner = ("|", "/", "-", "\\")
        idx = 0

        while thread.is_alive():
            print(f"\r{self.prompt}... {spinner[idx]}", end="\r")
            idx = (idx + 1) % len(spinner)
            sleep(0.1)

        thread.join()

        if self.exception is not None:
            print()
            raise self.exception
        else:
            print(f"\r{self.prompt}... Done!")

    def _task(self):
        """
        Executes the target. Catches any exceptions to be raised by main thread.
        """
        try:
            self.target(*self.args)
        except Exception as ex:  # pylint: disable=broad-except
            self.exception = ex


def install_qemu() -> None:
    """
    Checks is QEMU is already installed. If it isn't, install it.
    If the user refuses the install, abort the installation.
    """
    if platform == "win32":
        qemu_system_x86_64 = Path("C:\\Program Files\\qemu\\qemu-system-x86_64.exe")
        if not qemu_system_x86_64.exists():
            print(f"Could not find QEMU installed at {qemu_system_x86_64.parent}.")
            inp = input(f"QEMU is required to continue, would you like to install it now? [y/N] ")
            if inp.lower() not in ("y", "yes"):
                abort()

            installer_url = "https://qemu.weilnetz.de/w64/2022/qemu-w64-setup-20221117.exe"
            checksum_url = "https://qemu.weilnetz.de/w64/2022/qemu-w64-setup-20221117.sha512"
            installer_file = Path(tempfile.gettempdir()) / "qemu-setup.exe"
            checksum_file = Path(tempfile.gettempdir()) / "qemu-setup.sha512"

            t = LongTask("Downloading QEMU installer", request.urlretrieve, (installer_url, installer_file))
            t.exec()

            def verify():
                request.urlretrieve(checksum_url, checksum_file)
                with open(installer_file, "rb") as inst, open(checksum_file, "r") as chksm:
                    bytes = inst.read()
                    hash = hashlib.sha512(bytes).hexdigest()
                    assert hash.upper() == chksm.read().split()[0].upper()

            t = LongTask("Verifying QEMU installer", verify)
            t.exec()

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


def license_agreement() -> None:
    """
    Prompt the user to accept the license agreement.
    """
    print("Please review the following license agreement carefully.")
    print("========================================================")
    print(BUILD_LICENSE)
    print()
    inp = input("Do you accept these terms? [y/N] ")
    if inp.lower() not in ("y", "yes"):
        abort()


def copy_files() -> Path:
    """
    Write the program files in the install directory.
    """

    # Get the installation directory
    install_dir = {
        "win32": Path.home() / "AppData\\Local\\Programs\\VDevBox",
        "linux": Path.home() / ".local/share/VDevBox",
        "darwin": Path.home() / ".local/share/VDevBox",
    }[platform]

    inp = input(f"The software will be installed to {install_dir}. Is this OK? [y/N] ")
    if inp.lower() not in ("y", "yes"):
        abort()

    def do_copy():
        # Create .containers if not exists
        if not (Path.home() / ".containers").exists():
            makedirs(Path.home() / ".containers/")

        # Prepare install directory
        if install_dir.exists():
            shutil.rmtree(install_dir)
        makedirs(install_dir)

        # Decode and extract program contents stored in BUILD_BASE64
        with open(install_dir / "contents.tar", "wb") as f:
            f.write(base64.b64decode(BUILD_BASE64))
        shutil.unpack_archive(install_dir / "contents.tar", install_dir, "tar")
        os.remove(install_dir / "contents.tar")

    t = LongTask("Copying files", do_copy)
    t.exec()

    return install_dir


def update_PATH(install_dir: Path) -> None:
    """
    Update the user's PATH variable
    """
    bin = str(install_dir / "cman")

    if platform == "win32":
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", access=winreg.KEY_ALL_ACCESS)
        path: List[str] = winreg.QueryValueEx(key, "Path")[0].split(";")

        if bin.upper() not in map(lambda s: s.upper(), path):
            path.append(bin)
            PATH = ";".join(path) + ";"
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, PATH)

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
    license_agreement()
    install_dir = copy_files()
    update_PATH(install_dir)

    print("The installation completed successfully!")
    getpass("Press Enter to exit. ")
