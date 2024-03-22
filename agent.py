import base64
import json
import re
import traceback
import time
from io import BytesIO
from functools import partial
from agent_logger import logger
from openai import OpenAI
from globot import Globot


USE_VISION = False
FORCE_RUN = True
IMG_RES = 768
MAX_RETRIES = 3

client = OpenAI()

def _fake_func(name, **kwargs):
    return name, kwargs

FUNCTIONS = {
    'go_back': {
        'args_str': '()',
        'func': partial(_fake_func, 'go_back'),
    },
    'scroll_up': {
        'args_str': '()',
        'func': partial(_fake_func, 'scroll', direction='up'),
    },
    'scroll_down': {
        'args_str': '()',
        'func': partial(_fake_func, 'scroll', direction='down'),
    },
    'click': {
        'args_str': '(id: int)',
        'args_ex': '(id=...)',
        'func': partial(_fake_func, 'click'),
    },
    'type': {
        'args_str': '(id: int, text: str, submit: bool)',
        'args_ex': '(id=..., text=..., submit=...)',
        'func': partial(_fake_func, 'type'),
    },
    'set_objective_complete': {
        'args_str': '()',
        'func': partial(_fake_func, 'set_objective_complete'),
    },
}

@logger.log_openai_call('choose_action')
def choose_action(objective, messages, img, inputs, clickables):
    if USE_VISION:
        W, H = img.size
        img = img.resize((IMG_RES, int(IMG_RES* H/W)))
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    # Wrap each element in a <node> tag with an id and clickable/inputable attributes
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

    output_format = """\
## Reflection
1. Did you your last action get your closer to your objective? If this is your first action, just put "N/A".
2. Why or why not? If this is your first action, just put "N/A".

## Plan
1. What is your new plan based on your reflection?
2. What will your first step be given the current HTML? Which node will you interact with? What function will you call?

## Code
Call ONE of the following functions:
"""
    for k, v in FUNCTIONS.items():
        args_ex = v.get('args_ex', v['args_str'])
        output_format += f"```python\n{k}{args_ex}\n```\nOR\n"
    output_format = output_format[:-3]  # remove last OR

    if len(messages) == 0:
        system_message = {
            'role': 'system',
            'content': (
                f'Your objective is: "{objective}"\n'
                "You are given a browser where you can either go back a page, scroll up/down, click, or type into <node> elements on the page.\n"
                "If you believe you have accomplished your objective, call the set_objective_complete() function to finish your task.\n"
                "You can only click on nodes with clickable=True, or type into nodes with inputable=True.\n"
                "You can only call one function at a time, and always output a single one-line code block\n"
                "Output in the following format:\n" + output_format + "\n"
                "Do not repeat the questions in the output, only the headings and numbers."
            )
        }
        messages.append(system_message)
    
    user_prompt = (
        f'Here are nodes that you can click on and/or type into:\n\n{html_description}\n\n'
        'Answer the reflection questions, then call one of the available functions. The available functions are:\n\n' +
        "\n".join(f"{k}{v['args_str']}" for k, v in FUNCTIONS.items()) + '\n\n'
        'Note the when using the type() function, you must also specify whether to submit the form after typing (i.e. pressing enter).'
    )

    user_message = {
        'role': 'user',
        'content': user_prompt if not USE_VISION else [
            {'type': 'text', 'text': 'This is an image of the browser.'},
            {'type': 'image_url', 'image_url': f'data:image/png;base64,{img_base64}'},
            {'type': 'text', 'text': user_prompt},
        ]
    }
    messages.append(user_message)

    response1 = client.chat.completions.create(
            model="gpt-4-vision-preview" if USE_VISION else "gpt-4-1106-preview",
            messages=messages,
            temperature=0.0,
            max_tokens=500
        )

    retries = 0
    kwargs = {}
    while retries < MAX_RETRIES:
        response = client.chat.completions.create(
            model="gpt-4-vision-preview" if USE_VISION else "gpt-4-1106-preview",
            messages=messages,
            temperature=0.0,
            max_tokens=500
        )

        response_message = response.choices[0].message.content
        messages.append({'role': 'assistant', 'content': response_message})
        
        try:
            code = re.findall(r'```(?:python)?\n(.*?)\n```', response_message, re.DOTALL)
            if len(code) == 0:
                raise Exception('No code blocks found, please include a code block in your response')

            # Code gen > function calling
            func, kwargs = eval(code[-1], {k: v['func'] for k, v in FUNCTIONS.items()})

            # Validation, failed validation gets caught and sent to chatgpt to retry
            _id = kwargs.get('id', None)
            if func is None:                                raise Exception('No function called')
            if func in ['click', 'type'] and _id is None:   raise ValueError('No id specified')
            if func == 'click' and _id not in clickables:   raise IndexError(f'click() called but id {_id} is not clickable')
            if func == 'type' and _id not in inputs:        raise IndexError(f'type() called but id {_id} is not inputable')
            if func == 'type' and len(kwargs) != 3:         raise ValueError(f'Function type() expected 3 arguments, got {len(kwargs)}')
            break

        except Exception as e:
            print('Got error, feeding back to chatgpt:\n', e)
            error_message = traceback.format_exc()
            messages.append({'role': 'user', 'content': f"{e}\n\nI got an error running your code. Here is the full error message:\n{error_message}\nCan you fix the error and try again?"})
            retries += 1

    if retries >= MAX_RETRIES:
        raise Exception('Max retries exceeded!')

    return func, kwargs
    

