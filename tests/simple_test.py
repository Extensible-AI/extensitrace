import json
from extensilog import Extensilog 

with open('event_log.jsonl', 'w') as file:
    file.write('')


logger: Extensilog = Extensilog(log_file='event_log.jsonl')

@logger.log(track=True)
def test():
    logger.add_metadata({'key': 'value'})
    test2()
    pass

@logger.log()
def test2():
    pass

@logger.log(track=True)
def test3():
    pass

if __name__ == '__main__':
    test()
    test3()
    
    # Load event_log.json and make sure the length is one
    with open('event_log.jsonl', 'r') as file:
        log_data = [json.loads(line) for line in file]
        print(log_data)
        task_ids = [entry['task_id'] for entry in log_data if 'task_id' in entry]
        print(f"Total log entries: {len(log_data)}")
        print(f"Total unique task_ids: {len(set(task_ids))}")
        assert len(log_data) == 3, "The length of event_log.json should be 3"
        assert len(set(task_ids)) == 2, "There should be 2 unique task_ids"

        print('Simple test passed!')
