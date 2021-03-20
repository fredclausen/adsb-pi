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
advanced = False

volumes = False
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
            page = 4
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
    k = ""
    selected_containers = list()
    while True:
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
            if (curs_y - 2) in selected_containers:
                selected_containers.remove(curs_y - 2)
            else:
                selected_containers.append(curs_y - 2)
                
                # see if there are any containers we need to suggest
                required_containers = []
                required_containers_index = []
                recommended_containers = []
                recommended_containers_index = []
                selected_container_name = ""
                for container in containers:
                    if containers[container]['index'] == curs_y - 2:
                        selected_container_name = containers[container]['container_display_name']
                        if 'recommends' in containers[container]:
                            for key, item in containers[container]['recommends'].items():
                                recommended_containers.append(item)
                        if 'requires' in containers[container]:
                            for key, item in containers[container]['requires'].items():
                                required_containers.append(item)
                        continue
                
                if len(required_containers):
                    output = f"The container {selected_container_name} requires the installation of"
                    show = False
                    for item in required_containers:
                        for container in containers:
                            if containers[container]['container_name'] == item and containers[container]['index'] not in selected_containers:
                                show = True
                                required_containers_index.append(containers[container]['index'])
                                output += f" {containers[container]['container_display_name']}"
                    
                    if show:
                        clear_screen(screen)
                        output += ". Press (Y) to select these containers or (N) to skip."
                        screen.addstr(int(height // 2),int((width // 2) - (len(output) // 2) - len(output) % 2), output)
                        while True:
                            k = screen.getch()

                            if k == ord('n'):
                                break
                            elif k == ord('y'):
                                selected_containers.extend(required_containers_index)
                                break
                
                if len(recommended_containers):
                    output = f"The container {selected_container_name} recommends the installation of"
                    show = False
                    for item in recommended_containers:
                        for container in containers:
                            if containers[container]['container_name'] == item and containers[container]['index'] not in selected_containers:
                                show = True
                                recommended_containers_index.append(containers[container]['index'])
                                output += f" {containers[container]['container_display_name']}"
                    
                    if show:
                        clear_screen(screen)
                        output += ". Press (Y) to select these containers or (N) to skip."
                        screen.addstr(int(height // 2),int((width // 2) - (len(output) // 2) - len(output) % 2), output)
                        while True:
                            k = screen.getch()

                            if k == ord('n'):
                                break
                            elif k == ord('y'):
                                selected_containers.extend(recommended_containers_index)
                                break                

        if curs_y > len(containers) + 1:
            curs_y = len(containers) + 1
        elif curs_y < 2:
            curs_y = 2
        

        prompt = "Please select the container(s) you wish to install"
        status_bar = "Press Space to (de)select a container | Up and Down Arrows to Navigate | Press 'n' to Proceed | 'p' for Previous Page | Press 'q' or Control + C to exit"

        for i in range (1, height - 1):  # clear all the old lines out, just in case
            screen.addstr(i, 0, " " * (width - 1))
        screen.addstr(0, 0, prompt)
        # show status bar

        screen.attron(curses.color_pair(3))
        screen.addstr(height-1, 0, status_bar)
        screen.addstr(height-1, len(status_bar), " " * (width - len(status_bar) - 1))
        screen.attroff(curses.color_pair(3))
        screen.move(curs_y, curs_x)
        index = 2

        for container in containers:
            if containers[container]['index'] not in selected_containers:
                screen.addstr(index, 0, "[ ] " + containers[container]['container_display_name'])
            else:
                screen.addstr(index, 0, "[X] " + containers[container]['container_display_name'])
            index += 1
        screen.move(curs_y, curs_x)
        screen.refresh()
        k = screen.getch()


def exit_app():
    curses.nocbreak()
    curses.echo()
    curses.endwin()
    print("output: ", output_container_config)
    write_compose()
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
    global volumes
    global advanced

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
            show_proceed_screen(screen, item['container_display_name'], height, width)
            for section, section_values in container_config.items():
                if len(re.findall(r"^section_\d+", section)):
                    
                    if 'user_description' in section_values:
                        show_section_info(screen, section_values['user_description'], height, width)

                    run_section = False
                    loops = 0
                    starting_value = 0

                    if 'loops' in section_values and 'starting_value' in section_values['loops']:
                        starting_value = section_values['loops']['starting_value']

                    if 'run_if' in section_values and ('loops' not in section_values or (('loops' in section_values and 'min_loops' in section_values['loops'] and section_values['loops']['min_loops'] == 0)) or (('loops' in section_values and 'min_loops' not in section_values['loops']))):
                        run_section =  do_run_section(screen=screen, user_question=section_values['run_if']['user_question'], height=height, width=width)
                    elif 'depends_on' in section_values:
                        run_section = True  ## TODO: ADD IN LOGIC CHECK
                    else:
                        run_section = True

                    if 'volumes' in section_values:
                        volumes = True

                    while run_section:
                        loops += 1
                        for options, option_values in section_values.items():
                            if len(re.findall(r"^group_\d+", options)) == 1:
                                result = handle_groups(screen, option_values, options, height, width)
                                if option_values['env_name'].replace("[]", str(starting_value)) in env_settings:
                                   env_settings[option_values['env_name'].replace("[]", str(starting_value))] =  option_values['field_combine'].join((env_settings[option_values['env_name']], result))
                                else:
                                    env_settings[option_values['env_name'].replace("[]", str(starting_value))] = result
                            elif len(re.findall(r"^option_\d+", options)) == 1:
                                if ('advanced' in option_values and option_values['advanced'] == True and advanced == False) or ('disable_user_set' in option_values and option_values['disable_user_set'] == True):
                                    if 'compose_required' in option_values and option_values['compose_required'] == True:
                                        if 'variable_type' not in option_values or option_values['variable_type'] == "string":
                                            env_settings[option_values['env_name'].replace("[]", str(starting_value))] = option_values['default_value']
                                        elif option_values['variable_type'] == 'boolean':
                                            env_settings[option_values['env_name'].replace("[]", str(starting_value))] = option_values['default_value']
                                elif advanced or ('disable_user_set' not in option_values or option_values['disable_user_set'] == False):
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
                                                env_settings[option_values['env_name'].replace("[]", str(starting_value))] = response

                                    elif option_values['variable_type'] == 'boolean':
                                        response = handle_boolean(screen, option_values, options)

                                        if response:
                                            if option_values['default_value'] == False or option_values['compose_required'] == True:                                                
                                                if 'boolean_override_true' in option_values:
                                                    env_settings[option_values['env_name'].replace("[]", str(starting_value))] = option_values['boolean_override_true']
                                                else:
                                                    env_settings[option_values['env_name'].replace("[]", str(starting_value))] = "True"
                                        else:
                                            if option_values['default_value'] == True or option_values['compose_required'] == True:
                                                if 'boolean_override_false' in option_values:
                                                    env_settings[option_values['env_name'].replace("[]", str(starting_value))] = option_values['boolean_override_false']
                                                else:
                                                    env_settings[option_values['env_name'].replace("[]", str(starting_value))] = "False"
                                    elif option_values['variable_type'] == 'multi_choice':
                                        response = handle_multi_choice(screen, option_values, options, height, width)

                                        env_settings[option_values['env_name'].replace("[]", str(starting_value))] = response
                            #     screen.addstr(3, 0, f"Container Variable: {option_values[options]['display_name']}")
                        starting_value += 1
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
    page = 0


def show_proceed_screen(screen, container_name, height, width):
    for i in range (1, height - 1):  # clear all the old lines out, just in case
        screen.addstr(i, 0, " " * (width - 1))
    output = f"It it now time to configure {container_name}. Press enter to proceed."
    screen.addstr(int(height // 2),int((width // 2) - (len(output) // 2) - len(output) % 2),output)
    screen.refresh()
    while True:
        k = screen.getch()

        if k == curses.KEY_ENTER or k == ord("\n") or k == ord("\r"):
            return


def show_section_info(screen, info, height, width):
    for i in range (1, height - 1):  # clear all the old lines out, just in case
        screen.addstr(i, 0, " " * (width - 1))
    output = f"{info}. Press enter to proceed."
    screen.addstr(int(height // 2),int((width // 2) - (len(output) // 2) - len(output) % 2),output)
    screen.refresh()
    while True:
        k = screen.getch()

        if k == curses.KEY_ENTER or k == ord("\n") or k == ord("\r"):
            return


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
                    if 'variable_type' not in group or group['variable_type'] == "string":
                        result = handle_string(screen, group, key, height, width)
                    elif group['variable_type'] == "multi_choice":
                        result = handle_multi_choice(screen, group, key, height, width)
                else:
                    if 'variable_type' not in group or group['variable_type'] == "string":
                        result = separator.join((result, handle_string(screen, group, key, height, width)))
                    elif group['variable_type'] == "multi-choice":
                        result = separator.join((result, handle_multi_choice(screen, group, key, height, width)))
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
                if 'validator' not in option_values or len(re.findall(option_values['validator'], variable_string)) == 1:
                    return variable_string
                else:
                    screen.addstr(curs_y - 1, 0, " " * (width - 1))
                    screen.addstr(curs_y - 1, 0, "Formatting error: " + option_values['user_required_description'])
            else:
                screen.addstr(curs_y - 1, 0, " " * (width - 1))
                screen.addstr(curs_y - 1, 0, "The value should not be blank. Please input a value")
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


def ask_advanced(screen):
    global advanced
    global page
    exit = False
    height, width = screen.getmaxyx()
    clear_screen(screen)
    curses.noecho()
    screen.addstr(2, 0, "Some containers may have advanced configuration settings. These configuration options are not necessary")
    screen.addstr(3, 0, "To change for most users. Would you like to configure advanced options?")
    selection = 1

    status_bar = "Up and Down arrow keys to select | Enter to proceed"

    # show status bar

    screen.attron(curses.color_pair(3))
    screen.addstr(height-1, 0, status_bar)
    screen.addstr(height-1, len(status_bar), " " * (width - len(status_bar) - 1))
    screen.attroff(curses.color_pair(3))
    
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
                advanced = True
                page = 2
                return
            elif selection == 1:
                advanced = False
                page = 2
                return
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


def handle_multi_choice(screen, option_values, options, height, width):
    exit = False
    curses.noecho()
    screen.addstr(7, 0, "Make your selection below")
    selection = 0
    curses.curs_set(0)
    max_selection = len(option_values['multi_choice_options'])
    k = ""
    while not exit:
        if k == curses.KEY_UP:
            selection -= 1
            if selection < 0:
                selection = max_selection - 1
        elif k == curses.KEY_DOWN:
            selection += 1
            if selection > max_selection - 1:
                selection = 0                                            
        elif k == curses.KEY_ENTER or k == 10 or k == ord("\r"):
            index = 0
            for key, item in option_values['multi_choice_options'].items():
                if selection == index:
                    return item['env_text']
                index += 1
        if not exit:
            index = 0
            for key, item in option_values['multi_choice_options'].items():
                if selection == index:
                    screen.attron(curses.A_REVERSE)
                    screen.addstr(8 + index, 0, item['user_text'])
                    screen.attroff(curses.A_REVERSE) 
                else:
                    screen.addstr(8 + index, 0, item['user_text'])
                index += 1
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
    index = 0
    for key, item in config.items():
        if len(re.findall(r"^container_\d+", key)):
            item['index'] = index
            index += 1
            containers[item['container_name']] = item


def write_compose():
    global volumes
    global output_container_config
    global containers

    try:
        tab = "  "
        with open("docker-compose.yaml", "w") as compose:
            compose.write("version: '3.8'\n\n")
            compose.write("services:\n")
            for container in output_container_config:
                compose.write(tab + container + ":\n")
                compose.write(tab + tab + "image: " + containers[container]['container_image'] + '\n')
                compose.write(tab + tab + "tty: true\n")
                compose.write(tab + tab + "container_name: " + container + "\n")
                compose.write(tab + tab + "restart: always\n")
                if 'devices' in containers[container]['container_config']:
                    compose.write(tab + tab + "devices:\n")
                    for device, device_config in containers[container]['container_config']['devices'].items():
                        if device == 'usb' and device_config == True:
                            compose.write(tab + tab + tab + "- /dev/bus/usb:/dev/bus/usb\n")
                        else:
                            compose.write(tab + tab + tab + "- " + device_config['host_device_path'] + ":" + device_config['container_device_path'] + "\n")
                if 'ports' in containers[container]['container_config']:
                    compose.write(tab + tab + "ports:\n")
                    for port, port_config in containers[container]['container_config']['ports'].items():
                        compose.write(tab + tab + tab + "- " + str(port_config['container_port']) + ":" + str(port_config['container_port']) + "\n")
                compose.write(tab + tab + "environment:\n")
                for variable, value in output_container_config[container].items():
                    compose.write(tab + tab + tab + "- " + variable + "=" + str(value) + "\n")
                if 'volumes' in containers[container]['container_config']:
                    volumes_strings = []
                    tmpfs_strings = []
                    for volume, volumes_config in containers[container]['container_config']['volumes'].items():
                        if len(re.findall(r"^volume_\d+", volume)):
                            volumes_strings.append(tab + tab + tab + f"- {volumes_config['docker_volume_name']}:{volumes_config['container_path']}\n")
                        elif len(re.findall(r"^tmpfs_\d+", volume)):
                            tmpfs_strings.append(tab + tab + tab + f"- {volumes_config['container_path']}:{volumes_config['tmpfs_options']}\n")
                        
                    if len(volumes_strings):
                        compose.write(tab + tab + "volumes:\n")
                        for line in volumes_strings:
                            compose.write(line)
                    if len(tmpfs_strings):
                        compose.write(tab + tab + "tmpfs:\n")
                        for line in tmpfs_strings:
                            compose.write(line)
                

    except Exception as e:
        print(e)
        

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
            elif page == 4:
                curses.wrapper(ask_advanced)
            else:
                exit_app()

    except KeyboardInterrupt as e:
        print("KI", e)
        exit_app()
    except Exception as e:
        print("E", e)
        exit_app()
