import subprocess
import shutil
from pathlib import Path
from os import makedirs, chdir, remove
from sys import executable

root = Path(__file__).parent
build          = root  / "build/"
target_run     = root / "run.py"
target_server  = root / "server.py"
target_install = root / "installer" / "installer.py"


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
    "--distpath", "VDevBox"
]

subprocess.run([
    *pyinstaller,
    "--name",
    "cman",
    *build_options,
    target_run,
], check=True)

subprocess.run([
    *pyinstaller,
    "--noconsole",
    *build_options,
    target_server,
], check=True)

subprocess.run([
    *pyinstaller,
    "--console",
    "--onefile",
    *build_options,
    target_install,
], check=True)


# Zip
shutil.make_archive(build / "VDevBox", "zip", build / "VDevBox")
