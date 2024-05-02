from .base_connector import BaseConnector
import requests
import json


class ExtensibleConnector(BaseConnector):
    def __init__(self, endpoint: str="http://127.0.0.1:5000/api/push_tasks"):
        """
        Initialize the Extensible Connector.
        """
        self.credentials = {}
        self.endpoint = endpoint 


    def flush(self, logs: list):
        """
        Flushes the provided logs using the connector.

        Args:
            logs (list): A list of log entries to be flushed.
        """
        try:
            headers = {"Content-Type": "application/json"}
            data = json.dumps(logs)

            response = requests.post(self.endpoint, headers=headers, data=data)
            if response.status_code != 201:
                print(f"Failed to push logs: {response.text}")

        except Exception as e:
            print(f"An error occurred while pushing logs: {e}")
            
