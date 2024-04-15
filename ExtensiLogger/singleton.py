import threading

class Singleton(type):
    """
    This is a thread-safe implementation of a Singleton metaclass.
    It ensures that a class has only one instance and provides a global point of access to it.
    """

    _instances = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
        return cls._instances[cls]