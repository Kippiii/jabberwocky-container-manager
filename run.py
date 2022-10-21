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
    cm.start("test")
    try:
        cm.run_command("test", "rm -f echo.c")
        cm.run_command("test", "rm -f a.out")
        cm.put_file("test", "echo.c", "echo.c")
        cm.run_command("test", "gcc echo.c")
        cm.run_command("test", "./a.out")
        cm.get_file("test", "a.out", "a.out")
        cm.stop("test")
    except Exception as e:
        cm.stop("test")
        raise e

    logger.info("Success!")


if __name__ == "__main__":
    main()