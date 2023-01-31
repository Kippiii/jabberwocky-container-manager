import threading
from time import sleep
from typing import Optional, Callable, Iterable

class SpinningTask:
    """
    Perform a task that takes a long time. Provides a progress spinner.

    :param exception: Exception raised by thread, if any.
    :param prompt: The prompt showed to the user while the task is being performed.
    :param target: The function to be executed.
    :param args: Arguments to the function.
    """
    exception: Optional[Exception] = None
    prompt : str
    target: Callable[[], None]
    args: Iterable

    def __init__(self, prompt: str, target: Callable[[], None], args: Iterable = ()) -> None:
        self.prompt = prompt
        self.target = target
        self.args = args

    def exec(self):
        """
        Execute the target task.
        """
        thread = threading.Thread(target=self._task)
        thread.start()

        spinner = ("|", "/", "-", "\\")
        idx = 0

        while thread.is_alive():
            print(f"\r{self.prompt}... {spinner[idx]} ", end="\r")
            idx = (idx + 1) % len(spinner)
            sleep(0.1)

        thread.join()

        if self.exception is not None:
            print()
            raise self.exception
        else:
            print(f"\r{self.prompt}... Done!")

    def _task(self):
        """
        Executes the target. Catches any exceptions to be raised by main thread.
        """
        try:
            self.target(*self.args)
        except Exception as ex:  # pylint: disable=broad-except
            self.exception = ex
