from typing import Optional
from pathlib import Path
import pexpect
from pexpect import popen_spawn

class Container:
    booter: Optional[popen_spawn.PopenSpawn] = None
    ex_port: int = 10022
    qemu_file: Path
    arch: str

    def __init__(self, arch: str, qemu_file_path: str) -> None:
        self.qemu_file = Path(qemu_file_path)
        if not self.qemu_file.is_file():
            raise FileNotFoundError(qemu_file_path)
        self.arch = arch

    def start(self) -> None:
        self.booter = popen_spawn.PopenSpawn(f"qemu-system-{self.arch} -M SS-20 -drive file={self.qemu_file},format=qcow2 -net user,hostfwd=tcp::{self.ex_port}-:22 -net nic -m 1G -nographic")
        self.booter.expect("debian login: ", timeout=360)
        self.booter.sendline("root")
        self.booter.expect("Password: ")
        self.booter.sendline("root")
        self.booter.expect("debian:~#")

    def stop(self) -> None:
        self.booter.kill(0)