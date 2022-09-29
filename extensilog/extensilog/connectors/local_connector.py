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
        Flushes the provided logs into the local log file without loading the file into memory.

        This method appends the new logs directly to the log file in a JSON Lines (jsonl) format. 
        If the log file does not exist, it creates a new log file. This approach allows for efficient 
        appends and easy parsing of individual log entries without needing to load the entire file into memory.

        Args:
            logs (list): A list of log entries to be written to the log file.
        """
        try:
            # Open the file in append mode, creating it if it doesn't exist
            with open(self.log_file, 'a') as f:
                for log in logs:
                    # Write each log entry as a new line in JSON Lines format
                    f.write(json.dumps(log) + '\n')
        except Exception as e:
            print(f'Error appending to file: {e}')
