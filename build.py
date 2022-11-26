import subprocess
import shutil
from pathlib import Path
from os import makedirs, chdir, remove

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
build_options = [
    "--workpath", "work",
    "--specpath", "spec",
    "--distpath", "VDevBox"
]

subprocess.run([
    "pyinstaller",
    "--name",
    "cman",
    *build_options,
    target_run,
], shell=True, check=True)

subprocess.run([
    "pyinstaller",
    "--noconsole",
    *build_options,
    target_server,
], shell=True, check=True)

subprocess.run([
    "pyinstaller",
    "--onefile",
    *build_options,
    target_install,
], shell=True, check=True)


# Zip
shutil.make_archive(build / "VDevBox", "zip", build / "VDevBox")
