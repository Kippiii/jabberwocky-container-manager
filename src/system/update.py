import hashlib
import os
import re
import subprocess
import sys
import tempfile
from distutils.version import StrictVersion
from pathlib import Path
from platform import machine
from sys import platform
from typing import Tuple

import requests
from github import Github
from github.GitRelease import GitRelease
from github.GitReleaseAsset import GitReleaseAsset

from src.containers.container_manager_client import ContainerManagerClient
from src.globals import VERSION

EXE_FILE_EXTEN = ".exe" if platform == "win32" else ""


def get_newest_supported_version() -> Tuple[
    GitRelease, GitReleaseAsset
] | Tuple[None, None]:
    g = Github()
    repo = g.get_repo("Kippiii/jabberwocky-container-manager")

    releases = [
        r
        for r in repo.get_releases()
        if r.title.startswith("v")
        and StrictVersion(VERSION[1:]) < StrictVersion(r.title[1:])
    ]
    releases.sort(key=lambda r: StrictVersion(r.title[1:]), reverse=True)

    for release in releases:
        for asset in release.get_assets():
            if asset.name == f"installer-{platform}-{machine()}{EXE_FILE_EXTEN}":
                return release, asset

    return None, None


def update(release: GitRelease, asset: GitReleaseAsset):
    """
    Searches for updates and installs them if needed
    """
    # Search for latest release
    ContainerManagerClient().server_halt()

    sha_regex = r"installer-%s-%s%s\s+SHA256: ([a-zA-Z0-9]{64})" % (
        platform,
        machine(),
        EXE_FILE_EXTEN,
    )
    sha = re.search(sha_regex, release.body, re.MULTILINE).group(1)

    r = requests.get(asset.browser_download_url)
    p = Path(tempfile.gettempdir()) / asset.name

    # Verify Installer
    if hashlib.sha256(r.content).hexdigest().upper() != sha.upper():
        raise RuntimeError("Bad Checksum!!! Try updating again later.")

    with open(p, "wb") as f:
        f.write(r.content)

    if platform == "win32":
        subprocess.Popen([p], creationflags=subprocess.CREATE_NEW_CONSOLE)
        sys.exit(0)
    else:
        subprocess.run(["chmod", "+x", p], shell=False)
        os.execl(p, p)

    raise RuntimeError("This state should not be possible.")
