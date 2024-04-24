import contextlib
import inspect
import functools
import json
from datetime import datetime
from queue import Queue
import threading
import uuid
import openai
from .singleton import Singleton


thread_local_storage = threading.local()

class ExtensiLog(metaclass=Singleton):
    def __init__(self, client=None, log_file='./event_log.json'):
        self.client = client or openai
        self.log_file = log_file
        self.lock = threading.Lock()
        self.agent_id = str(uuid.uuid4())
        self.data_store = dict() 

    def log(self, track=False):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not hasattr(thread_local_storage, 'task_id') or track:
                    thread_local_storage.task_id = str(uuid.uuid4())
                    with self.lock:
                        self.data_store[thread_local_storage.task_id] = dict() 
                        self.data_store[thread_local_storage.task_id]['queue'] = Queue()
                        self.data_store[thread_local_storage.task_id]['client'] = self.client
                        self.data_store[thread_local_storage.task_id]['call_stack'] = []
                        self.data_store[thread_local_storage.task_id]['patched'] = False 
                        self.data_store[thread_local_storage.task_id]['completion_ids'] = set() 
                        self.data_store[thread_local_storage.task_id]['user_id'] = None 

                with self.lock:
                    self.data_store[thread_local_storage.task_id]['call_stack'].append(func.__name__)
                func_args = inspect.signature(func).bind(*args, **kwargs).arguments
                func_args_dict = self.__serialize_arguments(func_args)
                start_time = datetime.now().timestamp()

                with self.__patched_create_method():
                    result = func(*args, **kwargs)

                end_time = datetime.now().timestamp()
                with self.lock:
                    self.data_store[thread_local_storage.task_id]['call_stack'].pop()

                    self.__log_event(
                        log_id=str(uuid.uuid4()),  # Added UUID for each log
                        user_id=self.data_store[thread_local_storage.task_id]['user_id'],
                        function_name=func.__name__,
                        start_time=start_time,
                        end_time=end_time,
                        args=func_args_dict,
                        result=result,
                        task_id=thread_local_storage.task_id,
                        agent_id=self.agent_id,
                        call_stack=" -> ".join(self.data_store[thread_local_storage.task_id]['call_stack'])
                    )

                return result
            return wrapper
        return decorator


    def add_user_id(self, user_id):
        with self.lock:
            self.data_store[thread_local_storage.task_id]['user_id'] = user_id
        return user_id


    # TODO: Known bug is mock create getting called multiple times and throws extra logs
    def mock_create(self, original_create, *args, **kwargs):
        """
        A mock method to wrap around the original create method, logging additional information.
        """
        with self.lock:
            patched = self.data_store[thread_local_storage.task_id]['patched']

        if not patched: 
            chat_args_dict = self.__serialize_arguments(kwargs)
            chat_call_start_time = datetime.now().timestamp()
            result = original_create(*args, **kwargs)  # Call the original method directly
            chat_call_end_time = datetime.now().timestamp()

            with self.lock:
                self.__log_event(
                    user_id=self.data_store[thread_local_storage.task_id]['user_id'],
                    log_id=str(uuid.uuid4()),
                    function_name='openai.chat.completions.create',
                    start_time=chat_call_start_time,
                    end_time=chat_call_end_time,
                    args=chat_args_dict,
                    result=result.model_dump(),
                    task_id=getattr(thread_local_storage, 'task_id', str(uuid.uuid4())),
                    agent_id=self.agent_id,
                    call_stack=" -> ".join(self.data_store[thread_local_storage.task_id]['call_stack'])
                )
                self.data_store[thread_local_storage.task_id]['patched'] = True

            return result
        else:
            # Directly call the original method if already patched
            return original_create(*args, **kwargs)

    @contextlib.contextmanager
    def __patched_create_method(self):
        """
        A context manager to temporarily patch the create method for logging purposes.
        """
        # if not getattr(thread_local_storage, 'mock_applied', False):
        with self.lock:
            patched = self.data_store[thread_local_storage.task_id]['patched']
        
        if not patched: 
            task_id = thread_local_storage.task_id
            with self.lock:
                original_create = self.data_store[task_id]['client'].chat.completions.create

            def patched_create(*args, **kwargs):
                try:
                    return self.mock_create(original_create, *args, **kwargs)
                finally:
                    # Immediately restore the original method to avoid recursion
                    with self.lock:
                        self.data_store[task_id]['client'].chat.completions.create = original_create
                        self.data_store[thread_local_storage.task_id]['patched'] = False

            with self.lock:
                self.data_store[task_id]['client'].chat.completions.create = patched_create
            try:
                yield
            finally:
                # Ensure the original method is restored if not already done
                with self.lock:
                    if self.data_store[task_id]['client'].chat.completions.create != original_create:
                        self.data_store[task_id]['client'].chat.completions.create = original_create
                        self.data_store[thread_local_storage.task_id]['patched'] = False
        else:
            yield  # If already patched, just yield without re-patching


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


    def __log_event(self, **log_entry):
        # Example modification to include full call stack in the log
        task_id = thread_local_storage.task_id
        if log_entry['function_name'] == 'openai.chat.completions.create':
            if log_entry['result']['id'] in self.data_store[task_id]['completion_ids']:
                return
            else:
                self.data_store[task_id]['completion_ids'].add(log_entry['result']['id'])

        # log_entry['call_stack'] = " -> ".join(getattr(thread_local_storage, 'call_stack', []))
        # TODO: change the lock if needed as currently there is a lock on top level
        self.data_store[task_id]['queue'].put(log_entry)
        if len(self.data_store[task_id]['call_stack']) == 0:
            self.__flush_queue()


    def __flush_queue(self):
        existing_data = []
        try:
            with open(self.log_file, 'r') as f:
                existing_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print('Creating new log file or overwriting corrupted file.')

        new_data = []
        task_id = thread_local_storage.task_id
        while not self.data_store[task_id]['queue'].empty():
            log_entry = self.data_store[task_id]['queue'].get()
            new_data.append(log_entry)

        combined_data = existing_data + new_data
        try:
            with open(self.log_file, 'w') as f:
                json.dump(combined_data, f, indent=2)
        except Exception as e:
            print(f'Error writing to file: {e}')
