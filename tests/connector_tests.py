import datetime
import json
from uuid import uuid4
from extensilog import MongoConnector, PostgresConnector


mg_uri = "mongodb+srv://parth:px0rSVKRxZZZOFV6@cluster0.7vx269u.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

pg_uri = "postgresql://postgres:3Xtensible123@test.clqqi8meshib.us-east-1.rds.amazonaws.com:5432/postgres"
date_time = datetime.datetime.now().timestamp()
uuid = uuid4()


with open('data.json', 'r') as file:
    data = json.load(file)

    
def mongo_flush(data):
    mg_connector = MongoConnector(mg_uri, db_name='Test', collection_name='Logger')
    mg_connector.flush(data)

def postgres_flush(data):
    pg_connector = PostgresConnector(connection_string=pg_uri, table_name='logs')
    pg_connector.flush(data)


if __name__ == '__main__':
    postgres_flush(data)