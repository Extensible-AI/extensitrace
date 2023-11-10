import base64
from io import BytesIO
import json
import re
import sys
import traceback
import time

from openai import OpenAI
from globot import Globot


USE_VISION = True
IMG_RES = 768
MAX_RETRIES = 3


def choose_action(objective, messages, img, inputs, clickables, use_vision=True):
    if use_vision:
        W, H = img.size
        img = img.resize((IMG_RES, int(IMG_RES* H/W)))
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    s = ""
    for i in inputs.keys() | clickables.keys():
        inputable = False
        clickable = False
        if i in inputs:
            node = inputs[i]
            inputable = True
        if i in clickables:
            node = clickables[i]
            clickable = True

        s += f"<node id={i} clickable={clickable} inputable={inputable}>\n"
        s += node.__repr__(indent=2)
        s += "\n</node>\n"
    html_description = s

    # log for debug
    with open('html_description.txt', 'w') as f:
        f.write(html_description)

    client = OpenAI()
    available_functions = """\
go_back()
scroll_up()
scroll_down()
click(id: int)
type(id: int, text: str, submit: bool)\
"""

    output_format = """\
## Reflection
1. Did you your last action get your closer to your objective?
2. Why or why not?

## Plan
1. What is your new plan based on your reflection?
2. What will your first step be given the current HTML? Which node will you interact with? What function will you call?

## Code
Call ONE of the following functions:
```python
go_back()
```
OR
```python
scroll_up()
```
OR
```python
scroll_down()
```
OR
```python
click(id=...)
```
OR
```python
type(id=..., text=..., submit=...)
```"""

    if len(messages) == 0:
        system_message = {
            'role': 'system',
            'content': (
                f'Your objective is: "{objective}"\n'
                "You are given a browser where you can either go back a page, scroll up/down, click, or type into <node> elements on the page.\n"
                "Pay attention to your action history to no repeat your mistakes!\n"
                "You can only click on nodes with clickable=True, or type into nodes with inputable=True.\n"
                "You can only call one function at a time, choose between go_back(), scroll_up(), scroll_down(), click() and type() and output a single one-line code block\n"
                "Output in the following format:\n" + output_format
            )
        }
        messages.append(system_message)
    
    user_prompt = (
        f'Here are nodes that you can click on and/or type into:\n\n{html_description}\n\n'
        'Chose one node to click on or type into by its id and call the appropriate function.'
        'The available functions are:\n\n' + available_functions + '\n\n'
        'Note the when using the type() function, you must also specify whether to submit the form after typing (i.e. pressing enter).'
    )

    user_message = {
        'role': 'user',
        'content': user_prompt if not use_vision else [
            {'type': 'text', 'text': 'This is an image of the browser.'},
            {'type': 'image_url', 'image_url': f'data:image/png;base64,{img_base64}'},
            {'type': 'text', 'text': user_prompt},
        ]
    }
    messages.append(user_message)

    retries = 0
    result = None
    while retries < MAX_RETRIES:
        response = client.chat.completions.create(
            model="gpt-4-vision-preview" if use_vision else "gpt-4-1106-preview",
            messages=messages,
            temperature=0.0,
            max_tokens=500,
            stream=True
        )

        response_message = ""
        for chunk in response:
            delta = chunk.choices[0].delta.content
            if not delta:
                continue
            response_message += delta
            print(delta, end='', flush=True)
        messages.append({'role': 'assistant', 'content': response_message})

        with open('messages.txt', 'w') as f:
            json.dump(messages, f, indent=4)

        # Code psyop
        func = None
        _id = None
        _text = None
        _submit = None
        _scroll_dir = None
        def type_fn(id, text, submit):
            nonlocal func, _id, _text, _submit
            func = 'TYPE'
            _id = id
            _text = text
            _submit = submit

        def click_fn(id):
            nonlocal func, _id
            func = 'CLICK'
            _id = id
        
        def go_back_fn():
            nonlocal func
            func = 'GO_BACK'

        def scroll_up_fn():
            nonlocal func, _scroll_dir
            func = 'SCROLL'
            _scroll_dir = 'up'

        def scroll_down_fn():
            nonlocal func, _scroll_dir
            func = 'SCROLL'
            _scroll_dir = 'down'
        
        try:
            code = re.findall(r'```(?:python)?\n(.*?)\n```', response_message, re.DOTALL)
            if len(code) == 0:
                raise Exception('No code blocks found, please include a code block in your response')

            # Code gen > function calling
            exec(code[-1], {'click': click_fn, 'type': type_fn, 'go_back': go_back_fn, 'scroll_up': scroll_up_fn, 'scroll_down': scroll_down_fn})

            # Validation, failed validation gets caught and sent to chatgpt to retry
            if func is None:
                raise Exception('No function called')
            if _id is None and func in ['CLICK', 'TYPE']:
                raise ValueError('No id specified')
            if _id is not None and _id not in inputs and _id not in clickables:
                raise IndexError('id not found in inputs or clickables, please choose a valid id from the provided HTML')
            if func == 'CLICK' and _id not in clickables:
                raise IndexError(f'click() called but id {_id} is not clickable')
            if func == 'TYPE' and _id not in inputs:
                raise IndexError(f'type() called but id {_id} is not inputable')
            if func == 'TYPE' and (_text is None or _submit is None):
                raise ValueError('type() called but text and/or submit not specified')
            
            if func == 'CLICK':
                result = (func, (_id,))
            elif func == 'TYPE':
                result = (func, (_id, _text, _submit))
            elif func == 'SCROLL':
                result = (func, (_scroll_dir,))
            else:
                result = (func, ())
            break

        except Exception as e:
            error_message = traceback.format_exc()
            messages.append({'role': 'user', 'content': f"{e}\n\nI got an error running your code. Here is the full error message:\n{error_message}\nCan you fix the error and try again?"})
            retries += 1

    if retries >= MAX_RETRIES:
        raise Exception('Max retries exceeded!')

    return result
    

