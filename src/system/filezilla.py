import sys
from pathlib import Path
from subprocess import Popen, DETACHED_PROCESS

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
    Popen([bin, sftp], creationflags=DETACHED_PROCESS)
