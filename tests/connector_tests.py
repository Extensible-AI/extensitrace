import datetime
from uuid import uuid4
from extensilog import MongoConnector, PostgresConnector


mg_uri = "mongodb+srv://parth:px0rSVKRxZZZOFV6@cluster0.7vx269u.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

pg_uri = "postgresql://postgres:3Xtensible123@test.clqqi8meshib.us-east-1.rds.amazonaws.com:5432/postgres"
date_time = datetime.datetime.now().timestamp()
uuid = uuid4()

def mongo_flush():
    mg_connector = MongoConnector(mg_uri, db_name='Test', collection_name='Logger')
    # Insert a JSON document into the collection
    mg_connector.flush([{
        "log_id": str(uuid), 
        "function_name": "openai.chat.completions.create",
        "start_time": 1713562166.677055,
        "end_time": date_time,
        "args": {},
        "result": {},
        "task_id": "db6bddf5-c8ca-437f-bc42-fe7b29e4293b",
        "agent_id": "64c11754-2f65-453a-9796-9560acc464f0",
        "parent_log_id": None
    }])

def postgres_flush():
    pg_connector = PostgresConnector(connection_string=pg_uri, table_name='logs')
    pg_connector.flush([{
        "log_id": str(uuid), 
        "function_name": "openai.chat.completions.create",
        "start_time": 1713562166.677055,
        "end_time": date_time,
        "args": {},
        "result": {},
        "task_id": "db6bddf5-c8ca-437f-bc42-fe7b29e4293b",
        "agent_id": "64c11754-2f65-453a-9796-9560acc464f0",
        "parent_log_id": None
    }])

if __name__ == '__main__':
    postgres_flush()