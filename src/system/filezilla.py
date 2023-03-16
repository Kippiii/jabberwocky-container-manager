import sys
import os
from pathlib import Path
import subprocess as sp
from src.system.syspath import get_container_id_rsa

def fzpath() -> Path | None:
    if getattr(sys, 'frozen', False):
        base = Path(sys.executable).parent.parent / "contrib" / "filezilla"
    else:
        base = Path(__file__).parent.parent.parent / "contrib" / "filezilla"

    if sys.platform == "win32":
        return base / "filezilla.exe"
    elif sys.platform == "linux":
        return base / "bin" / "filezilla"
    elif sys.platform == "darwin":
        return base / "FileZilla.app"
    else:
        raise None

def filezilla(user: str, pswd: str, host: str, port: str) -> None:
    if host == "localhost":
        host = "127.0.0.1" # FileZilla doesn't like 'localhost'

    args = f"sftp://{user}:{pswd}@{host}:{port}"

    if sys.platform == "win32":
        sp.Popen([fzpath(), args], creationflags=sp.DETACHED_PROCESS)
    elif sys.platform == "linux":
        sp.Popen([fzpath(), args], start_new_session=True, stdout=sp.PIPE, stderr=sp.PIPE)
    elif sys.platform == "darwin":
        sp.Popen([
            Path("/usr/bin/open"),
            fzpath(),
            "--args",
            args
        ], start_new_session=True, stdout=sp.PIPE, stderr=sp.PIPE)
    else:
        raise FileNotFoundError()

def sftp(user: str, pswd: str, host: str, port: str, cname: str):
    args = [
        "C:\\Windows\\System32\\OpenSSH\\sftp.exe" if sys.platform == "win32" else "/usr/bin/sftp",
        "-oNoHostAuthenticationForLocalhost=yes",
        "-oStrictHostKeyChecking=no",
        "-oLogLevel=ERROR",
        "-oPasswordAuthentication=no",
        "-i{}".format(get_container_id_rsa(cname)),
        "-P{}".format(port),
        "{}@{}".format(user, host)
    ]

    os.system(" ".join(args)) # sp.run is buggy on macOS

