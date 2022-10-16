from typing import Dict

from src.containers.container import Container

class ContainerManager:
    containers: Dict[str, Container] = {}

    def __init__(self) -> None:
        pass

    def start(self, container_name: str) -> None:
        if container_name in self.containers:
            return # Raise exception
        self.containers[container_name] = Container(f"{container_name}.qcow2")
        self.containers[container_name].start()

    def stop(self, container_name: str):
        if container_name not in self.containers:
            return # Raise exception
        self.containers[container_name].stop()
        del self.containers[container_name]

    def run_command(self, container_name: str, cmd: str) -> None:
        if container_name not in self.containers:
            return # Raise exception
        self.containers[container_name].run(cmd)
    
    def get_file(self, container_name: str, remote_file: str, local_file: str) -> None:
        if container_name not in self.containers:
            return # Raise exception
        self.containers[container_name].get(remote_file, local_file)

    def put_file(self, container_name: str, local_file: str, remote_file: str) -> None:
        if container_name not in self.containers:
            return # Raise exception
        self.containers[container_name].put(local_file, remote_file)
