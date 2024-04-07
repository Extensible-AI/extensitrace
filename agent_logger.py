import inspect
import functools
import json
from datetime import datetime
from queue import Queue
import threading
import uuid
import openai

from log_library.log_utils import update_log_viewer
from log_library.singleton import Singleton

class AgentLogger(metaclass=Singleton):
    def __init__(self, client=None, log_file='./event_log.json'):
        self.client = client or openai
        self.log_file = log_file
        self.event_queue = Queue()
        self.lock = threading.Lock()
        self.agent_id = str(uuid.uuid4())
        self.current_task_id = None
        self.prev_task_id = None

    def log(self, track=False):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if track:
                    self.current_task_id = str(uuid.uuid4())
                
                func_args = inspect.signature(func).bind(*args, **kwargs).arguments
                func_args_dict = {k: self.__serialize_value(v) for k, v in func_args.items()}

                original_create = self.client.chat.completions.create

                start_time = datetime.now().isoformat()

                def mock_create(*args, **kwargs):
                    chat_call_start_time = datetime.now().isoformat()
                    chat_args_dict = {k: self.__serialize_value(v) for k, v in kwargs.items()}
                    result = original_create(*args, **kwargs)
                    chat_call_end_time = datetime.now().isoformat()
                    self.__log_event(
                        function_name='openai.chat.completions.create',
                        start_time=chat_call_start_time,
                        end_time=chat_call_end_time,
                        args=chat_args_dict,
                        result=result.model_dump(),
                        agent_id=self.agent_id
                    )
                    return result
                
                self.client.chat.completions.create = mock_create
                
                try:
                    result = func(*args, **kwargs)
                finally:
                    self.client.chat.completions.create = original_create

                end_time = datetime.now().isoformat()
                
                self.__log_event(
                    function_name=func.__name__,
                    start_time=start_time,
                    end_time=end_time,
                    args=func_args_dict,
                    result=result,
                    agent_id=self.agent_id
                )

                return result
            return wrapper
        return decorator
    
    def __serialize_value(self, value):
        if isinstance(value, (str, int, float, bool, type(None))):
            return value
        elif isinstance(value, (list, tuple)):
            return [self.__serialize_value(v) for v in value]
        elif isinstance(value, dict):
            return {k: self.__serialize_value(v) for k, v in value.items()}
        else:
            return str(value)

    def __log_event(self, **log_entry):
        log_entry['task_id'] = self.current_task_id if self.current_task_id else str(uuid.uuid4())

        if self.prev_task_id != self.current_task_id:
            with self.lock:
                self.__flush_queue()  # Flush the queue if the task ID has changed
            self.prev_task_id = self.current_task_id

        self.event_queue.put(log_entry)

    def __flush_queue(self):
        existing_data = []
        try:
            # Attempt to read the existing log file
            with open(self.log_file, 'r') as f:
                existing_data = json.load(f)
        except FileNotFoundError:
            print('File not found. A new file will be created.')
        except json.JSONDecodeError:
            print('JSON decode error in the existing file. Starting fresh.')

        new_data = []
        seen_ids = set()
        while not self.event_queue.empty():
            log_entry = self.event_queue.get() 

            # Check if id is in result, if True, it is an openai call, if error or false, its not
            try:
                openai_call_id = log_entry.get('result', {}).get('id')
            except:
                openai_call_id = False
            
            # Dedupe logs
            if openai_call_id and openai_call_id not in seen_ids:
                seen_ids.add(openai_call_id)
                new_data.append(log_entry)
            elif not openai_call_id:
                new_data.append(log_entry)

        combined_data = existing_data + new_data

        try:
            # Write the updated log data back to the file
            with open(self.log_file, 'w') as f:
                json.dump(combined_data, f, indent=2)
        except Exception as e:
            print(f'Error writing to file: {e}')

        update_log_viewer(combined_data)