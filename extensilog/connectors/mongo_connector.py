from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
import atexit

from .base_connector import BaseConnector

class MongoConnector(BaseConnector):
    def __init__(self, connection_string: str, db_name: str, collection_name: str, client: MongoClient=None):
        """
        Initialize the MongoDB Connector using a connection string.
        :param connection_string: MongoDB connection URI.
        :param db_name: Name of the database.
        :param collection_name: Name of the collection.
        """
        self.db_name = db_name
        self.collection_name = collection_name
        self.client = client or MongoClient(connection_string, tlsAllowInvalidCertificates=True)
        try:
            # Verify server connectivity
            self.client.admin.command('ping')
        except ConnectionFailure as e:
            print("Failed to connect to MongoDB:", e)
        except OperationFailure as e:
            print("Authentication failed:", e)
        atexit.register(self.close_connection)

    def close_connection(self):
        """
        Close the MongoDB connection.
        """
        if self.client:
            self.client.close()
            print("MongoDB connection closed.")

    def flush(self, json_data):
        """
        Insert a list of JSON documents into the specified MongoDB collection.
        :param json_data: A JSON document or dict to be inserted.
        """
        try:
            db = self.client[self.db_name]
            collection = db[self.collection_name]
            collection.insert_many(json_data)
            print("Data inserted successfully.")
            return True
        except Exception as e:
            print("An error occurred while inserting data:", e)
