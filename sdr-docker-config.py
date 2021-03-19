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
output_container_config = {}

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
    print("output: ", output_container_config)
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
    status_bar = "Press enter to save option and proceed | Use arrow keys to navigate between options"

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
                        screen.addstr(2, 0, " " * (width - 1))
                        screen.addstr(2, 0, section_values['user_description'])

                    run_section = False
                    loops = 0

                    if 'run_if' in section_values and ('loops' not in section_values or (('loops' in section_values and 'min_loops' in section_values['loops'] and section_values['loops']['min_loops'] == 0)) or (('loops' in section_values and 'min_loops' not in section_values['loops']))):
                        run_section =  do_run_section(screen=screen, user_question=section_values['run_if']['user_question'], height=height, width=width)
                    elif 'depends_on' in section_values:
                        run_section = True  ## TODO: ADD IN LOGIC CHECK
                    else:
                        run_section = True

                    while run_section:
                        loops += 1
                        for options, option_values in section_values.items():
                            if len(re.findall(r"^group_\d+", options)) == 1:
                                result = handle_groups(screen, option_values, options, height, width)
                                if option_values['env_name'] in env_settings:
                                   env_settings[option_values['env_name']] =  option_values['field_combine'].join((env_settings[option_values['env_name']], result))
                                else:
                                    env_settings[option_values['env_name']] = result
                            elif len(re.findall(r"^option_\d+", options)) == 1:
                                if 'disable_user_set' in option_values and option_values['disable_user_set'] == True:
                                    if 'compose_required' in option_values and option_values['compose_required'] == True:
                                        if 'variable_type' not in option_values or option_values['variable_type'] == "string":
                                            env_settings[option_values['env_name']] = option_values['default_value']
                                        elif option_values['variable_type'] == 'boolean':
                                            env_settings[option_values['env_name']] = option_values['default_value']
                                elif ('disable_user_set' not in option_values or option_values['disable_user_set'] == False):
                                    for i in range (1, height - 1):  # clear all the old lines out, just in case
                                        screen.addstr(i, 0, " " * (width - 1))
                                    screen.addstr(3, 0, f"Container Variable: {option_values['display_name']}")
                                    screen.addstr(4, 0, f"Container Variable: {option_values['user_description']}")
                                    if 'user_required_description' in option_values:
                                        screen.addstr(5, 0, f"Required Formatting: {option_values['user_required_description']}")
                                    
                                    if 'variable_type' not in option_values or option_values['variable_type'] == "string":
                                        response = handle_string(screen, option_values, options, height, width)

                                        if ('user_required' in option_values and response != option_values['default_value']) or 'user_required' not in option_values:
                                            if (response != option_values['default_value']) or ('compose_required' in option_values and option_values['compose_required'] == True):
                                                env_settings[option_values['env_name']] = response

                                    elif option_values['variable_type'] == 'boolean':
                                        response = handle_boolean(screen, option_values, options)

                                        if response:
                                            if option_values['default_value'] == False or option_values['compose_required'] == True:                                                
                                                if 'boolean_override_true' in option_values:
                                                    env_settings[option_values['env_name']] = option_values['boolean_override_true']
                                                else:
                                                    env_settings[option_values['env_name']] = "True"
                                        else:
                                            if option_values['default_value'] == True or option_values['compose_required'] == True:
                                                if 'boolean_override_false' in option_values:
                                                    env_settings[option_values['env_name']] = option_values['boolean_override_false']
                                                else:
                                                    env_settings[option_values['env_name']] = "False"
                            #     screen.addstr(3, 0, f"Container Variable: {option_values[options]['display_name']}")

                        if 'run_if' in section_values:
                            # first, lets make sure the loop actually ran if required
                            did_run_check = False
                            
                            if 'loops' in section_values:
                                if 'min_loops' in section_values['loops'] and loops < section_values['loops']['min_loops']:
                                    for i in range (1, height - 1):  # clear all the old lines out, just in case
                                        screen.addstr(i, 0, " " * (width - 1))
                                    did_run_check = True
                                    screen.addstr(3, 0, "This section needs to be ran at least once. Please select yes on the next screen")
                                    run_section =  do_run_section(screen=screen, user_question=section_values['run_if']['user_question'], first=True, height=height, width=width)
                                elif 'max_loops' in section_values['loops'] and section_values['loops']['max_loops'] >= loops:
                                    did_run_check = True
                                    run_section = False                                    

                            if not did_run_check and 'user_question_after' not in section_values['run_if']:
                                run_section =  do_run_section(screen=screen, user_question=section_values['run_if']['user_question'], first=False, height=height, width=width)
                            elif not did_run_check:
                                run_section = do_run_section(screen=screen, user_question=section_values['run_if']['user_question'], user_question_after=section_values['run_if']['user_question_after'], first=False, height=height, width=width)
                        else:
                            run_section = False
            output_container_config[item['container_name']] = env_settings
    page = 4

