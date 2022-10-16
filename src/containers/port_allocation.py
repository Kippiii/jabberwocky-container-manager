from typing import Optional

class PortAllocator:
    cur_port: int = 12300

    def __init__(self) -> None:
        pass

    def allocate(self) -> int:
        self.cur_port += 1
        return self.cur_port - 1

pa: Optional[PortAllocator] = None
def allocate_port() -> int:
    global pa
    if pa is None:
        pa = PortAllocator()
    return pa.allocate()