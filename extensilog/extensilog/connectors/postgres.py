import json
import psycopg2
from psycopg2 import OperationalError, DatabaseError

from .connector import Connector

class PostgresConnector(Connector):
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

    def flush(self, json_data: list):
        if self.connection:
            try:
                cursor = self.connection.cursor()
                for data in json_data:
                    columns = data.keys()
                    values = [json.dumps(data[col]) if isinstance(data[col], dict) else data[col] for col in columns]
                    query = f"INSERT INTO {self.table_name} ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(values))})"
                    cursor.execute(query, values)
                self.connection.commit()  # Ensure changes are committed if autocommit is not enabled
                print("Data inserted successfully.")
                cursor.close()
                return True
            except DatabaseError as e:
                print("An error occurred while inserting data:", e)
            except Exception as e:
                print("Unexpected error:", e)
        else:
            print("Database connection is not established.")

    def close(self):
        """
        Close the database connection.
        """
        if self.connection:
            self.connection.close()
            print("Connection closed.")
