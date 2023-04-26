"""
Builds new containers
"""

import json
import os
import random
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
    """
    Generates the default manifest file for a new container to be built
    """
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


def make_skeleton(working_dir: Path) -> None:
    """
    Creates the skeleton for a build generator

    :param working_dir: The directory to generate the build setup
    """
    if working_dir.exists() and not (
        working_dir.is_dir() and not os.listdir(working_dir)
    ):
        raise FileExistsError(f"{working_dir} is a file or non-empty directory.")

    os.makedirs(working_dir / "resources")
    os.makedirs(working_dir / "scripts")
    os.makedirs(working_dir / "packages")
    os.makedirs(working_dir / "build")
    os.makedirs(working_dir / "build" / "temp")
    with open(working_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(generate_default_manifest(), f, indent=4)


def clean(working_dir: Path, stdin: TextIO, stdout: TextIO, stderr: TextIO) -> None:
    """
    Deletes the build init directory

    :param working_dir: The build init directory to delete
    """
    if not is_supported_platform():
        raise OSError(f"{sys.platform} does not support building.")
    if not is_skeleton(working_dir):
        raise RuntimeError(f"Provided path '{working_dir}' is not an init'd directory.")

    subprocess.run([
        *([] if os.geteuid() == 0 else [which("sudo")]),
        which("bash"),
        get_scripts_path() / "clean.sh",
        working_dir,
    ], stdin=stdin, stdout=stdout, stderr=stderr, check=True)


def is_supported_platform() -> bool:
    """
    Checks if platform supports debootstrap
    """
    return sys.platform == "linux"


def is_skeleton(working_dir: Path) -> bool:
    """
    Checks if a directory is a skeleton for build init
    """
    return all(
        [
            (working_dir.is_dir()),
            (working_dir / "resources").is_dir(),
            (working_dir / "scripts").is_dir(),
            (working_dir / "packages").is_dir(),
            (working_dir / "build" / "temp").is_dir(),
            (working_dir / "manifest.json").is_file(),
        ]
    )


def missing_required_tools() -> List[str]:
    """
    Checks if any tools are missing that need to be installed to build
    """
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
    if not which("awk"):
        missing.append("awk")
    if not which("sed"):
        missing.append("sed")

    return missing


def do_debootstrap(
    working_dir: Path, stdin: TextIO, stdout: TextIO, stderr: TextIO
) -> None:
    """
    Starts the build process

    :param working_dir: The directory to build from
    :param stdin: The standard in stream
    :param stdout: The standard out stream
    :param stderr: The standard error stream
    """
    if not is_supported_platform():
        raise OSError(f"{sys.platform} does not support building.")
    if not is_skeleton(working_dir):
        raise RuntimeError(f"Provided path '{working_dir}' is not an init'd directory.")
    if missing := missing_required_tools():
        raise RuntimeError(
            "The following tools are required but are not installed: "
            f"{', '.join(missing)}"
        )

    with open(working_dir / "manifest.json", "r", encoding="utf-8") as jfp:
        manifest = ContainerManifest(json.load(jfp))

    if not Path(f"/proc/sys/fs/binfmt_misc/qemu-{manifest.arch}").is_file():
        if _sys_arch_to_debian_arch(manifest.arch) != _sys_arch_to_debian_arch(
            machine()
        ):
            raise RuntimeError(
                f"qemu-{manifest.arch} is not registered in binfmt_misc."
                f" Try `sudo update-binfmts --enable qemu-{manifest.arch}`"
            )

    username = subprocess.check_output("whoami", shell=True).strip().decode("utf-8")
    usergroup = (
        subprocess.check_output(f"id -gn {username}", shell=True)
        .strip()
        .decode("utf-8")
    )
    assert not (" " in username or " " in usergroup)

    subprocess.run(
        [
            *([] if os.geteuid() == 0 else [which("sudo")]),
            which("bash"),
            get_scripts_path() / "build.sh",
            username,
            usergroup,
            working_dir,
            manifest.password,
            manifest.hostname,
            f"{manifest.hddmaxsize}G",
            manifest.aptpkgs,
            _sys_arch_to_debian_arch(machine()),
            _sys_arch_to_debian_arch(manifest.arch),
            " ".join(_full_script_order(working_dir, manifest)),
            manifest.release,
        ],
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        check=True,
    )


def do_export(working_dir: Path, compress=True) -> None:
    """
    Exports the result of the build to an archive

    :param working_dir: The directory where the build occured
    :param compress: Whether or not to output to a compressed tar
    """
    with open(working_dir / "manifest.json", "r", encoding="utf-8") as jfp:
        manifest = ContainerManifest(json.load(jfp))

    archive_fname = "jcontainer.tar" + ".gz" * compress

    with open(
        working_dir / "build" / "temp" / "config.json", "w", encoding="utf-8"
    ) as config:
        json.dump(manifest.config().to_dict(), config)

    with tarfile.open(
        working_dir / "build" / archive_fname, "w:gz" if compress else "w"
    ) as tar:
        tar.add(working_dir / "build" / "temp" / "config.json", arcname="config.json")
        tar.add(working_dir / "build" / "temp" / "hdd.qcow2", arcname="hdd.qcow2")
        tar.add(working_dir / "build" / "temp" / "vmlinuz", arcname="vmlinuz")
        tar.add(working_dir / "build" / "temp" / "initrd.img", arcname="initrd.img")


def _sys_arch_to_debian_arch(arch: str):
    """
    Converts the arch of the system to a debian-based arch

    :param arch: The arch string of the system
    """
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


def _full_script_order(working_dir: Path, manifest: ContainerManifest) -> List[str]:
    """
    Generates order of scripts to be executed

    :param working_dir: The directory of building
    :param manifest: The manifest object for
    """
    allscripts = os.listdir(working_dir / "scripts")

    if any(" " in x for x in allscripts):
        raise RuntimeError("Script file names cannot contain spaces.")

    if len(missing := set(manifest.scriptorder).difference(allscripts)):
        raise RuntimeError(
            "The following scripts were specified in scriptorder but were not found "
            f"in the scripts directory: {missing}"
        )

    return manifest.scriptorder + list(set(allscripts).difference(manifest.scriptorder))
