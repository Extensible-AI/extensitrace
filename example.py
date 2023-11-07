import base64
from io import BytesIO
import re
import traceback
import time

from openai import OpenAI
from globot import Globot


IMG_RES = 512
MAX_RETRIES = 3


def choose_action(objective, history, img, inputs, clickables):
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
click(id: int)
type(id: int, text: str, submit: bool)\
"""

    output_format = """\
## Thoughts on image
Answer the quesions:
What do you see in the image?
What action will take you closer to accomplishing your objective?

## Thoughts on nodes
Answer the questions:
What are the corresponding nodes for the elements you want to interact with?
How will you interact with them?

## Code
```python
click(id=...)
# OR
type(id=..., text=..., submit=...)
```"""

    system_message = {
        'role': 'system',
        'content': (
            f'Your objective is: "{objective}"\n',
            "You are given a browser where you can either click, or type into <node> elements on the page.\n"
            "Pay attention to your action history to no repeat your mistakes!\n"
            #TODO: "You can also scroll up and down the page.\n",
            "You can only click on nodes with clickable=True, or type into nodes with inputable=True.\n"
            "You can only call one function at a time - choose between click() and type()\n"
            "Output in the following format:\n" + output_format
        )
    }

    user_prompt = (
        f'Here are nodes that you can click on and/or type into:\n\n{html_description}\n\n'
        'Chose one node to click on or type into by its id and call the appropriate function.'
        'The available functions are:\n\n' + available_functions + '\n\n'
        'Note the when using the type() function, you must also specify whether to submit the form after typing (i.e. pressing enter).'
    )
    if len(history) > 0:
        user_prompt += 'For reference, here is your history of actions - do not repeat your mistakes!:\n\n' + '\n\n'.join(history)

    image_prompt = {
        'role': 'user',
        'content': [
            {'type': 'text', 'text': 'This is an image of the browser.'},
            {'type': 'image_url', 'image_url': f'data:image/png;base64,{img_base64}'},
            {'type': 'text', 'text': user_prompt},
        ]
    }
    messages = [system_message, image_prompt]

    retries = 0
    result = None
    while retries < MAX_RETRIES:
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
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

        # Code psyop
        func = None
        _id = None
        _text = None
        _submit = None
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
        try:
            # Code gen > function calling
            code = re.findall(r'```(?:python)?\n(.*?)\n```', response_message, re.DOTALL)
            exec(code[0], {'click': click_fn, 'type': type_fn})

            # Validation, failed validation gets caught and sent to chatgpt to retry
            if func is None:
                raise Exception('No function called')
            if _id is None:
                raise ValueError('No id specified')
            if _id not in inputs and _id not in clickables:
                raise IndexError('id not found in inputs or clickables, please choose a valid id from the provided HTML')
            if func == 'CLICK' and _id not in clickables:
                raise IndexError(f'click() called but id {_id} is not clickable')
            if func == 'TYPE' and _id not in inputs:
                raise IndexError(f'type() called but id {_id} is not inputable')
            if func == 'TYPE' and (_text is None or _submit is None):
                raise ValueError('type() called but text and/or submit not specified')
            
            result = (func, (_id,)) if func == 'CLICK' else (func, (_id, _text, _submit))
            break

        except Exception as e:
            error_message = traceback.format_exc()
            messages.append({'role': 'user', 'content': f"{e}\n\nI got an error running your code. Here is the full error message:\n{error_message}\nCan you fix the error and try again?"})
            retries += 1

    return result
    

def main():
    objective = input("What is your objective?\n> ")
    
    bot = Globot()
    bot.go_to_page('https://www.google.com/')
    time.sleep(5)

    history = []
    while True:
        try:
            img, inputs, clickables = bot.crawl()
            func, args = choose_action(objective, history, img, inputs, clickables)
        except Exception as e:
            print(e)
            print('Error crawling page, retrying...')
            # Likely page not fully loaded, wait and try again
            time.sleep(2)
            continue

        print('GPT Command:')
        if func == 'CLICK':
            node_id = args[0]
            action = 'Click:\n' + str(clickables[node_id]) + '\n'
        else:
            node_id, text, submit = args
            if submit:
                action = f'Type and submit "{text}" into:\n' + str(inputs[node_id]) + '\n'
            else:
                action = f'Type "{text}" into:\n' + str(inputs[node_id]) + '\n'
        
        history.append('URL: ' + bot.page.url[:100]+ '\n' + action)
        print(action)

        command = input()
        if command == "r" or command == "":
            if func == 'CLICK':
                bot.click(clickables[node_id])
            else:
                bot.type(inputs[node_id], text, submit)
            time.sleep(2)
        elif command == "g":
            url = input("URL:")
            bot.go_to_page(url)
            time.sleep(2)
        elif command == "u":
            bot.scroll("up")
            time.sleep(2)
        elif command == "d":
            bot.scroll("down")
            time.sleep(2)
        elif command == "c":
            id = int(input("id:"))
            bot.click(clickables[id])
            time.sleep(2)
        elif command == "t":
            id = int(input("id:"))
            text = input("text:")
            bot.type(clickables[id], text, submit)
            time.sleep(2)
        elif command == "o":
            objective = input("Objective:")
        else:
            print(
                "(g) to visit url\n(u) scroll up\n(d) scroll down\n(c) to click\n(t) to type\n" +
                "(h) to view commands again\n(r/enter) to run suggested command\n(o) change objective"
            )


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Ctrl+C detected, exiting gracefully.")
        exit(0)