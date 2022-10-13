from pathlib import Path
import pexpect
from pexpect import popen_spawn

class Container:
    def __init__(self) -> None:
        pass

    def start(self) -> None:
        arch: str = "sparc"
        ex_port: int = 10029
        qemu_file: Path = Path("hdd.qcow2")
        booter = popen_spawn.PopenSpawn(f"qemu-system-{arch} -M SS-20 -drive file={qemu_file},format=qcow2 -net user,hostfwd=tcp::{ex_port}-:22 -net nic -m 1G -nographic")
        booter.expect("debian login: ", timeout=360)
        booter.sendline("root")
        booter.expect("Password: ")
        booter.sendline("root")
        booter.expect("debian:~#")
        print("Successfully booted!")
        booter.kill(0)