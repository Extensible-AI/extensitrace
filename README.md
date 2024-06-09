# ExtensiTrace
### Python Package for Agent Workflow Tracking

ExtensiTrace allows for a simple way to track all agent actions including python functions and all openai tool calls. 

### Install from PyPI
`pip install extensitrace`

### Usage 

```python
from extensitrace import ExtensiTrace

client = OpenAI() # Optional to pass in
connector = MongoConnector(...) # Optional connector, defaults to local
# Logger writes to a jsonl file locally by default 
et: ExtensiTrace = ExtensiTrace(connector=connector) # See constructor in extensitrace/extensitrace.py for more info

# Need track=True for top level
et.log(track=True)
def top_level_func():
    lower_level_func()
    
et.log()
def lower_level_func():
    pass
```

### Notes to keep in mind
- Tracks one openai call per function
- Streaming openai calls not captured - the tracer is meant for tracking tool calls 
- Support for Openai only right now
- The client objects should be the same across files if it is being passed in manually
- Singleton class, however instantiation methods across files must match, recommend creating and importing from a file (see example below)
- If this is very useful to you and want to use it in prod I'm happy to write an async interface for log dumps


### Recommended Setup

`tracer.py`
```python
from extensitrace import ExtensiTrace

et: ExtensiTrace = ExtensiTrace(connector=connector) 

```

`main.py`
```python
from tracer import et
```