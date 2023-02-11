import json
import requests
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional
from sys import stdout, stdin

from src.system.syspath import get_repo_file, get_container_dir, get_container_home

class RepoManager:
    """
    Manages aspects of the repos
    """

    @dataclass
    class _Repo:
        url: str
        archives: List[str]

        def to_dict(self) -> dict:
            return {
                'url': self.url,
                'archives': self.archives,
            }

        def save_archives(self) -> None:
            """
            Saves all of the archives listed into the object
            """
            try:
                resp = requests.get(self.url)
            except requests.exceptions.RequestException as exc:
                raise ValueError(f"Could not connect to {self.url}") with exc

            if not resp.ok:
                raise Exception(f"Got status code {resp.status_code} from {self.url}")
            try:
                data = resp.json()
            except json.JSONDecodeError as exc:
                raise ValueError("Web server gave invalid response")
            if "archives" not in data or not isinstance(data['archives'], list):
                raise ValueError("Got invalid data from server")
            self.archives = [str(x) for x in data['archives']]

    def __init__(self) -> None:
        repo_json_path: Path = get_repo_file()
        self.repos: List[RepoManager._Repo] = []

        if not repo_json_path.exists():
            with open(str(repo_json_path), 'w') as file:
                json.dump({"repos": []}, file)
        self.open()

    def open(self) -> None:
        """
        Loads information from repo json into memory
        """
        repo_json_path: Path = get_repo_file()
        with open(str(repo_json_path)) as file:
            config = json.load(file)
            if "repos" not in config or not isinstance(config['repos'], list):
                raise ValueError("'repos' list not in repo config")
            for repo_dict in config['repos']:
                if "url" not in repo_dict or not isinstance(repo_dict['url'], str):
                    raise ValueError("'url' string missing from a repo in list")
                if "archives" not in repo_dict or not isinstance(repo_dict['archives'], list):
                    raise ValueError(f"'archives' list missing from repo with url: {repo_dict['url']}")
                self.repos.append(RepoManager._Repo(repo_dict['url'], [str(x) for x in repo_dict['archives']]))

    def save(self) -> None:
        """
        Saves the information from memory into the repo json
        """
        repo_json_path: Path = get_repo_file()
        with open(str(repo_json_path), 'w') as file:
            json.dump({
                "repos": [repo.to_dict() for repo in self.repos],
            }, file)

    def update_repo(self, repo_url: str) -> None:
        """
        Updates the list of archives for the repo

        :param repo_url: The URL to the repo being updated
        """
        for repo in self.repos:
            if repo.url == repo_url:
                repo.save_archives()
                self.save()
                return
        raise ValueError(f"{repo_url} does not exist. Please add it using add_repo")

    def update_all(self) -> None:
        """
        Updates all repos
        """
        for repo in self.repos:
            self.update_repo(repo.url)

    def add_repo(self, repo_url: str) -> None:
        """
        Adds a repo to the list

        :param repo_url: The url of the repo to add
        """
        repo: RepoManager._Repo = RepoManager._Repo(repo_url, [])
        repo.save_archives()
        self.repos.append(repo)
        self.save()

    def download(self, archive_str: str) -> Optional[Path]:
        """
        Downloads an archive from a repo

        :param archive_str: The name of the archive to be installed
        :return: The path to the downloaded file
        """
        for repo in self.repos:
            stdout.write(f"Checking {repo.url}...\n")
            if archive_str not in repo.archives:
                stdout.write("Archive not found in repo\n")
                continue
            value: str = ""
            while len(value) == 0 or value[0] not in ['y', 'Y', 'n', 'N']:
                stdout.write("Archive found, should we download: [y, n]: ")
                stdout.flush()
                value = stdin.readline()
            if value[0] in ['n', 'N']:
                stdout.write("Skipping...\n")
                continue
            stdout.write("Downloading...\n")
            try:
                with requests.get(f"{repo.url}{'' if repo.url[-1] == '/' else '/'}get/{archive_str}", stream=True) as r:
                    p: Path = get_container_home() / archive_str
                    with open(p, "wb") as f:
                        for chunk in r.iter_content(chunk_size=32*1024*1024):
                            f.write(chunk)
            except requests.exceptions.RequestException as exc:
                raise ValueError(f"Could not connect to server {repo.url}") with exc
            
            stdout.write("Successfully downloaded archive\n")
            return p

        stdout.write("Could not find archive from repos\n")
        return None

    def upload(self, save_path: Path, repo_url: str, username: str, password: str) -> None:
        """
        Uploads an archive to a repo

        :param save_path: The path to the archive
        :param repo_url: The url to the repo for upload
        """
        data: dict = {
            "username": username,
            "password": password,
        }
        files: dict = {
            "file": open(str(save_path), 'rb'),
        }

        try:
            r = requests.post(f"{repo_url}{'' if repo_url[-1] == '/' else '/'}put", json=data, files=files)
        except requests.exceptions.RequestException as exc:
            raise ValueError(f"Could not connect to server {repo.url}") with exc
