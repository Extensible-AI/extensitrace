import json
from openai.types.chat import ChatCompletion 

def replace_data_in_viewer(file_name, content):
    start_index = -1
    end_index = -1
    with open(file_name, 'r+', encoding='utf-8') as file:
        html_content = file.readlines()
        for i, line in enumerate(html_content):
            if '// DATA STARTS HERE' in line:
                start_index = i + 1
            if '// DATA ENDS HERE' in line:
                end_index = i
        if start_index != -1 and end_index != -1:
            html_content[start_index:end_index] = [content]
        else:
            print("Could not find data markers in the HTML file.")
            return
        
        file.seek(0)
        file.truncate()
        file.writelines(html_content)

def update_log_viewer(json_content):
    json_str = json.dumps(json_content)
    json_str = json_str.replace('true', 'true').replace('false', 'false').replace('null', "'None'")
    new_js_line = f'const data = {json_str};\n'
    replace_data_in_viewer('collapsed_log_viewer.html', new_js_line)
    replace_data_in_viewer('graph_log_viewer.html', new_js_line)
    replace_data_in_viewer('flame_log_viewer.html', new_js_line)

if __name__ == '__main__':
    with open('event_log.json') as events:
        update_log_viewer(json.loads(events.read()))