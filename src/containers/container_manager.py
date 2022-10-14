from typing import Dict

from src.containers.container import Container

class ContainerManager:
    containers: Dict[str, Container]

    def __init__(self) -> None:
        pass

    def start(self, container_name: str):
        pass

    def stop(self, container_name: str):
        pass
