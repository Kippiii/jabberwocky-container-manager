import sys
from pathlib import Path
from subprocess import Popen, run, DETACHED_PROCESS
from src.system.syspath import get_container_id_rsa

def filezilla(user: str, pswd: str, host: str, port: str):
    if getattr(sys, 'frozen', False):
        base = Path(sys.executable).parent.parent / "contrib" / "filezilla"
    else:
        base = Path(__file__).parent.parent.parent / "contrib" / "filezilla"

    if sys.platform == "win32":
        Popen([base / "filezilla.exe", sftp], creationflags=DETACHED_PROCESS)
    elif sys.platform == "linux":
        Popen([base / "bin" / "filezilla", sftp])
    elif sys.platform == "darwin":
        Popen([
            Path("/usr/bin/open"),
            base / "FileZilla.app",
            "--args",
            sftp
        ])
    else:
        raise RuntimeError(f"Unknown Platform {sys.platform}")

def sftp(user: str, pswd: str, host: str, port: str, cname: str):
    args = [
        "C:\\Windows\\System32\\OpenSSH\\sftp.exe" if sys.platform == "win32" else "/usr/bin/sftp",
        "-oStrictHostKeyChecking=no",
        "-oLogLevel=ERROR",
        "-oPasswordAuthentication=no",
        "-i{}".format(get_container_id_rsa(cname)),
        "-P{}".format(port),
        "{}@{}".format(user, host)
    ]

    run(args, shell=True)
