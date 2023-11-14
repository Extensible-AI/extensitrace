import io
import sys
import time
import json
from PIL import Image
from playwright.sync_api import sync_playwright

# See Globot.__init__ function
from fake_useragent import UserAgent

VOID_ELEMENTS = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
READABLE_ATTRIBUTES = {'title', 'alt', 'href', 'placeholder', 'label', 'value', 'caption', 'summary', 'aria-label', 'aria-describedby', 'datetime', 'download', 'selected', 'checked', 'type'}

UNCLICKABLE_ELEMENTS = {'html', 'head', 'body'}
CLICKABLE_ELEMENTS = {'a', 'button', 'img', 'details', 'summary'}

INPUT_ELEMENTS = {'input', 'textarea', 'select', 'option'}


class DOMNode:
    def __init__(self, i, nodes, strings):
        self._on_screen = None
        self.parent = None
        self.children = []
        self.llm_id = None
        ### Only some nodes have these, default None to differentiate between None and False
        self.bounds = None
        self.center = None
        self.inputValue = None
        self.inputChecked = None
        self.isClickable = None
        self.optionSelected = None
        ###
        self.parentId = nodes['parentIndex'][i] if nodes['parentIndex'][i] >= 0 else None
        self.nodeType = strings[nodes['nodeType'][i]]
        self.nodeName = strings[nodes['nodeName'][i]].lower()
        self.nodeValue = strings[nodes['nodeValue'][i]].strip() if nodes['nodeValue'][i] >= 0 else None
        self.backendNodeId = nodes['backendNodeId'][i]

        self.attributes = {}
        attrs = nodes['attributes'][i]
        for att1, att2 in zip(attrs[::2], attrs[1::2]):
            self.attributes[strings[att1]] = strings[att2][:100] # cut off long URLs

        self.readable_attributes = {k: v for k, v in self.attributes.items() if k in READABLE_ATTRIBUTES}

    def __repr__(self, indent=0):
        if self.nodeName == '#text':
            return ' ' * indent + (self.nodeValue or '')

        attr_str = " ".join([f'{k}="{v}"' for k, v in self.readable_attributes.items()])
        attr_str = " " + attr_str if attr_str else ""
        open_tag = f'<{self.nodeName}{attr_str}>'
        close_tag = f'</{self.nodeName}>'

        if len(self.children) == 0:
            return (' ' * indent + open_tag) + (close_tag if self.nodeName not in VOID_ELEMENTS else '')

        # special case for elements with only one text child -> one-line element
        if len(self.children) == 1 and self.children[0].nodeName == '#text':
            return (' ' * indent + open_tag) + self.children[0].__repr__() + close_tag

        children_repr = '\n'.join([child.__repr__(indent + 2) for child in self.children])
        return (' ' * indent + open_tag) + '\n' + children_repr + '\n' + (' ' * indent + close_tag)

    def on_screen(self, screen_bounds):
        if len(self.children) > 0:
            return any([child.on_screen(screen_bounds) for child in self.children])

        if self.bounds is None or len(self.bounds) != 4 or self.bounds[2]*self.bounds[3] == 0:
            return False
        
        x, y, w, h = self.bounds
        win_upper_bound, win_left_bound, win_width, win_height = screen_bounds
        win_right_bound = win_left_bound + win_width
        win_lower_bound = win_upper_bound + win_height
        return x < win_right_bound and x + w > win_left_bound and y < win_lower_bound and y + h > win_upper_bound


