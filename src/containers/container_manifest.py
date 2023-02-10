import re
import random
from typing import Dict, List, Any
from src.containers.exceptions import InvalidManifestError
from src.containers.container_config import ContainerConfig


class ContainerManifest(ContainerConfig):
    aptpkgs: List[str]
    scriptorder: List[str]

    def __init__(self, manifest: dict):
        manifest_errors = []
        if "password" not in manifest:
            manifest = manifest.copy()
            manifest["password"] = ContainerManifest._random_password()

        try:
            super().__init__(manifest)
        except InvalidManifestError as ex:
            manifest_errors.append(str(ex))

        if "aptpkgs" not in manifest:
            pass
        elif type(aptpkgs := manifest["aptpkgs"]) is not list:
            manifest_errors.append("'aptpkgs' must be a list.")
        else:
            for pkg in aptpkgs:
                if pkg is not str or not re.fullmatch(r"[a-zA-Z0-9\-]", pkg):
                    manifest_errors.append(f"Invalid package name '{pkg}'.")

        if "scriptorder" not in manifest:
            pass
        elif type(sorder := manifest["scriptorder"]) is not list:
            manifest_errors.append(f"'scriptorder' must be an array.")
        else:
            for fname in sorder:
                if type(fname) is not str:
                    manifest_errors.append(f"Invalid file name '{fname}'.")

        # Raise errors if applicable
        if manifest_errors:
            raise InvalidManifestError("\n".join(manifest_errors))

        # Done with guard clasues
        self.aptpkgs = manifest.get("aptpkgs") or []
        self.scriptorder = manifest.get("scriptorder") or []

    def to_dict(self) -> Dict[str, Any]:
        manifest = super().to_dict()
        manifest["aptpkgs"] = self.aptpkgs
        manifest["scriptorder"] = self.scriptorder
        return manifest

    def _random_password() -> str:
        return ''.join([chr(random.choice(range(65, 90))) for _ in range(30)])
