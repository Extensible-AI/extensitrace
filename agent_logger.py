import inspect
import functools
import json
from datetime import datetime
from queue import Queue
import threading
import uuid
import openai

class AgentLogger:
    def __init__(self, flush_interval=1, log_file='event_log.json'):
        self.event_queue = Queue()
        self.flush_interval = flush_interval
        self.counter = 0
        self.lock = threading.Lock()
        self.log_file = log_file
        self.agent_id = str(uuid.uuid4())
        self.run_id = None

    def log(self):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = datetime.now().isoformat()
                
                # Capture the original function's arguments
                func_args = inspect.signature(func).bind(*args, **kwargs).arguments
                func_args_dict = {k: self.__serialize_value(v) for k, v in func_args.items()}

                # Log the call to openai.chat.completions.create if it happens
                original_create = openai.chat.completions.create
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
                        result=result.model_dump()
                    )
                    return result

                openai.chat.completions.create = mock_create
                
                try:
                    result = func(*args, **kwargs)
                finally:
                    # Ensure the original method is restored
                    openai.chat.completions.create = original_create

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
        self.event_queue.put(log_entry)
        with self.lock:
            self.counter += 1
            if self.counter >= self.flush_interval:
                self.__flush_queue()
                self.counter = 0

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

        # This set will track the client_msg_ids of 'openai.chat.completions.create' function calls
        client_msg_ids = set(
            entry.get('args', {}).get('event_data', {}).get('client_msg_id')
            for entry in existing_data
            if entry.get('function_name') == 'openai.chat.completions.create'
        )

        new_data = []
        while not self.event_queue.empty():
            log_entry = self.event_queue.get()
            # Check if the log entry is for an OpenAI API call
            if log_entry.get('function_name') == 'openai.chat.completions.create':
                client_msg_id = log_entry.get('args', {}).get('event_data', {}).get('client_msg_id')
                # Add the log entry if it's not a duplicate
                if client_msg_id not in client_msg_ids:
                    new_data.append(log_entry)
                    client_msg_ids.add(client_msg_id)
            else:
                # For all other function calls, add the entry directly
                new_data.append(log_entry)

        # Sort the new data based on 'start_time' before combining
        sorted_new_data = sorted(new_data, key=lambda x: x['start_time'], reverse=True)
        combined_data = existing_data + sorted_new_data

        try:
            # Write the updated log data back to the file
            with open(self.log_file, 'w') as f:
                json.dump(combined_data, f, indent=2)
        except Exception as e:
            print(f'Error writing to file: {e}')


logger = AgentLogger(flush_interval=1)
