from typing import List


class Connector:
    def __init__(self):
        """
        Initialize the Connector.
        """
        pass
    
    def flush(self, logs: List):
        """
        This method should be overridden by subclasses.
        """
        raise NotImplementedError("The flush method must be implemented by subclasses.")