def main(force_run=False):
    objective = input("What is your objective?\n> ")
    
    bot = Globot()
    bot.go_to_page('https://www.google.com/')

    messages = []
    while True:
        try:
            img, inputs, clickables = bot.crawl()
            func, args = choose_action(objective, messages, img, inputs, clickables, use_vision=USE_VISION)
        except Exception as e:
            print(e)
            traceback.print_exc()
            print('Error crawling page, retrying...')
            # Likely page not fully loaded, wait and try again
            time.sleep(2)
            continue

        print('\nGPT Command:')
        if func == 'CLICK':
            node_id = args[0]
            action = 'Click:\n' + str(clickables[node_id]) + '\n'
        elif func == 'TYPE':
            node_id, text, submit = args
            if submit:
                action = f'Type and submit "{text}" into:\n' + str(inputs[node_id]) + '\n'
            else:
                action = f'Type "{text}" into:\n' + str(inputs[node_id]) + '\n'
        elif func == 'SCROLL':
            action = f'Scroll {args[0]}\n'
        else:
            action = 'Go back\n'
        
        print(action)

        command = 'y' if force_run else input("Run command? (Y/n):").lower()
        if command == "y" or command == "":
            if func == 'CLICK':
                bot.click(clickables[node_id])
            elif func == 'TYPE':
                bot.type(inputs[node_id], text, submit)
            elif func == 'SCROLL':
                bot.scroll(args[0])
            else:
                bot.go_back()
        elif command == "g":
            url = input("URL:")
            bot.go_to_page(url)
        elif command == "b":
            bot.go_back()
        elif command == "u":
            bot.scroll("up")
        elif command == "d":
            bot.scroll("down")
        elif command == "c":
            id = int(input("id:"))
            bot.click(clickables[id])
        elif command == "t":
            id = int(input("id:"))
            text = input("text:")
            bot.type(clickables[id], text, submit)
        elif command == "o":
            objective = input("Objective:")
        else:
            print(
                "(g) to visit url\n(u) scroll up\n(d) scroll down\n(c) to click\n(t) to type\n" +
                "(h) to view commands again\n(r/enter) to run suggested command\n(o) change objective"
            )


if __name__ == '__main__':
    force_run = len(sys.argv) > 1 and 'y' in sys.argv[1]
    try:
        main(force_run=force_run)
    except KeyboardInterrupt:
        print("\n[!] Ctrl+C detected, exiting gracefully.")
        exit(0)