from collections import deque

# Replace 'log_entries' with your actual data
import json

with open('event_log.json', 'r') as file:
    log_entries = json.load(file)

# Replace 'log_entries' with your actual data

def generate_mermaid(log_entries):
    # Organize log entries by parent_id
    children = {}
    for entry in log_entries:
        parent_id = entry['parent_id']
        if parent_id not in children:
            children[parent_id] = []
        children[parent_id].append(entry)

    # Initialize a queue for breadth-first traversal and start with the root nodes (no parent_id)
    queue = deque(log_entries[i] for i in range(len(log_entries)) if log_entries[i]['parent_id'] is None)
    visited = set()  # To keep track of visited nodes

    mermaid_diagram = "graph TD\n"
    while queue:
        current_entry = queue.popleft()
        current_id = current_entry['log_id']

        # Skip if already visited to prevent cycles
        if current_id in visited:
            continue
        visited.add(current_id)

        # Get all children and add them to the queue
        for child_entry in children.get(current_id, []):
            queue.append(child_entry)
            # Create a connection in the Mermaid diagram
            mermaid_diagram += f'    {current_id}("{current_entry["function_name"]}<br>({current_id})") --> {child_entry["log_id"]}("{child_entry["function_name"]}<br>({child_entry["log_id"]})")\n'

        # Add root nodes to the Mermaid diagram
        if current_entry['parent_id'] is None:
            mermaid_diagram += f'    {current_id}("{current_entry["function_name"]}<br>({current_id})")\n'

    return mermaid_diagram

# Print the Mermaid diagram to stdout (or you could write this to a file)
print(generate_mermaid(log_entries))

# To write to a file, uncomment the following lines:
mermaid_diagram = generate_mermaid(log_entries)

with open('output.mmd', 'w') as file:
    file.write(mermaid_diagram)