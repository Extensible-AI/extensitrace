import inspect
import functools
import json
from datetime import datetime
from queue import Queue
import threading
import openai

class AgentLogger:
    def __init__(self, flush_interval=10):
        self.event_queue = Queue()
        self.flush_interval = flush_interval
        self.counter = 0
        self.lock = threading.Lock()

    def log_openai_call(self):
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
                    function_name=func_name,
                    start_time=start_time,
                    end_time=end_time,
                    args=func_args_dict,
                    result=result
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
        events = []
        while not self.event_queue.empty():
            events.append(self.event_queue.get())
        if events:
            with open('event_log.json', 'a') as f:
                json.dump(events, f, indent=2)
                f.write('\n')

logger = AgentLogger(flush_interval=1)
