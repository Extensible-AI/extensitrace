import json
import os
import time
from extensilog import ExtensiLog
from threading import Thread
import logging

logger: ExtensiLog = ExtensiLog(log_file='extensilog.jsonl')

def log_generator(index):
    @logger.log(track=True)
    def test():
        logger.add_metadata({'key': f'value_{index}'})
        test2()
        pass

    @logger.log()
    def test2():
        pass

    @logger.log(track=True)
    def test3():
        pass

    test()
    test3()


def log_generator_python_log(index):
    # Configure the Python logger
    logging.basicConfig(filename='benchmark.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    def test():
        # Log with metadata
        logging.info(f'Test function start with index {index}')
        test2()

    def test2():
        # Simple log statement
        logging.debug('Test2 function executed')

    def test3():
        # Log with metadata indicating function start
        logging.info(f'Test3 function start with index {index}')

    test()
    test3()


def run_stress_test_extensilog():
    threads = []
    for i in range(1000):
        t = Thread(target=log_generator, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

def run_stress_test_python():
    threads = []
    for i in range(1000):
        t = Thread(target=log_generator_python_log, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

if __name__ == '__main__':
    try:
        os.remove('benchmark.log')
    except FileNotFoundError:
        pass
    try:
        os.remove('extensilog.jsonl')
    except FileNotFoundError:
        pass
    start_time = time.time()
    run_stress_test_extensilog()
    end_time = time.time()
    print(f"Time taken for 1000 extenislog logs: {end_time - start_time} seconds")

    start_time = time.time()
    run_stress_test_python()
    end_time = time.time()
    print(f"Time taken for 1000 python logs: {end_time - start_time} seconds")

