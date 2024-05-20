from dataclasses import dataclass


@dataclass
class Task:
    log_id: str
    function_name: str
    start_time: float 
    end_time: float 
    args: dict 
    result: dict 
    task_id: str
    agent_id: str
    parent_log_id: str
    metadata: dict 
    inferred_accuracy: float 
    accuracy_reasoning: str