class Globot:
    def __init__(self, headless=False):
        playwright = sync_playwright().start()
        self.browser = playwright.chromium.launch(headless=headless)
        
        # Remove HiDPI if on a low resolution screen
        device = playwright.devices['Desktop Chrome HiDPI']
        # Uncomment if you start getting blocked
        device['user_agent'] = UserAgent().random
        self.context = self.browser.new_context(**device, locale="en-US")

        # Some websites require cookies to be set
        self.context.add_cookies([
            {"name": "cookie_name", "value": "cookie_value", "domain": "example.com", "path": "/", "expires": int(time.time()) + 3600}
        ])
        self.page = self.context.new_page()

    def go_to_page(self, url):
        self.page.goto(url=url if "://" in url else "https://" + url, timeout=10000)
        self.client = self.page.context.new_cdp_session(self.page)

    def go_back(self):
        self.page.go_back()
        
    def scroll(self, direction):
        if direction == "up":
            self.page.mouse.wheel(delta_x=0, delta_y=-900)
        elif direction == "down":
            self.page.mouse.wheel(delta_x=0, delta_y=900)

    def click(self, node: DOMNode):
        # Inject javascript into the page which removes the target= attribute from all links
        js = """
        links = document.getElementsByTagName("a");
        for (var i = 0; i < links.length; i++) {
            links[i].removeAttribute("target");
        }
        """
        self.page.evaluate(js) 
        assert node.center is not None, "Cannot click on node with no bounds"
        self.page.mouse.click(*node.center)

    def type(self, node: DOMNode, text, submit=False):
        if not node.inputChecked:
            self.page.mouse.dblclick(*node.center)
        self.page.keyboard.type(text)
        if submit:
            self.page.keyboard.press("Enter")

    def crawl(self):
        self.page.wait_for_load_state("load")
        self.page.wait_for_load_state("networkidle")
        time.sleep(1)
        print("\nPage loaded!\n")

        screenshot = Image.open(io.BytesIO(self.page.screenshot())).convert("RGB")

        dom = self.client.send(
            "DOMSnapshot.captureSnapshot",
            {"computedStyles": [], "includeDOMRects": True, "includePaintOrder": True},
        )
        with open("dom.json", "w") as f:
            f.write(json.dumps(dom, indent=4))

        dom_strings = dom['strings']
        document = dom['documents'][0]
        dom_layout = document['layout']
        dom_nodes = document['nodes']
        
        screen_bounds =  dom_layout['bounds'][0]
        # For some reason `window.devicePixelRatio` this gives the wrong answer sometimes
        device_pixel_ratio = screen_bounds[2] / self.page.evaluate("window.screen.width")

        nodes = []
        root = None

        # Takes much longer naively
        nodeIndex_flipped = {v: k for k, v in enumerate(dom_layout['nodeIndex'])}
        inputValue_flipped = {v: k for k, v in enumerate(dom_nodes['inputValue']['index'])}
        for i in range(len(dom_nodes['parentIndex'])):
            node = DOMNode(i, dom_nodes, dom_strings)
            if i == 0:
                root = node

            if i in nodeIndex_flipped:
                bounds = dom_layout['bounds'][nodeIndex_flipped[i]]
                bounds = [int(b / device_pixel_ratio) for b in bounds]
                node.bounds = bounds
                node.center = (int(bounds[0] + bounds[2]/2), int(bounds[1] + bounds[3]/2))

            if i in dom_nodes['isClickable']['index']:
                node.isClickable = True

            if i in inputValue_flipped:
                v = dom_nodes['inputValue']['value'][inputValue_flipped[i]]
                node.inputValue = dom_strings[v] if v >= 0 else ''
                # node.string_attributes['value'] = node.inputValue

            if i in dom_nodes['inputChecked']['index']:
                node.inputChecked = True
                # TODO: set checked attribute in <input> tags

            if i in dom_nodes['optionSelected']['index']:
                node.optionSelected = True
                # TODO: set selected attribute in <option> tags

            nodes.append(node)

        # Switch node ids to node pointers
        for node in nodes:
            if node.parentId is not None:
                node.parent = nodes[node.parentId]
                node.parent.children.append(node)

        count = 0
        input_elements = {}
        clickable_elements = {}
        def find_interactive_elements(node):
            nonlocal count
            clickable = node.nodeName in CLICKABLE_ELEMENTS and node.isClickable and node.center is not None

            inputable = node.nodeName in INPUT_ELEMENTS or node.inputValue is not None

            visible = node.on_screen(root.bounds) and 'visibility: hidden' not in node.attributes.get('style', '')

            if visible and (clickable or inputable):
                if clickable:
                    clickable_elements[count] = node
                if inputable:
                    input_elements[count] = node
                node.llm_id = count
                count += 1
        
            for child in node.children:
                find_interactive_elements(child)
        
        find_interactive_elements(root)

        return screenshot, input_elements, clickable_elements
