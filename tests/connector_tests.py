import datetime
import json
from uuid import uuid4
from extensilog import MongoConnector, PostgresConnector



date_time = datetime.datetime.now().timestamp()
uuid = uuid4()


data = []
with open('data.jsonl', 'r') as file:
    for line in file:
        data.append(json.loads(line))

    
def mongo_flush(data):
    mg_connector = MongoConnector(mg_uri, db_name='Test', collection_name='Logger')
    mg_connector.flush(data)

def postgres_flush(data):
    pg_connector = PostgresConnector(connection_string=pg_uri, table_name='logs')
    pg_connector.flush(data)


if __name__ == '__main__':
    postgres_flush(data)