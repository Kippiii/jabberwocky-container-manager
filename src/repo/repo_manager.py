import json
import requests
from pathlib import Path
from dataclasses import dataclass
from typing import List

from src.repo.syspath import get_repo_file

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
            resp = requests.get(self.url)
            if not resp.ok:
                raise Exception(f"Got status code {resp.status_code} from {self.url}")
            data = resp.json()
            if "archives" not in data or not isinstance(data['archives'], list):
                raise ValueError("Got invalid data from server")
            self.archives = [str(x) for x in data['archives']]

    def __init__(self) -> None:
        repo_json_path: Path = get_repo_file()
        repos: List[_Repo] = []

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
                self.repos.append(_Repo(repo_dict['url'], [str(x) for x in repo_dict['archives']]))

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
                self.save_archives()
                self.save()
                return
        raise ValueError(f"{repo_url} does not exist. Please add it using add_repo")

    def add_repo(self, repo_url: str) -> None:
        """
        Adds a repo to the list

        :param repo_url: The url of the repo to add
        """
        repo: _Repo = _Repo(repo_url, [])
        repo.save_archives()
        self.repos.append(repo)
        self.save()

    def download(self, archive_str: str, container_name: str) -> None:
        """
        Downloads an archive and installs it with the given container name

        :param archive_str: The name of the archive to be installed
        :param container_name: THe name that will be given to the container
        """
        # TODO
