import json
import psycopg2
from psycopg2 import OperationalError, DatabaseError

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
    

    def __del__(self):
        """
        Destructor method to ensure the connection is closed when the object is deleted.
        """
        self.close()

        
    def close(self):
        """
        Close the database connection.
        """
        if self.connection:
            self.connection.close()
            print("Database connection closed.")


    def flush(self, json_data: list):
        if not self.connection:
            print("Database connection is not established.")
            return False

        if not json_data:
            print("No data to insert.")
            return False

        try:
            cursor = self.connection.cursor()
            # Transforming JSON data into tuples for insertion
            columns = json_data[0].keys()
            values = [tuple(item[column] for column in columns) for item in json_data]
            query = f"INSERT INTO {self.table_name} ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(columns))})"
            cursor.executemany(query, values)
            self.connection.commit()  # Commit changes
            cursor.close()
            print("Data inserted successfully.")
            return True
        except DatabaseError as e:
            print("An error occurred while inserting batch data:", e)
            return False
        except Exception as e:
            print("Unexpected error during batch insertion:", e)
            return False

