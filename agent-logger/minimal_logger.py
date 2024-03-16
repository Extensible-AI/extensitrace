# minimal_logger.py
import inspect
import functools
import json
from datetime import datetime

class MinimalLogger:
    def __init__(self):
        self.event_queue = []

    def log_openai_call(self, func_name: str):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = datetime.now().isoformat()
                result = func(*args, **kwargs)
                end_time = datetime.now().isoformat()

                func_args = inspect.signature(func).bind(*args, **kwargs).arguments
                func_args_str = ', '.join(f'{k}={v!r}' for k, v in func_args.items())

                log_entry = {
                    'function_name': func_name,
                    'start_time': start_time,
                    'end_time': end_time,
                    'args': func_args_str,
                    'result': result
                }

                self.event_queue.append(json.dumps(log_entry))
                print("Queue content", self.event_queue[-1] if len(self.event_queue) else None)

                return result
            return wrapper
        return decorator

logger = MinimalLogger()