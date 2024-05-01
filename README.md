# Extensilog 
## Key Features
### Python Package for Agent Workflow Tracking

ExtensiLogger is designed to facilitate comprehensive logging and tracking within agent-based systems or workflows. It provides a structured way to log events, data, and metrics, making it easier to monitor and analyze the behavior of agents in various environments.

### Usage 

The package can be easily installed using pip. Navigate to the extensilog directory and install using the following commands:

#### Install from PyPI
`pip install extensilog`

#### Incorporating in code

```python
from extensilog import MongoConnector

client = OpenAI() # Optional to pass in
connector = MongoConnector(...) # Optional connector, defaults to local
el: Extensilog = Extensilog(connector=connector)

el.log(track=True)
def top_level_func():
    lower_level_func()
    
el.log()
def lower_level_func():
    pass
```
