import threading

class Singleton:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def instance(cls, *args, **kwargs):
        print("instance called")
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(*args, **kwargs)
        return cls._instance


class Logger(Singleton):
    def __init__(self, name: str):
        print(f"Initializing Logger with name: {name}")
        self.name = name


# Correct usage
logger1 = Logger.instance("App")
logger2 = Logger.instance("App2")

print(logger1 is logger2)       # True
print(logger1.name, logger2.name)  # Both show 'App' (first init persists)
