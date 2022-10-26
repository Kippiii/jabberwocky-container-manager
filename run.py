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
    try:
        cm.start("planc")
        cm.run_command("planc", "rm -f echo.c")
        cm.run_command("planc", "rm -f a.out")
        cm.run_command("planc", "ls")
        cm.put_file("planc", "echo.c", "echo.c")
        cm.run_command("planc", "/sparc/bin/sparc-linux-gcc echo.c")
        cm.run_command("planc", "./a.out")
        cm.get_file("planc", "a.out", "a.out")
        cm.stop("planc")
    except Exception as e:
        cm.stop("planc")
        raise e

    logger.info("Success!")


if __name__ == "__main__":
    main()