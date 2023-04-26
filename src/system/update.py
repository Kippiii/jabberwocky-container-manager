"""
Used for updating the Jabberwocky tool
"""
import hashlib
import os
import re
import subprocess
import sys
import tempfile
from distutils.version import \
    StrictVersion  # pylint: disable=deprecated-module
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
    """
    Gets the newest release from Github

    :return: A tuple of the release object and the asset object
    """
    git = Github()
    repo = git.get_repo("Kippiii/jabberwocky-container-manager")

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

    sha_regex = (
        r"installer-%s-%s%s\s+SHA256: ([a-zA-Z0-9]{64})"  # pylint: disable=consider-using-f-string
        % (
            platform,
            machine(),
            EXE_FILE_EXTEN,
        )
    )
    sha = re.search(sha_regex, release.body, re.MULTILINE).group(1)

    req = requests.get(asset.browser_download_url, timeout=360 * 20)
    path = Path(tempfile.gettempdir()) / asset.name

    # Verify Installer
    if hashlib.sha256(req.content).hexdigest().upper() != sha.upper():
        raise RuntimeError("Bad Checksum!!! Try updating again later.")

    with open(path, "wb") as f:
        f.write(req.content)

    if platform == "win32":
        subprocess.Popen(  # pylint: disable=consider-using-with
            [path], creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        sys.exit(0)
    else:
        subprocess.run(["chmod", "+x", path], shell=False, check=False)
        os.execl(path, path)

    raise RuntimeError("This state should not be possible.")
