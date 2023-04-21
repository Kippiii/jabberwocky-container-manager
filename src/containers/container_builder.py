"""
Builds new containers
"""

import json
import os
import random
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from platform import machine
from shutil import which
from typing import List, TextIO

from src.containers.container_manifest import ContainerManifest
from src.globals import MANIFEST_VERSION
from src.system.syspath import get_scripts_path


def generate_default_manifest():
    return {
        "manifest": MANIFEST_VERSION,
        "arch": "x86_64",
        "memory": 500,
        "hddmaxsize": 10,
        "hostname": "debian",
        "release": "bullseye",
        "portfwd": [],
        "aptpkgs": "",
        "scriptorder": [],
        "password": "".join([chr(random.choice(range(65, 90))) for _ in range(30)]),
    }


def make_skeleton(work_dir: Path) -> None:
    if work_dir.exists() and not (work_dir.is_dir() and not os.listdir(work_dir)):
        raise FileExistsError(f"{work_dir} is a file or non-empty directory.")

    os.makedirs(work_dir / "resources")
    os.makedirs(work_dir / "scripts")
    os.makedirs(work_dir / "packages")
    os.makedirs(work_dir / "build")
    os.makedirs(work_dir / "build" / "temp")
    with open(work_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(generate_default_manifest(), f, indent=4)


def clean(work_dir: Path) -> None:
    if not is_skeleton(work_dir):
        raise RuntimeError(f"Provided path '{work_dir}' is not an init'd directory.")
    shutil.rmtree(work_dir / "build" / "temp")
    os.mkdir(work_dir / "build" / "temp")


def is_supported_platform() -> bool:
    return sys.platform == "linux"


def is_skeleton(work_dir: Path) -> bool:
    return all(
        [
            (work_dir.is_dir()),
            (work_dir / "resources").is_dir(),
            (work_dir / "scripts").is_dir(),
            (work_dir / "packages").is_dir(),
            (work_dir / "build" / "temp").is_dir(),
            (work_dir / "manifest.json").is_file(),
        ]
    )


def missing_required_tools() -> List[str]:
    missing = []

    if (os.geteuid() != 0) and (not which("sudo")):
        missing.append("sudo")
    if not which("bash"):
        missing.append("bash")
    if not which("debootstrap"):
        missing.append("debootstrap")
    if not which("chroot"):
        missing.append("chroot")
    if not which("virt-resize") or not which("virt-make-fs"):
        missing.append("guestfs-tools")

    return missing


def do_debootstrap(
    work_dir: Path, stdin: TextIO, stdout: TextIO, stderr: TextIO
) -> None:
    if not is_supported_platform():
        raise OSError(f"{sys.platform} does not support building.")
    if not is_skeleton(work_dir):
        raise RuntimeError(f"Provided path '{work_dir}' is not an init'd directory.")
    if missing := missing_required_tools():
        raise RuntimeError(
            "The following tools are required but are not installed: "
            f"{', '.join(missing)}"
        )

    with open(work_dir / "manifest.json", "r", encoding="utf-8") as jfp:
        manifest = ContainerManifest(json.load(jfp))

    subprocess.run(
        [
            which("bash"),
            get_scripts_path() / "build.sh",
            work_dir,
            manifest.password,
            manifest.hostname,
            f"{manifest.hddmaxsize}G",
            manifest.aptpkgs,
            _sys_arch_to_debian_arch(machine()),
            _sys_arch_to_debian_arch(manifest.arch),
            " ".join(_full_script_order(work_dir, manifest)),
            manifest.release,
        ],
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        check=True,
    )


def do_export(work_dir: Path, compress=True) -> None:
    with open(work_dir / "manifest.json", "r", encoding="utf-8") as jfp:
        manifest = ContainerManifest(json.load(jfp))

    archive_fname = "jcontainer.tar" + ".gz" * compress

    with open(
        work_dir / "build" / "temp" / "config.json", "w", encoding="utf-8"
    ) as config:
        json.dump(manifest.config().to_dict(), config)

    with tarfile.open(
        work_dir / "build" / archive_fname, "w:gz" if compress else "w"
    ) as tar:
        tar.add(work_dir / "build" / "temp" / "config.json", arcname="config.json")
        tar.add(work_dir / "build" / "temp" / "hdd.qcow2", arcname="hdd.qcow2")
        tar.add(work_dir / "build" / "temp" / "vmlinuz", arcname="vmlinuz")
        tar.add(work_dir / "build" / "temp" / "initrd.img", arcname="initrd.img")


def _sys_arch_to_debian_arch(arch: str):
    arch = arch.lower()

    if arch in ("amd64", "x86_64"):
        return "amd64"
    if arch in ("arm64", "aarch64"):
        return "arm64"
    if arch in ("mipsel",):
        return "mipsel"
    # if arch in ("mips64el", ):
    #     return "mips64el"

    return "UNKNOWN"


def _full_script_order(work_dir: Path, manifest: ContainerManifest) -> List[str]:
    allscripts = os.listdir(work_dir / "scripts")

    if any(" " in x for x in allscripts):
        raise RuntimeError("Script file names cannot contain spaces.")

    if len(missing := set(manifest.scriptorder).difference(allscripts)):
        raise RuntimeError(
            "The following scripts were specified in scriptorder but were not found "
            f"in the scripts directory: {missing}"
        )

    return manifest.scriptorder + list(set(allscripts).difference(manifest.scriptorder))
