"""
Manages the Filezilla client
"""
import os
import subprocess as sp
import sys
from pathlib import Path

from src.system.syspath import get_container_id_rsa


def fzpath() -> Path | None:
    """
    Gets the path to Filezilla executable
    """
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent.parent / "contrib" / "filezilla"
    else:
        base = Path(__file__).parent.parent.parent / "contrib" / "filezilla"

    if sys.platform == "win32":
        return base / "filezilla.exe"
    if sys.platform == "linux":
        return base / "bin" / "filezilla"
    if sys.platform == "darwin":
        return base / "FileZilla.app"
    return None


def filezilla(user: str, pswd: str, host: str, port: str) -> None:
    """
    Opens a light-weight Filezilla client

    :param user: The username for SSH
    :param pswd: The password for SSH
    :param host: The host name being SSHed into
    :param port: The port being SSHed into
    """
    if host == "localhost":
        host = "127.0.0.1"  # FileZilla doesn't like 'localhost'

    args = f"sftp://{user}:{pswd}@{host}:{port}"

    if sys.platform == "win32":
        sp.Popen(  # pylint: disable=consider-using-with
            [fzpath(), args], creationflags=sp.DETACHED_PROCESS
        )
    elif sys.platform == "linux":
        sp.Popen(  # pylint: disable=consider-using-with
            [fzpath(), args], start_new_session=True, stdout=sp.PIPE, stderr=sp.PIPE
        )
    elif sys.platform == "darwin":
        sp.Popen(  # pylint: disable=consider-using-with
            [Path("/usr/bin/open"), fzpath(), "--args", args],
            start_new_session=True,
            stdout=sp.PIPE,
            stderr=sp.PIPE,
        )
    else:
        raise FileNotFoundError()


def sftp(user: str, _pswd: str, host: str, port: str, cname: str):
    """
    Opens an SFTP session

    :param user: The username
    :param pswd: The password
    :param host: The host being connected to
    :param port: The port of the host being connected to
    :param cname: The name of the container
    """
    args = [
        "C:\\Windows\\System32\\OpenSSH\\sftp.exe"
        if sys.platform == "win32"
        else "/usr/bin/sftp",
        "-oNoHostAuthenticationForLocalhost=yes",
        "-oStrictHostKeyChecking=no",
        "-oLogLevel=ERROR",
        "-oPasswordAuthentication=no",
        f"-i{get_container_id_rsa(cname)}",
        f"-P{port}",
        f"{user}@{host}",
    ]

    os.system(" ".join(args))  # sp.run is buggy on macOS
