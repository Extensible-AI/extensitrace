from abc import ABC, abstractmethod
from typing import List


class BaseConnector(ABC):
    def __init__(self):
        """
        Initialize the Connector.
        """
        pass
    
    @abstractmethod
    def flush(self, logs: List):
        """
        This method should be overridden by subclasses.
        """
        raise NotImplementedError("This method must be implemented by the subclass.")