def handle_groups(screen, option_values, option, height, width):
    result = ""
    separator = option_values['field_combine']

    for key, group in option_values.items():
        if re.findall(r"^option_\d+", key):
            if 'disable_user_set' in group and group['disable_user_set'] == True:
                if 'compose_required' in group and group['compose_required'] == True:
                    result =  separator.join((result, group['default_value']))
            else:
                for i in range (1, height - 1):  # clear all the old lines out, just in case
                    screen.addstr(i, 0, " " * (width - 1))
                screen.addstr(3, 0, f"Container Variable: {group['display_name']}")
                screen.addstr(4, 0, f"Container Variable: {group['user_description']}")
                if result == "":
                    result = handle_string(screen, group, key, height, width)
                else:
                    result = separator.join((result, handle_string(screen, group, key, height, width)))
        elif re.findall(r"^group_\d", key):
            if result == "":
                    result = handle_groups(screen, group, key, height, width)
            else:
                result = separator.join((result, handle_groups(screen, group, key, height, width)))
    return result

def handle_string(screen, option_values, options, height, width):
    curses.curs_set(1)
    curs_x = 0
    curs_y = height - 2
    screen.addstr(7, 0, "Input your answer below")
    variable_string = ""
    if "default_value" in option_values:
        variable_string = option_values['default_value']
        curs_x = len(variable_string)
    exit = False
    
    screen.addstr(curs_y, 0, variable_string)
    screen.move(curs_y, curs_x)
    while not exit:
        k = screen.getch()
        if k == curses.KEY_LEFT:
            curs_x -= 1
            if curs_x < 0:
                curs_x = 0
        elif k == curses.KEY_RIGHT:
            curs_x += 1
            if curs_x > width:
                curs_x = width
        elif k == 127:
            variable_string = variable_string[:curs_x - 1] + variable_string[curs_x + 1:]
            curs_x -= 1
            if curs_x < 0:
                curs_x = 0
        elif k == curses.KEY_DC:
            variable_string = variable_string[:curs_x] + variable_string[curs_x + 1:]
        elif k >= 32 and k <= 126:
            variable_string = variable_string[:curs_x] + chr(k) + variable_string[curs_x:]
            curs_x += 1
            if curs_x > width:
                curs_x = width
        elif k == curses.KEY_ENTER or k == 10 or k == ord("\r"):
            if ('user_required' in option_values and variable_string != option_values['default_value']) or 'user_required' not in option_values:
                return variable_string

                exit = True
            else:
                screen.addstr(curs_y - 1, 0, "Please input a value")
        if not exit:    
            screen.addstr(curs_y, 0, " " * (width - 1))
            screen.addstr(curs_y, 0, variable_string)
            screen.move(curs_y, curs_x)
            screen.refresh()

def handle_boolean(screen, option_values, options):
    exit = False
    curses.noecho()
    screen.addstr(7, 0, "Make your selection below")
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
                return True
            elif selection == 1:
                return False
                exit = True
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
def do_run_section(screen, user_question, user_question_after=None, first=True, height=0, width=0):
    for i in range (1, height - 1):  # clear all the old lines out, just in case
        screen.addstr(i, 0, " " * (width - 1))

    if first or user_question_after is None:
        screen.addstr(3, 0, f"{user_question}")
    else:
        screen.addstr(3, 0, f"{user_question_after}")

    selection = 0
    exit = False
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
            return not bool(selection)
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

