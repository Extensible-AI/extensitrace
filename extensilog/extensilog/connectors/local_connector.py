from __future__ import annotations
import json
from .base_connector import BaseConnector

class LocalConnector(BaseConnector):
    def __init__(self, log_file: str):
        """
        Initialize the Local Connector.
        """
        self.log_file = log_file 


    def flush(self, logs: list) -> None:
        """
        Flushes the provided logs into the local log file.

        This method attempts to read the existing data from the log file, appending the new logs to it.
        If the log file does not exist or is corrupted, it creates a new log file or overwrites the corrupted file.
        Finally, it writes the combined data back to the log file.

        Args:
            logs (list): A list of log entries to be written to the log file.
        """
        existing_data = []
        try:
            with open(self.log_file, 'r') as f:
                existing_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print('Creating new log file or overwriting corrupted file.')

        combined_data = existing_data + logs 
        try:
            with open(self.log_file, 'w') as f:
                json.dump(combined_data, f, indent=2)
        except Exception as e:
            print(f'Error writing to file: {e}')