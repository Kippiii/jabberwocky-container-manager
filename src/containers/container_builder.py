import os
import json
from pathlib import Path
from src.globals import MANIFEST_VERSION

DEFAULT_MANIFEST = {
    "manifest": MANIFEST_VERSION,
    "arch": "x86_64",
    "memory": 500,
    "hddmaxsize": 10,
    "hostname": "debian",
    "portfwd": [],
    "aptpkgs": [],
    "scriptorder": [],
}

def make_skeleton(wd: Path) -> None:
    if wd.exists() and not (wd.is_dir() and not os.listdir(wd)):
        raise FileExistsError(f"{wd} is a file or non-empty directory.")

    os.makedirs(wd / "resources")
    os.makedirs(wd / "scripts")
    os.makedirs(wd / "packages")
    os.makedirs(wd / "build")
    os.makedirs(wd / "build" / "dist")
    os.makedirs(wd / "build" / "temp")
    with open(wd / "manifest.json", 'w') as f:
        json.dump(DEFAULT_MANIFEST, f, indent=4)
