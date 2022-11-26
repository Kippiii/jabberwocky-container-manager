import subprocess
import shutil
import base64
from pathlib import Path
from os import makedirs, chdir
from sys import executable

root           = Path(__file__).parent
build          = root / "build/"
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
    "--distpath", "dist"
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


shutil.make_archive(build / "dist", "tar", build / "dist")

with open(build / "dist.tar", "rb") as f:
    build_base64 = base64.b64encode(f.read())

with open(root / "LICENSE") as f:
    build_license = f.read()

with open(target_install, "r") as fsrc, open(build / "installer.py", "w") as fdest:
    for line in fsrc.readlines():
        if line.startswith("BUILD_BASE64"):
            fdest.write(f"BUILD_BASE64 = {build_base64}\n")
        elif line.startswith("BUILD_LICENSE"):
            fdest.write(f"BUILD_LICENSE = {build_license.__repr__()}\n")
        else:
            fdest.write(line)


subprocess.run([
    *pyinstaller,
    "--console",
    "--onefile",
    *build_options,
    build / "installer.py",
], check=True)