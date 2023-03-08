import os
import sys
import json
import tarfile
import subprocess
from pathlib import Path
from shutil import which
from src.globals import MANIFEST_VERSION
from src.system.syspath import get_scripts_path
from src.system.multithreading import SpinningTask
from src.containers.container_manifest import ContainerManifest
from typing import List

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
    os.makedirs(wd / "build" / "temp")
    with open(wd / "manifest.json", 'w') as f:
        json.dump(DEFAULT_MANIFEST, f, indent=4)


def is_supported_platform() -> bool:
    return sys.platform == "linux"


def is_skeleton(wd: Path) -> bool:
    return all([
        (wd.is_dir()),
        (wd / "resources").is_dir(),
        (wd / "scripts").is_dir(),
        (wd / "packages").is_dir(),
        (wd / "build" / "temp").is_dir(),
        (wd / "manifest.json").is_file(),
    ])


def missing_required_tools() -> List[str]:
    missing = []

    if not which("sudo"):
        missing.append("sudo")
    if not which("debootstrap"):
        missing.append("debootstrap")
    if not which("chroot"):
        missing.append("chroot")
    if not which("virt-resize") or not which("virt-make-fs"):
        missing.append("guestfs-tools")

    return missing


def do_debootstrap(wd: Path) -> None:
    if not is_supported_platform():
        raise OSError(f"{sys.platform} does not support building.")
    if not is_skeleton(wd):
        raise RuntimeError(f"Provided path '{wd}' is not an init'd directory.")
    if missing := missing_required_tools():
        raise RuntimeError(f"The following tools are required but are not installed: {', '.join(missing)}")

    with open(wd / "manifest.json", "r") as jfp:
        manifest = ContainerManifest(json.load(jfp))

    p = subprocess.run([
        which("bash"),
        get_scripts_path() / "build.sh",
        wd / "build" / "temp" / "rootfs",
        wd / "build" / "temp" / "hdd.qcow2",
        wd / "build" / "temp" / "vmlinuz",
        wd / "build" / "temp" / "initrd.img",
        manifest.password,
        manifest.hostname,
        f"{manifest.hddmaxsize}G",
        ",".join(manifest.aptpkgs),
    ])

    if p.returncode != 0:
        sys.exit(p.returncode)


def do_export(wd: Path, compress=True) -> None:
    with open(wd / "manifest.json", "r") as jfp:
        manifest = ContainerManifest(json.load(jfp))

    archive_fname = f"jcontainer.tar" + ".gz" * compress

    with open(wd / "build" / "temp" / "config.json", "w") as config:
        json.dump(manifest.config().to_dict(), config)

    with tarfile.open(wd / "build" / archive_fname, "w:gz" if compress else "w") as tar:
        tar.add(wd / "build" / "temp" / "config.json", arcname="config.json")
        tar.add(wd / "build" / "temp" / "hdd.qcow2", arcname="hdd.qcow2")
        tar.add(wd / "build" / "temp" / "vmlinuz", arcname="vmlinuz")
        tar.add(wd / "build" / "temp" / "initrd.img", arcname="initrd.img")
