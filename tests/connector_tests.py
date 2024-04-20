
import time
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from extensilog import MongoConnector

uri = "mongodb+srv://parth:px0rSVKRxZZZOFV6@cluster0.7vx269u.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Create a new client and connect to the server
connector = MongoConnector(uri, db_name='Test', collection_name='Logger')


def main():
    # Insert a JSON document into the collection
    connector.flush([{
        'task_id': '123',
        'user_id': '123',
        'timestamp': '{}'.format(time.time())
    }])

if __name__ == '__main__':
    main()