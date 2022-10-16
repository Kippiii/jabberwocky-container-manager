from src.containers.container_manager import ContainerManager

def main():
    cm = ContainerManager()
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

    print("Success!")


if __name__ == "__main__":
    main()