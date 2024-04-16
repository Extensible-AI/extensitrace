import json
# from extensilogger import ExtensiLogger
from extensilogger.extensilogger import ExtensiLogger

# Clear the event_log.json file
with open('event_log.json', 'w') as file:
    file.write('[]')

logger = ExtensiLogger()

@logger.log()
def test():
    pass

if __name__ == '__main__':
    test()
    
    # Load event_log.json and make sure the length is one
    with open('event_log.json', 'r') as file:
        log_data = json.load(file)
        assert len(log_data) == 1, "The length of event_log.json should be 1"
        print('Simple test passed!')