import logging
from sys import stdin, stdout

from src.containers.container_manager import ContainerManager

class MyInStream:
    logger: logging.Logger

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def read(self, *args, **kwargs):
        inp = stdin.read(*args, **kwargs)
        # inp = self.file.read(*args, **kwargs)
        if len(inp) > 0 and ord(inp) == 4:
            return ""
        self.logger.info("Read %d", ord(inp) if len(inp) == 1 else -1)
        return inp


def main():
    logging.basicConfig()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    cm = ContainerManager(logger=logger)
    cm.start("base")
    try:
        cm.run_command("base", "rm -f echo.c")
        cm.run_command("base", "rm -f a.out")
        cm.put_file("base", "echo.c", "echo.c")
        cm.run_command("base", "apt install -y gcc")
        cm.run_command("base", "gcc echo.c")
        cm.run_command("base", "./a.out")
        cm.get_file("base", "a.out", "a.out")
        cm.stop("base")
    except Exception as e:
        cm.stop("base")
        raise e

    logger.info("Success!")


if __name__ == "__main__":
    main()