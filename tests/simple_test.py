import json
from extensilog import ExtensiLog
# from extensilogger.extensilogger import ExtensiLogger

# Clear the event_log.json file
with open('event_log.json', 'w') as file:
    file.write('[]')

logger: ExtensiLog = ExtensiLog()

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
    with open('event_log.json', 'r') as file:
        log_data = json.load(file)
        task_ids = [entry['task_id'] for entry in log_data if 'task_id' in entry]
        print(f"Total log entries: {len(log_data)}")
        print(f"Total unique task_ids: {len(set(task_ids))}")
        assert len(log_data) == 3, "The length of event_log.json should be 3"
        assert len(set(task_ids)) == 2, "There should be 2 unique task_ids"

        print('Simple test passed!')
