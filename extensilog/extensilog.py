import contextlib
import inspect
import functools
import json
from datetime import datetime
from queue import Queue
import threading
import uuid
import openai
import atexit

from .connectors.local_connector import LocalConnector
from .singleton import Singleton


thread_local_storage = threading.local()

class Extensilog(metaclass=Singleton):
    def __init__(self, client=None, log_file='./event_log.json', connector=None, task_flush_limit=1):
        self.client = client or openai
        self.log_file = log_file
        self.lock = threading.Lock()
        self.agent_id = str(uuid.uuid4())
        self.data_store = dict() 
        self.connector = connector or LocalConnector(log_file)
        self.task_flush_limit = task_flush_limit
        self.task_flush_ids = Queue() 
        self.task_count = 0
        self.to_flush = []
        atexit.register(self.__on_exit)


    def __on_exit(self):
        """
        Method to ensure all remaining logs are flushed upon program interruption or shutdown.
        """
        with self.lock:
            while not self.task_flush_ids.empty():
                task_id = self.task_flush_ids.get()
                self.__add_to_flush(task_id)
            self.__flush_queue()
            self.task_count = 0
            self.data_store = dict()  # Optionally reset the data store if needed
            print("Program interrupted. All pending logs have been flushed.")


    def log(self, track=False):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if track and hasattr(thread_local_storage, 'task_id') and len(self.data_store[thread_local_storage.task_id]['call_stack']) > 0:
                    raise ValueError("Cannot track a top level function that is already part of a task.")
                if not hasattr(thread_local_storage, 'task_id') or track:
                    thread_local_storage.task_id = str(uuid.uuid4())
                    with self.lock:
                        self.task_flush_ids.put(thread_local_storage.task_id)
                        self.task_count += 1
                        self.data_store[thread_local_storage.task_id] = {
                            'queue': Queue(),
                            'client': self.client,
                            'call_stack': [],
                            'patched': False,
                            'completion_ids': set(),
                            'last_openai_call': {},
                            'metadata': None
                        }

                with self.lock:
                    self.data_store[thread_local_storage.task_id]['call_stack'].append((func.__name__, str(uuid.uuid4())))


                func_args = inspect.signature(func).bind(*args, **kwargs).arguments
                func_args_dict = self.__serialize_arguments(func_args)
                start_time = datetime.now().timestamp()

                with self.__patched_create_method():
                    result = func(*args, **kwargs)

                end_time = datetime.now().timestamp()
                with self.lock:
                    log = self.data_store[thread_local_storage.task_id]['call_stack'].pop()

                    self.__log_event(
                        log_id=log[1],
                        function_name=func.__name__,
                        start_time=start_time,
                        end_time=end_time,
                        args=func_args_dict,
                        result={'result_string':result} if isinstance(result, str) else result,
                        task_id=thread_local_storage.task_id,
                        agent_id=self.agent_id,
                        parent_log_id=self.data_store[thread_local_storage.task_id]['call_stack'][-1][1] if self.data_store[thread_local_storage.task_id]['call_stack'] else None,
                        metadata=self.data_store[thread_local_storage.task_id]['metadata'],
                        inferred_accuracy=None,
                        accuracy_reasoning=None
                    )

                return result
            return wrapper
        return decorator

    
    def add_metadata(self, metadata: dict):
        with self.lock:
            if self.data_store[thread_local_storage.task_id]['metadata']:
                metadata = {**metadata, **self.data_store[thread_local_storage.task_id]['metadata']}
            else:
                self.data_store[thread_local_storage.task_id]['metadata'] = metadata
        return metadata


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
            result = original_create(*args, **kwargs)  
            chat_call_end_time = datetime.now().timestamp()

            with self.lock:
                self.__log_event(
                    log_id=str(uuid.uuid4()),
                    function_name='openai.chat.completions.create',
                    start_time=chat_call_start_time,
                    end_time=chat_call_end_time,
                    args=chat_args_dict,
                    result=result.model_dump(),
                    task_id=getattr(thread_local_storage, 'task_id', str(uuid.uuid4())),
                    agent_id=self.agent_id,
                    parent_log_id=self.data_store[thread_local_storage.task_id]['call_stack'][-1][1] if self.data_store[thread_local_storage.task_id]['call_stack'] else None,
                    metadata=self.data_store[thread_local_storage.task_id]['metadata'],
                    inferred_accuracy=None,
                    accuracy_reasoning=None
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
            yield  # If already patched, yield without re-patching


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
            openai_id = log_entry['result']['id']
            self.data_store[task_id]['last_openai_call'][openai_id] = log_entry['log_id'] 

        self.data_store[task_id]['queue'].put(log_entry)

        if len(self.data_store[task_id]['call_stack']) == 0 and self.task_count >= self.task_flush_limit:
            # TODO: to be made non-blocking
            removed = 0
            while removed < self.task_flush_limit: 
                task_id = self.task_flush_ids.get()
                removed += 1
                self.__add_to_flush(task_id)
            self.task_count -= self.task_flush_limit
            self.__flush_queue()


    # TODO: add batch flushing with storing in memory
    def __add_to_flush(self, task_id):
        while not self.data_store[task_id]['queue'].empty():
            log_entry = self.data_store[task_id]['queue'].get()
            # Skip the loop if the log id is not the last openai call
            if log_entry['function_name'] == 'openai.chat.completions.create' and self.data_store[task_id]['last_openai_call'][log_entry['result']['id']] != log_entry['log_id']:
                continue
            self.to_flush.append(log_entry)

    
    def __flush_queue(self):
        if self.to_flush:
            self.connector.flush(self.to_flush)
            self.to_flush.clear()
