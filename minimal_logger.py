import inspect
import functools
import json
from datetime import datetime
from queue import Queue
import threading

class AgentLogger:
    def __init__(self, flush_interval=10):
        self.event_queue = Queue()
        self.flush_interval = flush_interval
        self.counter = 0
        self.lock = threading.Lock()

    def log_openai_call(self, func_name: str):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = datetime.now().isoformat()
                result = func(*args, **kwargs)
                end_time = datetime.now().isoformat()
                func_args = inspect.signature(func).bind(*args, **kwargs).arguments
                func_args_dict = {k: self.serialize_value(v) for k, v in func_args.items()}
                log_entry = {
                    'function_name': func_name,
                    'start_time': start_time,
                    'end_time': end_time,
                    'args': func_args_dict,
                    'result': result
                }
                self.event_queue.put(log_entry)
                with self.lock:
                    self.counter += 1
                    if self.counter >= self.flush_interval:
                        self.flush_queue()
                        self.counter = 0
                return result
            return wrapper
        return decorator
    
    def serialize_value(self, value):
        if isinstance(value, (str, int, float, bool, type(None))):
            return value
        elif isinstance(value, (list, tuple)):
            return [self.serialize_value(v) for v in value]
        elif isinstance(value, dict):
            return {k: self.serialize_value(v) for k, v in value.items()}
        else:
            return str(value)

    def flush_queue(self):
        events = []
        while not self.event_queue.empty():
            events.append(self.event_queue.get())
        if events:
            with open('event_log.json', 'a') as f:
                json.dump(events, f, indent=2)
                f.write('\n')

logger = AgentLogger(flush_interval=1)