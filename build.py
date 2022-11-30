import subprocess
import shutil
import hashlib
from pathlib import Path
from os import makedirs, chdir, pathsep
from os.path import basename
from sys import executable, platform
from platform import machine

EXE_FILE_EXTEN = ".exe" if platform == "win32" else ""

root           = Path(__file__).parent.absolute()
build          = root / "build/"
target_run     = root / "run.py"
target_server  = root / "server.py"
target_install = root / "installer.py"

installer_name = f"installer-{platform}-{machine()}"
installer_file = build / "dist" / (installer_name + EXE_FILE_EXTEN)


# Clean previous build
if build.is_dir():
    shutil.rmtree(build)
makedirs(build)
chdir(build)


# Build
pyinstaller = [
    executable,
    "-m",
    "PyInstaller"
]
build_options = [
    "--workpath", "work",
    "--specpath", "spec",
    "--distpath", "dist"
]

subprocess.run([
    *pyinstaller,
    "--name",
    "jab",
    *build_options,
    target_run,
], check=True)

subprocess.run([
    *pyinstaller,
    "--noconsole",
    *build_options,
    target_server,
], check=True)

shutil.make_archive(build / "dist", "tar", build / "dist")

subprocess.run([
    *pyinstaller,
    f"--console",
    f"--onefile",
    f"--name",
    installer_name,
    f"--add-data",
    f"{build / 'dist.tar'}{pathsep}.",
    f"--add-data",
    f"{root / 'LICENSE'}{pathsep}.",
    *build_options,
    target_install,
], check=True)

with open(installer_file, "rb") as fin:
    sha256 = hashlib.sha256(fin.read()).hexdigest()
    print(f"{basename(installer_file).ljust(25)} SHA256: {sha256}")