def main(force_run=False):
    objective = "reaearch about pi.com and write a short sentence about them" # input("What is your objective?\n> ")
    
    bot = Globot()
    bot.go_to_page('https://www.google.com/')

    messages = []
    while True:
        try:
            img, inputs, clickables = bot.crawl()
            func, args = choose_action(objective, messages, img, inputs, clickables)
        except Exception as e:
            print(e)
            traceback.print_exc()
            print('Error crawling page, retrying...')
            # Likely page not fully loaded, wait and try again
            time.sleep(2)
            continue

        if   func == 'type':                    action = f"Type {' and submit' if args['submit'] else ''}'{args['text']}' into:\n{inputs[args['id']]}\n"
        elif func == 'click':                   action = f"Click:\n{clickables[args['id']]}\n"
        elif func == 'scroll':                  action = f'Scroll {args["direction"]}\n'
        elif func == 'go_back':                 action = 'Go back\n'
        elif func == 'set_objective_complete':  action = 'Objective complete!!'

        command = 'y' if force_run else input("Run command? (Y/n):").lower()
        if command == "y" or command == "":
            if   func == 'type':                    bot.type(inputs[args['id']], args['text'], args['submit'])
            elif func == 'click':                   bot.click(clickables[args['id']])
            elif func == 'scroll':                  bot.scroll(args['direction'])
            elif func == 'go_back':                 bot.go_back()
            elif func == 'set_objective_complete':  exit(0)
            continue    
    
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

        command = input(
            "\nChoose a command:\n"
            "(g) go to url\n(b) go back\n(u) scroll up\n(d) scroll down\n(c) click\n(t) type\n" +
            "(h) view help again\n(o) change objective\n\n> "
        )
        if   command == "g":  bot.go_to_page(input("URL:"))
        elif command == "b":  bot.go_back()
        elif command == "u":  bot.scroll("up")
        elif command == "d":  bot.scroll("down")
        elif command == "c":  bot.click(clickables[int(input("id:"))])
        elif command == "t":  bot.type(inputs[int(input("id:"))], input("text:"), submit=True)
        elif command == "o":  objective = input("Objective:")


if __name__ == '__main__':
    force_run = FORCE_RUN
    try:
        main(force_run=force_run)
    except KeyboardInterrupt:
        print("\n[!] Ctrl+C detected, exiting gracefully.")
        exit(0)