import re
from typing import Dict, Any, List
from src.globals import MANIFEST_VERSION, SUPPORTED_ARCHS
from src.containers.exceptions import UnsupportedLegacyConfigError, InvalidConfigError

_LEGACY_CT_CONFIG = {
    "arch": "x86_64",
    "arguments": {
        "m": "500M",
        "drive": "file=hdd.qcow2,format=qcow2"
    }
}


class ContainerConfig:
    arch: str
    memory: int
    hddmaxsize: int
    hostname: str
    username: str = "root"
    password: str
    portfwd: List[List[int]]
    legacy: bool

    def __init__(self, manifest: dict):
        if (version := manifest.get("manifest")) is None:
            manifest = ContainerConfig._convert_legacy(manifest)
        elif version not in range(0, MANIFEST_VERSION + 1):
            raise InvalidConfigError(f"Unknown manifest version {version.__repr__()}")

        config_errors = []

        if "arch" not in manifest:
            config_errors.append("'arch' is not an optional field.")
        elif (arch := manifest["arch"]) not in SUPPORTED_ARCHS:
            config_errors.append(f"'{arch}' is not a valid architecture.")

        if "hostname" not in manifest:
            pass
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]{2,}", (hname := manifest["hostname"])):
            config_errors.append(f"Invalid hostname {hname.__repr__()}")

        if "memory" not in manifest:
            config_errors.append("'memory' is not an optional field.")
        elif type(manifest["memory"]) is not int:
            config_errors.append(f"'memory' must be an integer.")

        if "hddmaxsize" not in manifest:
            config_errors.append("'hddmaxsize' is not an optional field.")
        elif type(manifest["hddmaxsize"]) is not int:
            config_errors.append(f"'hddmaxsize' must be an integer.")

        if "portfwd" not in manifest:
            pass
        elif type(portfwd := manifest["portfwd"]) is not list:
            config_errors.append("'portfwd' must be an array.")
        elif not all(len(l) == 2 and all(type(i) is int for i in l) for l in portfwd):
            config_errors.append("The 'portfwd' argument is malformed.")
        else:
            vtaken = {22}
            htaken = {22}
            for vport, hport in portfwd:
                if vport not in range(1, 65535):
                    config_errors.append(f"Invalid port '{vport}'.")
                elif vport in vtaken:
                    config_errors.append(f"Virtual port {vport} used more than once.")
                else:
                    vtaken.add(vport)
                if hport not in range(1, 65535):
                    config_errors.append(f"Invalid port '{hport}'.")
                elif hport in htaken:
                    config_errors.append(f"Host port {hport} used more than once.")
                else:
                    htaken.add(hport)

        if (pswd := manifest.get("password")) is None:
            config_errors.append("'password' is not an optional field.")
        elif type(pswd) is not str:
            config_errors.append("'password' must be a string.")

        # Raise errors if applicable
        if config_errors:
            raise InvalidConfigError("\n".join(config_errors))

        # Done with guard clasues
        self.arch = manifest["arch"]
        self.memory = manifest["memory"]
        self.hddmaxsize = manifest["hddmaxsize"]
        self.hostname = manifest.get("hostname") or "debian"
        self.portfwd = manifest.get("portfwd") or []
        self.password = manifest["password"]
        self.legacy = manifest.get("__legacy") if type(manifest.get("__legacy")) is bool else False


    def _convert_legacy(manifest: dict) -> dict:
        if manifest == _LEGACY_CT_CONFIG:
            return {
                "manifest": 0,
                "arch": "x86_64",
                "memory": 2500,
                "hddmaxsize": 25,
                "hostname": "debian",
                "portfwd": [],
                "username": "root",
                "password": "root",
                "__legacy": True,
            }

        raise UnsupportedLegacyConfigError()


    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest": MANIFEST_VERSION,
            "arch": self.arch,
            "memory": self.memory,
            "hddmaxsize": self.hddmaxsize,
            "hostname": self.hostname,
            "portfwd": self.portfwd,
            "username": self.username,
            "password": self.password,
            **({"__legacy": True} if self.legacy else {}),
        }

    def load_legacy_config(config: Dict[str, Any]) -> "ContainerConfig":
        raise NotImplementedError()
