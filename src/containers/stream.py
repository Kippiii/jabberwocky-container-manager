from sys import stdin, stdout

class MyStream():
    """
    A custom Stream for dealing with fabric
    """
    unechoed_input: str = ""

    def __init__(self):
        pass

    def read(self, *args, **kwargs):
        """
        Reads from stdin
        """
        inp = stdin.read(*args, **kwargs)
        if len(inp) == 1 and ord(inp) == 4:
            return ""
        self.unechoed_input = inp
        return inp

    def fileno(self, *args, **kwargs):
        return stdin.fileno(*args, **kwargs)
    
    def write(self, content, *args, **kwargs):
        """
        Writes to stdout
        """
        if content[0] == "\r":
            content = content[1:]
        if content.encode() == self.unechoed_input.encode():
            self.unechoed_input = ""
            return ""
        return stdout.write(content, *args, **kwargs)
    
    def flush(self, *args, **kwargs):
        """
        Flushes stdout
        """
        return stdout.flush(*args, **kwargs)