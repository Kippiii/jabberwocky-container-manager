from sys import stdin, stdout

class MyStream():
    """
    A custom Stream for dealing with fabric
    """
    def __init__(self):
        pass

    def read(self, *args, **kwargs):
        """
        Reads from stdin
        """
        inp = stdin.read(*args, **kwargs)
        if len(inp) == 1 and ord(inp) == 4:
            return ""
        return inp
    
    def write(self, *args, **kwargs):
        """
        Writes to stdout
        """
        return stdout.write(*args, **kwargs)
    
    def flush(self, *args, **kwargs):
        """
        Flushes stdout
        """
        return stdout.flush(*args, **kwargs)