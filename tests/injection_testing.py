from extensitrace import ExtensiTrace
import json
import os

logger: ExtensiTrace = ExtensiTrace(log_file='extensitrace.jsonl', agent_id='agent_1')

@logger.log(track=True, task_id='task_1')
def entry():
    second()

@logger.log()
def second():
    pass

if __name__ == '__main__':

    if os.path.exists('extensitrace.jsonl'):
        os.remove('extensitrace.jsonl')

    entry()

    with open('extensitrace.jsonl', 'r') as file:
        log_data = [json.loads(line) for line in file]
        task_ids = [entry['task_id'] for entry in log_data if 'task_id' in entry]
        agent_ids = [entry['agent_id'] for entry in log_data if 'agent_id' in entry]

    given_task_id = 'task_1'
    given_agent_id = 'agent_1'

    if not all(task_id == given_task_id for task_id in task_ids):
        raise ValueError(f"One or more task_ids do not match the given task_id '{given_task_id}'")

    if not all(agent_id == given_agent_id for agent_id in agent_ids):
        raise ValueError(f"One or more agent_ids do not match the given agent_id '{given_agent_id}'")
    