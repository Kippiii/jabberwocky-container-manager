import logging
from sys import stdin, stdout

from src.containers.container import Container


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

    # cm = ContainerManager(logger=logger)
    # cm.start("planb")
    # try:
    #     cm.run_command("planb", "rm -f echo.c")
    #     cm.run_command("planb", "rm -f a.out")
    #     cm.put_file("planb", "echo.c", "echo.c")
    #     cm.run_command("planb", "gcc echo.c")
    #     cm.run_command("planb", "./a.out")
    #     cm.get_file("planb", "a.out", "a.out")
    #     cm.stop("planb")
    # except Exception as e:
    #     cm.stop("planb")
    #     raise e

    ct = Container('ct', logger)
    ct.start()

    try:
        ct.sshi.__update_hostkey__()
        ct.run('ls')
        ct.run('rm -f echo.c')
        #ct.run('rm -f a.out')
        ct.put('echo.c', 'echo.c')
        ct.run('sparc-linux-gcc echo.c')
        ct.run('./a.out')
        ct.get('a.out', 'a.out')
    except Exception as ex:
        ct.stop()
        logger.info(ex)
    else:
        ct.stop()
        logger.info("Success!")


if __name__ == "__main__":
    main()
