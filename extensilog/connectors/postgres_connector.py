import json
import psycopg2
import atexit
from psycopg2 import OperationalError
from extensilog.model import Task

from .base_connector import BaseConnector

class PostgresConnector(BaseConnector):
    def __init__(self, connection_string: str, table_name: str):
        """
        Initialize the PostgreSQL Connector using a connection string.
        :param connection_string: PostgreSQL connection URI.
        :param table_name: Name of the PostgreSQL table.
        """
        self.connection_string = connection_string
        self.table_name = table_name
        self.connection = None
        try:
            self.connection = psycopg2.connect(self.connection_string)
            self.connection.autocommit = True
            print('Connection successful')
        except OperationalError as e:
            print("Failed to connect to PostgreSQL:", e)
        atexit.register(self.close)

        
    def close(self):
        """
        Close the database connection.
        """
        if self.connection:
            self.connection.close()
            print("Database connection closed.")


    def flush(self, json_data: list) -> bool:
        if not self.connection:
            print("Database connection is not established.")
            return False

        if not json_data:
            print("No data to insert.")
            return False

        tasks = [Task(**item) for item in json_data]

        conn = self.connection
        try:
            cur = conn.cursor()
            insert_query = """
            INSERT INTO logs (log_id, function_name, start_time, end_time, args, result, task_id, agent_id, parent_log_id, metadata, inferred_accuracy, accuracy_reasoning)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cur.executemany(insert_query, [(task.log_id, task.function_name, task.start_time, task.end_time, 
                                            json.dumps(task.args), json.dumps(task.result), task.task_id, 
                                            task.agent_id, task.parent_log_id, json.dumps(task.metadata), 
                                            task.inferred_accuracy, task.accuracy_reasoning) for task in tasks])
            conn.commit()
            cur.close()
            return True
        except Exception as e:
            print(f"Error inserting data: {e}")
            return False
