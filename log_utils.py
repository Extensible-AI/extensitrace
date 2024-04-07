import json


def update_log_viewer(json_content):
    html_file_path = 'log_viewer.html'
    # Read the current HTML content
    with open(html_file_path, 'r', encoding='utf-8') as file:
        html_content = file.readlines()
    # Convert True and False to lowercase and None to 'None'
    json_str = json.dumps(json_content)
    json_str = json_str.replace('true', 'true').replace('false', 'false').replace('null', "'None'")
    # Prepare the new JavaScript line with the updated JSON data
    new_js_line = f'const data = {json_str};\n'
    # Find the start and end index for the existing JavaScript block
    start_index = -1
    end_index = -1
    for i, line in enumerate(html_content):
        if '// DATA STARTS HERE' in line:
            start_index = i + 1 # Include the next line after the comment
        if '// DATA ENDS HERE' in line:
            end_index = i # Include the line before the comment
    # Ensure we found the markers before trying to replace the content
    if start_index != -1 and end_index != -1:
        # Replace the existing JavaScript block with the new JSON data
        html_content[start_index:end_index] = [new_js_line]
    else:
        print("Could not find data markers in the HTML file.")
        return
    # Write the updated HTML content back to the file
    with open(html_file_path, 'w', encoding='utf-8') as file:
        file.writelines(html_content)
