import sys
from pathlib import Path
import subprocess
from src.system.syspath import get_container_id_rsa

def filezilla(user: str, pswd: str, host: str, port: str):
    if sys.platform == "darwin":
        raise NotImplementedError("FileZilla")

    if getattr(sys, 'frozen', False):
        base = Path(sys.executable).parent.parent / "contrib" / "filezilla"
    else:
        base = Path(__file__).parent.parent.parent / "contrib" / "filezilla"

    if sys.platform == "win32":
        bin = base / "filezilla.exe"
    elif sys.platform == "linux":
        bin = base / "bin" / "filezilla"

    sftp = f"sftp://{user}:{pswd}@{host}:{port}"
    subprocess.Popen([bin, sftp], creationflags=subprocess.DETACHED_PROCESS)

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

    subprocess.run(args, shell=True)
