import re
from typing import Dict, List, Any, Union
from src.containers.exceptions import InvalidManifestError
from src.containers.container_config import ContainerConfig


class ContainerManifest(ContainerConfig):
    aptpkgs: Union[str, List[str]]
    scriptorder: List[str]
    release: str

    def __init__(self, manifest: dict):
        manifest_errors = []
        aptpkgs = ""

        try:
            super().__init__(manifest)
        except InvalidManifestError as ex:
            manifest_errors.append(str(ex))

        if "aptpkgs" in manifest:
            val = manifest["aptpkgs"]
            if type(val) is list and all(type(i) is str for i in val):
                val = " ".join(val)
            if type(val) is str and all(" " <= i <= "z" for i in val):
                aptpkgs = val.strip()
            else:
                manifest_errors.append("'aptpkgs' must be a string or list of strings.")

        if "scriptorder" not in manifest:
            pass
        elif type(sorder := manifest["scriptorder"]) is not list:
            manifest_errors.append(f"'scriptorder' must be an array.")
        else:
            for fname in sorder:
                if type(fname) is not str:
                    manifest_errors.append(f"Invalid file name '{fname}'.")

        if manifest.get("release") not in (None, "bullseye", "bookworm"):
            manifest_errors.append("'release' must be either bullseye or bookworm.")

        # Raise errors if applicable
        if manifest_errors:
            raise InvalidManifestError("\n".join(manifest_errors))

        # Done with guard clasues
        self.aptpkgs = aptpkgs
        self.scriptorder = manifest.get("scriptorder") or []
        self.release = manifest.get("release") or "bullseye"

    def to_dict(self) -> Dict[str, Any]:
        manifest = super().to_dict()
        manifest["aptpkgs"] = self.aptpkgs
        manifest["scriptorder"] = self.scriptorder
        manifest["release"] = self.release
        return manifest

    def config(self) -> ContainerConfig:
        return super()
