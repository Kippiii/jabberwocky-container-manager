import logging

from src.containers.container_manager import ContainerManager

def main():
    logging.basicConfig()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    cm = ContainerManager(logger=logger)
    cm.start("hdd")
    try:
        cm.run_command("hdd", "rm -f echo.c")
        cm.run_command("hdd", "rm -f a.out")
        cm.put_file("hdd", "echo.c", "echo.c")
        cm.run_command("hdd", "gcc echo.c")
        cm.get_file("hdd", "a.out", "a.out")
        cm.stop("hdd")
    except Exception as e:
        cm.stop("hdd")
        raise e

    logger.info("Success!")


if __name__ == "__main__":
    main()