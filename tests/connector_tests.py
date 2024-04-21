from extensilog import MongoConnector, PostgresConnector

mg_uri = "mongodb+srv://parth:px0rSVKRxZZZOFV6@cluster0.7vx269u.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
pg_uri = "postgresql://postgres:3Xtensible123@test.clqqi8meshib.us-east-1.rds.amazonaws.com:5432/postgres"

# Create a new client and connect to the server
mg_connector = MongoConnector(mg_uri, db_name='Test', collection_name='Logger')
pg_connector = PostgresConnector(connection_string=pg_uri, table_name='logs')

def mongo_flush():
    # Insert a JSON document into the collection
    mg_connector.flush([{
        "log_id": "ac8cb691-842c-477b-9522-d619a9bad30e",
        "function_name": "openai.chat.completions.create",
        "start_time": 1713562166.677055,
        "end_time": 1713562167.452621,
        "args": {},
        "result": {},
        "task_id": "db6bddf5-c8ca-437f-bc42-fe7b29e4293b",
        "agent_id": "64c11754-2f65-453a-9796-9560acc464f0",
        "parent_log_id": None
    }])

def postgres_flush():
    pg_connector.flush([{
        "log_id": "ac8cb691-842c-477b-9522-d619a9bad30e",
        "function_name": "openai.chat.completions.create",
        "start_time": 1713562166.677055,
        "end_time": 1713562167.452621,
        "args": {},
        "result": {},
        "task_id": "db6bddf5-c8ca-437f-bc42-fe7b29e4293b",
        "agent_id": "64c11754-2f65-453a-9796-9560acc464f0",
        "parent_log_id": None
    }])

if __name__ == '__main__':
    postgres_flush()