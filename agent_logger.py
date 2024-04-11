import contextlib
import inspect
import functools
import json
from datetime import datetime
from queue import Queue
import threading
import uuid
import openai
from .log_utils import update_log_viewer
from .singleton import Singleton

thread_local_storage = threading.local()

class AgentLogger(metaclass=Singleton):
    def __init__(self, client=None, log_file='./event_log.json'):
        self.client = client or openai
        self.log_file = log_file
        self.event_queue = Queue()
        self.lock = threading.Lock()
        self.agent_id = str(uuid.uuid4())

    def log(self, track=False):
        print('logging!')
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not hasattr(thread_local_storage, 'task_id') or track:
                    thread_local_storage.task_id = str(uuid.uuid4())
                if not hasattr(thread_local_storage, 'call_stack'):
                    thread_local_storage.call_stack = []
                if not hasattr(thread_local_storage, 'create_count'):
                    thread_local_storage.create_count = 0

                thread_local_storage.call_stack.append(func.__name__)
                func_args = inspect.signature(func).bind(*args, **kwargs).arguments
                func_args_dict = self.__serialize_arguments(func_args)
                start_time = datetime.now().timestamp()

                with self.__patched_create_method():
                    result = func(*args, **kwargs)

                end_time = datetime.now().timestamp()
                thread_local_storage.call_stack.pop()

                self.__log_event(
                    log_id=str(uuid.uuid4()),  # Added UUID for each log
                    function_name=func.__name__,
                    start_time=start_time,
                    end_time=end_time,
                    args=func_args_dict,
                    result=result,
                    task_id=thread_local_storage.task_id,
                    agent_id=self.agent_id,
                    call_stack=" -> ".join(thread_local_storage.call_stack)
                )

                return result
            return wrapper
        return decorator


    def mock_create(self, original_create, *args, **kwargs):
        print('Mock create called')
        thread_local_storage.create_count += 1
        print(thread_local_storage.call_stack)
        chat_args_dict = self.__serialize_arguments(kwargs)
        chat_call_start_time = datetime.now().timestamp()
        result = original_create(*args, **kwargs)
        chat_call_end_time = datetime.now().timestamp()
        self.__log_event(
            log_id=str(uuid.uuid4()),  # Added UUID for each log
            function_name='openai.chat.completions.create',
            start_time=chat_call_start_time,
            end_time=chat_call_end_time,
            args=chat_args_dict,
            result=result.model_dump(),
            task_id=getattr(thread_local_storage, 'task_id', str(uuid.uuid4())),
            agent_id=self.agent_id,
            call_stack=" -> ".join(getattr(thread_local_storage, 'call_stack', []))
        )
        return result


    @contextlib.contextmanager
    def __patched_create_method(self):
        original_create = self.client.chat.completions.create
        if hasattr(thread_local_storage, 'is_patched') and thread_local_storage.is_patched:
            yield  # Skip patching if already patched
        else:
            thread_local_storage.is_patched = True
            self.client.chat.completions.create = lambda *args, **kwargs: self.mock_create(original_create, *args, **kwargs)
            try:
                yield
            finally:
                self.client.chat.completions.create = original_create
                thread_local_storage.is_patched = False
                print(f'Create count: {thread_local_storage.create_count}')


    def __serialize_arguments(self, arguments):
        return {k: self.__serialize_value(v) for k, v in arguments.items()}

    def __serialize_value(self, value):
        if isinstance(value, (str, int, float, bool, type(None))):
            return value
        elif isinstance(value, (list, tuple)):
            return [self.__serialize_value(v) for v in value]
        elif isinstance(value, dict):
            return {k: self.__serialize_value(v) for k, v in value.items()}
        else:
            return str(value)

    # def __log_event(self, **log_entry):
    #     with self.lock:
    #         self.event_queue.put(log_entry)
    #         if len(thread_local_storage.call_stack) == 0:  # Flush on top-level call completion
    #             self.__flush_queue()

    def __log_event(self, **log_entry):
        # Example modification to include full call stack in the log
        log_entry['call_stack'] = " -> ".join(getattr(thread_local_storage, 'call_stack', []))
        with self.lock:
            self.event_queue.put(log_entry)
            if len(thread_local_storage.call_stack) == 0:
                self.__flush_queue()

    def __flush_queue(self):
        existing_data = []
        try:
            with open(self.log_file, 'r') as f:
                existing_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print('Creating new log file or overwriting corrupted file.')

        new_data = []
        while not self.event_queue.empty():
            log_entry = self.event_queue.get()
            new_data.append(log_entry)

        combined_data = existing_data + new_data
        try:
            with open(self.log_file, 'w') as f:
                json.dump(combined_data, f, indent=2)
        except Exception as e:
            print(f'Error writing to file: {e}')

        update_log_viewer(combined_data)