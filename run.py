from src.containers.container import Container

def main():
    c = Container("sparc", "hdd.qcow2")
    c.start()
    c.stop()
    print("Success!")


if __name__ == "__main__":
    main()