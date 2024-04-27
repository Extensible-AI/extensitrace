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
        if self.connection:
            try:
                cursor = self.connection.cursor()
                # Prepare data for batch insertion
                if not json_data:
                    print("No data to insert.")
                    return False

                columns = json_data[0].keys()
                query = f"INSERT INTO {self.table_name} ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(columns))})"
                cursor.executemany(query, json_data)
                self.connection.commit()  # Ensure changes are committed if autocommit is not enabled
                cursor.close()
                return True
            except DatabaseError as e:
                print("An error occurred while inserting batch data:", e)
            except Exception as e:
                print("Unexpected error during batch insertion:", e)
        else:
            print("Database connection is not established.")
            return False

