import subprocess
import shutil
from pathlib import Path
from os import makedirs, chdir, pathsep
from sys import executable

root           = Path(__file__).parent.absolute()
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
    "--console",
    "--onefile",
    "--add-data",
    f"{build / 'dist.tar'}{pathsep}.",
    f"--add-data",
    f"{root / 'LICENSE'}{pathsep}.",
    *build_options,
    target_install,
], check=True)
