import curses
import sys
import time
import json
import re
import os
from typing import Any, Dict, Hashable, List, Tuple

page = 1
config = []
containers = {}
advanced_mode = False

volumes = []
output_container_lines = []

def init(screen):
    # Create the curses enviornment
    screen = curses.initscr()
    height, width = screen.getmaxyx()
    global page
    
    curses.noecho()
    curses.curs_set(0)
    curses.cbreak()
    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
    screen.attron(curses.color_pair(2))

    welcome = "WELCOME TO SDR DOCKER CONFIG"
    help_string = "This utility will walk you through setting up containers that will recieve, display, and feed ADSB data."
    help_string_next = "As well as containers that can receive and/or display ACARS/VDLM and airband VHF communications"
    status_bar = "Press 'n' to Proceed | Press 'q' or Control + C to exit"

    clear_screen(screen)

    # show text

    screen.addstr(int(height // 2 - 3),int((width // 2) - (len(welcome) // 2) - len(welcome) % 2),welcome)
    screen.addstr(int(height // 2),int((width // 2) - (len(help_string) // 2) - len(help_string) % 2),help_string)
    screen.addstr(int(height // 2 + 1),int((width // 2) - (len(help_string_next) // 2) - len(help_string_next) % 2), help_string_next)

    # show status bar

    screen.attron(curses.color_pair(3))
    screen.addstr(height-1, 0, status_bar)
    screen.addstr(height-1, len(status_bar), " " * (width - len(status_bar) - 1))
    screen.attroff(curses.color_pair(3))

    k = ""
    while True:
        k = screen.getch()

        if k == ord('q'):
            exit_app()
        elif k == ord('n'):
            page = 2
            return
    screen.refresh()

def show_containers(screen):
    global page
    global containers
    curs_x = 1
    curs_y = 2

    height, width = screen.getmaxyx()

    clear_screen(screen)
    curses.noecho()
    curses.cbreak()
    curses.curs_set(1)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
    screen.attron(curses.color_pair(2))
    prompt = "Please select the container(s) you wish to install"
    status_bar = "Press Space to (de)select a container | Up and Down Arrows to Navigate | Press 'n' to Proceed | 'p' for Previous Page | Press 'q' or Control + C to exit"
    selected_containers = list()

    screen.addstr(0, 0, prompt)
    index = 2
    for container in containers:
        screen.addstr(index, 0, "[ ] " + container)
        index += 1
    
    # show status bar

    screen.attron(curses.color_pair(3))
    screen.addstr(height-1, 0, status_bar)
    screen.addstr(height-1, len(status_bar), " " * (width - len(status_bar) - 1))
    screen.attroff(curses.color_pair(3))

    screen.move(curs_y, curs_x)

    while True:
        k = screen.getch()

        if k == ord('q'):
            exit_app()
        elif k == ord('n'):
            page = 3
            for container in containers:
                if containers[container]['index'] in selected_containers:
                    containers[container]['selected'] = True
            return
        elif k == ord('p'):
            page = 1
            return
        if k == curses.KEY_DOWN:
            curs_y = curs_y + 1
        elif k == curses.KEY_UP:
            curs_y = curs_y - 1
        elif k == ord(' '):
            if (curs_y - 1) in selected_containers:
                selected_containers.remove(curs_y - 1)
            else:
                selected_containers.append(curs_y - 1)
        
        if curs_y > len(containers) + 1:
            curs_y = len(containers) + 1
        elif curs_y < 2:
            curs_y = 2
        
        index = 2

        for container in containers:
            if containers[container]['index'] not in selected_containers:
                screen.addstr(index, 0, "[ ] " + container)
            else:
                screen.addstr(index, 0, "[X] " + container)
            index += 1
        screen.move(curs_y, curs_x)
        screen.refresh()

def exit_app():
    curses.nocbreak()
    curses.echo()
    curses.endwin()
    sys.exit(0)

def clear_screen(screen):
    screen.clear()
    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
    screen.bkgd(' ', curses.color_pair(2))
    screen.refresh()

def config_container(screen):
    global page
    global containers
    global advanced_mode

    height, width = screen.getmaxyx()

    clear_screen(screen)
    curses.noecho()
    curses.cbreak()
    curses.curs_set(1)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
    screen.attron(curses.color_pair(2))
    status_bar = "Press enter to save option and proceed | Control - P to go to the previous option"

    # show status bar

    screen.attron(curses.color_pair(3))
    screen.addstr(height-1, 0, status_bar)
    screen.addstr(height-1, len(status_bar), " " * (width - len(status_bar) - 1))
    screen.attroff(curses.color_pair(3))

    for container in containers:
        item = containers[container]
        if 'selected' in item and item['selected'] == True:
            screen.addstr(0, 0, item['container_display_name'])
            container_config = item['container_config']
            env_settings = {}
            for section, section_values in container_config.items():
                if len(re.findall(r"^section_\d+", section)):
                    
                    if 'user_description' in section_values:
                        pass
                        screen.addstr(2, 0, " " * (width - 1))
                        screen.addstr(2, 0, section_values['user_description'])

                    for options, option_values in section_values.items():
                        if len(re.findall(r"^option_\d+", options)) == 1:
                            if ('disable_user_set' not in option_values or option_values['disable_user_set'] == False):
                                for i in range (1, height - 1):  # clear all the old lines out, just in case
                                    screen.addstr(i, 0, " " * (width - 1))
                                screen.addstr(3, 0, f"Container Variable: {option_values['display_name']}")
                                screen.addstr(4, 0, f"Container Variable: {option_values['user_description']}")
                                if 'user_required_description' in option_values:
                                    screen.addstr(5, 0, f"Required Formatting: {option_values['user_required_description']}")
                                screen.addstr(7, 0, "Make your selection below")
                                if 'variable_type' not in option_values or option_values['variable_type'] == "string":
                                    pass
                                    while True:
                                         k = screen.getch()
                                         screen.refresh()
                                elif option_values['variable_type'] == 'boolean':
                                    exit = False
                                    if 'default_value' not in option_values or option_values['default_value'] == True:
                                        selection = 0
                                    else:
                                        selection = 1
                                    
                                    curses.curs_set(0)
                                    k = ""
                                    while not exit:
                                        if k == curses.KEY_UP:
                                            selection -= 1
                                            if selection < 0:
                                                selection = 1
                                        elif k == curses.KEY_DOWN:
                                            selection += 1
                                            if selection > 1:
                                                selection = 0                                            
                                        elif k == curses.KEY_ENTER or k == 10 or k == ord("\r"):
                                            if selection == 0:
                                                exit = True
                                                if option_values['default_value'] == False or option_values['compose_required'] == True:                                                
                                                    if 'boolean_override_true' in option_values:
                                                        env_settings[option_values['env_name']] = option_values['boolean_override_true']
                                                    else:
                                                        env_settings[option_values['env_name']] = True
                                            elif selection == 1:
                                                exit = True
                                                if option_values['default_value'] == True or option_values['compose_required'] == True:
                                                    if 'boolean_override_false' in option_values:
                                                        env_settings[option_values['env_name']] = option_values['boolean_override_false']
                                                    else:
                                                        env_settings[option_values['env_name']] = False
                                        if not exit:
                                            if selection == 0:
                                                screen.attron(curses.A_REVERSE)
                                                screen.addstr(8, 0, "YES")
                                                screen.attroff(curses.A_REVERSE)
                                                screen.addstr(9, 0, "NO")
                                            else:
                                                screen.addstr(8, 0, "YES")
                                                screen.attron(curses.A_REVERSE)
                                                screen.addstr(9, 0, "NO")
                                                screen.attroff(curses.A_REVERSE)
                                            screen.refresh()
                                            k = screen.getch()

                        #     screen.addstr(3, 0, f"Container Variable: {option_values[options]['display_name']}")
                #print(env_settings)
    
    page = 4

def raise_on_duplicate_keys(ordered_pairs: List[Tuple[Hashable, Any]]) -> Dict:
    """Raise ValueError if a duplicate key exists in provided ordered list of pairs, otherwise return a dict."""
    dict_out = {}
    for key, val in ordered_pairs:
        if key in dict_out:
            raise ValueError(f'Duplicate key: {key}')
        else:
            dict_out[key] = val
    return dict_out

def get_containers():
    global config
    global containers
    index = 1
    for key, item in config.items():
        if len(re.findall(r"^container_\d+", key)):
            item['index'] = index
            index += 1
            containers[item['container_display_name']] = item


if __name__ == "__main__":
    json_file = "documentation/sample-config.json"
    
    try:
        config = json.load(open(json_file), object_pairs_hook=raise_on_duplicate_keys)
        get_containers()
        while True:
            if page == 1:
                curses.wrapper(init)
            elif page == 2:
                curses.wrapper(show_containers)
            elif page == 3:
                curses.wrapper(config_container)
            else:
                exit_app()

    except KeyboardInterrupt as e:
        print("KI", e)
        exit_app()
    except Exception as e:
        print("E", e)
        print(advanced_mode)
        exit_app()

