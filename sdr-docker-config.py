import curses
import sys
import json
import re
import os
import argparse
import collections
import traceback
import copy
# some bs to get the correct python library imported
try:
    import urllib.request
except Exception:
    import urllib2

SOFTWARE_VERSION = "0.7.1"
page = 1
config = collections.OrderedDict()
containers = collections.OrderedDict()
global_vars = collections.OrderedDict()
advanced = False
exit_message = None
install_path = "/opt/adsb/"
yaml_extension = ".yml"
auto_run_post_install = False

volumes = False
output_container_config = collections.OrderedDict()
system_serials = collections.OrderedDict()

def init(screen):
    # Create the curses enviornment
    screen = curses.initscr()
    height, width = screen.getmaxyx()
    if height < 30 or width < 110:
        raise EnvironmentError("Window too small!")

    global page
    global SOFTWARE_VERSION

    curses.noecho()
    curses.curs_set(0)
    curses.cbreak()
    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
    screen.attron(curses.color_pair(2))

    welcome = "WELCOME TO SDR DOCKER CONFIG version {}".format(SOFTWARE_VERSION)
    help_string = "This utility will walk you through setting up containers that will recieve, display, and feed ADSB data."
    help_string_next = "As well as containers that can receive and/or display ACARS/VDLM and airband VHF communications"
    status_bar = "Press 'n' or 'Enter' to Proceed | Press 'q' or Control + C to exit"

    clear_screen(screen)

    # show text

    screen.addstr(int(height // 2 - 3), int((width // 2) - (len(welcome) // 2) - len(welcome) % 2), welcome)
    screen.addstr(int(height // 2), int((width // 2) - (len(help_string) // 2) - len(help_string) % 2), help_string)
    screen.addstr(int(height // 2 + 1), int((width // 2) - (len(help_string_next) // 2) - len(help_string_next) % 2), help_string_next)

    # show status bar
    if len(status_bar) > width - 1:
        status_bar = status_bar[:width - 1]
    screen.attron(curses.color_pair(3))
    screen.addstr(height - 1, 0, status_bar)
    screen.addstr(height - 1, len(status_bar), " " * (width - len(status_bar) - 1))
    screen.attroff(curses.color_pair(3))

    k = ""
    while True:
        k = screen.getch()

        if k == ord('q'):
            exit_app()
        elif k == ord('n') or k == ord("\n") or k == ord('\r') or k == curses.KEY_ENTER:
            page = 4
            return
    screen.refresh()


def global_configs(screen):
    global global_vars
    global advanced
    global page
    height, width = screen.getmaxyx()
    if height < 30 or width < 110:
        raise EnvironmentError("Window too small!")
    import time
    if 'global_vars' in config:
        response = show_proceed_screen(screen, "some global configuration options")
        if response is None:
            clear_screen(screen)
            curses.noecho()
            curses.cbreak()
            curses.curs_set(1)
            curses.start_color()
            curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
            curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLUE)
            curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
            screen.attron(curses.color_pair(2))
            status_bar = "Press enter to save option and proceed"

            # show status bar
            if len(status_bar) > width - 1:
                status_bar = status_bar[:width - 1]
            screen.attron(curses.color_pair(3))
            screen.addstr(height - 1, 0, status_bar)
            screen.addstr(height - 1, len(status_bar), " " * (width - len(status_bar) - 1))
            screen.attroff(curses.color_pair(3))

            iterate_global_vars = config['global_vars']
            global_var_keys = []
            global_var_values = []

            for key, value in iterate_global_vars.items():
                if len(re.findall(r"^option_+\d+", key)):
                    global_var_keys.append(key)
                    global_var_values.append(value)
            options_index = 0
            section_responses = {}
            previous_responses = copy.deepcopy(global_vars)
            global_vars = {}
            while options_index < len(global_var_keys) and options_index >= 0:
                option_values = global_var_values[options_index]
                option_key = global_var_keys[options_index]

                if ('advanced' in option_values and option_values['advanced'] is True and advanced is False) or ('disable_user_set' in option_values and option_values['disable_user_set'] is True):
                    if 'compose_required' in option_values and option_values['compose_required'] is True:
                        if 'variable_type' not in option_values or option_values['variable_type'] == "string":
                            section_responses[option_values['env_name']] = option_values['default_value']
                        elif option_values['variable_type'] == 'boolean':
                            section_responses[option_values['env_name']] = option_values['default_value']
                        elif option_values['variable_type'] == 'timezone':
                            user_timezone = option_values['default_value']

                            if os.path.isfile("/etc/localtime"):
                                user_timezone = '/'.join(os.path.realpath('/etc/localtime').split('/')[-2:])
                            elif os.path.isfile("/etc/timezone"):
                                user_timezone = '/'.join(os.path.realpath('/etc/timezone').split('/')[-2:])
                            section_responses[option_values['env_name']] = user_timezone
                elif advanced or ('disable_user_set' not in option_values or option_values['disable_user_set'] is False):
                    for i in range(1, height - 1):  # clear all the old lines out, just in case
                        screen.addstr(i, 0, " " * (width - 1))
                    screen.addstr(3, 0, "Container Variable: {}".format(option_values['display_name']))
                    screen.addstr(4, 0, "Container Variable: {}".format(option_values['user_description']))
                    if 'user_required_description' in option_values:
                        screen.addstr(5, 0, "Required Formatting: {}".format(option_values['user_required_description']))
                    if 'variable_type' not in option_values or option_values['variable_type'] == "string":
                        previous = None
                        if option_values['env_name'] in section_responses:
                            previous = section_responses[option_values['env_name']]
                        elif option_values['env_name'] in previous_responses:
                            previous = previous_responses[option_values['env_name']]
                        response = handle_string(screen, option_values, option_key, previous)
                        if response == -1:
                            sub_iterator = options_index - 1
                            while True:
                                if sub_iterator < 0:
                                    sub_iterator -= 1
                                    break

                                if advanced or (('disable_user_set' not in option_items[sub_iterator] or option_items[sub_iterator]['disable_user_set'] is False) and ('advanced' not in option_items[sub_iterator] or option_items[sub_iterator]['advanced'] is False)):
                                    sub_iterator -= 1
                                    break
                                else:
                                    sub_iterator -= 1

                            options_index = sub_iterator
                        else:
                            section_responses[option_values['env_name']] = response
                    elif option_values['variable_type'] == "boolean":
                        previous = None
                        if option_values['env_name'] in section_responses:
                            temp_working_value = section_responses[option_values['env_name']]

                            if ('boolean_override_false' in option_values and temp_working_value == option_values['boolean_override_false']) or temp_working_value == "False":
                                previous = False
                            else:
                                previous = True
                        elif option_values['env_name'] in previous_responses:
                            temp_working_value = previous_responses[option_values['env_name']]

                            if ('boolean_override_false' in option_values and temp_working_value == option_values['boolean_override_false']) or temp_working_value == "False":
                                previous = False
                            else:
                                previous = True
                        response = handle_boolean(screen, option_values, option_key, previous)
                        if response == -1:
                            sub_iterator = options_index - 1
                            while True:
                                if sub_iterator < 0:
                                    sub_iterator -= 1
                                    break

                                if advanced or (('disable_user_set' not in option_items[sub_iterator] or option_items[sub_iterator]['disable_user_set'] is False) and ('advanced' not in option_items[sub_iterator] or option_items[sub_iterator]['advanced'] is False)):
                                    sub_iterator -= 1
                                    break
                                else:
                                    sub_iterator -= 1

                            options_index = sub_iterator
                        elif response == 0:
                            if option_values['default_value'] is False or option_values['compose_required'] is True:
                                if 'boolean_override_true' in option_values:
                                    section_responses[option_values['env_name']] = option_values['boolean_override_true']
                                else:
                                    section_responses[option_values['env_name']] = "True"
                        else:
                            if option_values['default_value'] is True or option_values['compose_required'] is True:
                                if 'boolean_override_false' in option_values:
                                    section_responses[option_values['env_name']] = option_values['boolean_override_false']
                                else:
                                    section_responses[option_values['env_name']] = "False"
                    elif option_values['variable_type'] == "timezone":
                        user_timezone = option_values['default_value']

                        if option_values['env_name'] in section_responses:
                            user_timezone = section_responses[option_values['env_name']]
                            del section_responses[option_values['env_name']]
                        elif option_values['env_name'] in previous_responses:
                            user_timezone = section_responses[option_values['env_name']]
                        else:
                            if os.path.isfile("/etc/localtime"):
                                user_timezone = '/'.join(os.path.realpath('/etc/localtime').split('/')[-2:])
                            elif os.path.isfile("/etc/timezone"):
                                user_timezone = '/'.join(os.path.realpath('/etc/timezone').split('/')[-2:])

                        response = handle_string(screen, option_values, option_key, user_timezone)

                        if response == -1:
                            sub_iterator = options_index - 1
                            while True:
                                if sub_iterator < 0:
                                    sub_iterator -= 1
                                    break

                                if advanced or (('disable_user_set' not in option_items[sub_iterator] or option_items[sub_iterator]['disable_user_set'] is False) and ('advanced' not in option_items[sub_iterator] or option_items[sub_iterator]['advanced'] is False)):
                                    sub_iterator -= 1
                                    break
                                else:
                                    sub_iterator -= 1

                            options_index = sub_iterator
                        else:
                            section_responses[option_values['env_name']] = response
                    elif option_values['variable_type'] == 'multi-choice':
                        previous = None
                        if option_values['env_name'] in section_responses:
                            temp_working_value = section_responses[option_values['env_name']]
                            del section_responses[option_values['env_name']]
                            multi_counter = 0
                            for multi_key, multi_item in option_values['multi_choice_options'].items():
                                if multi_item['env_text'] == temp_working_value:
                                    previous = multi_counter
                                else:
                                    multi_counter += 1
                        elif option_values['env_name'] in previous_responses:
                            temp_working_value = previous_responses[option_values['env_name']]

                            multi_counter = 0
                            for multi_key, multi_item in option_values['multi_choice_options'].items():
                                if multi_item['env_text'] == temp_working_value:
                                    previous = multi_counter
                                else:
                                    multi_counter += 1

                        response = handle_multi_choice(screen, option_values, options_key, previous)

                        if response == -1:
                            sub_iterator = options_index - 1
                            while True:
                                if sub_iterator < 0:
                                    break

                                if advanced or (('disable_user_set' not in option_items[sub_iterator] or option_items[sub_iterator]['disable_user_set'] is False) and ('advanced' not in option_items[sub_iterator] or option_items[sub_iterator]['advanced'] is False)):
                                    sub_iterator -= 1
                                    break
                                else:
                                    sub_iterator -= 1

                            options_index = sub_iterator
                            starting_value -= 1
                        else:
                            section_responses[option_values['env_name']] = response
                options_index += 1

            if options_index <= -1:
                page = 1
                return
            else:
                global_vars.update(section_responses)
                page = 3
                return
        else:
            page = 1
            return
    page = 3
    return


def select_containers(screen):
    global page
    global containers
    global config
    curs_x = 1
    curs_y = 3

    height, width = screen.getmaxyx()
    if height < 30 or width < 110:
        raise EnvironmentError("Window too small!")

    # build the list of headers so we can skip
    cat_header_indexes = []
    cat_index = 1
    index = 2
    for cat_key, cat_item in config['categories'].items():
        screen.addstr(index + cat_index, 0, "====={}=====".format(cat_item))
        for container in containers:
            if containers[container]['category'] == cat_key:
                index += 1
        cat_header_indexes.append(index + cat_index)
        cat_index += 1
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
    for container in containers:
        if 'selected' in containers[container] and containers[container]['selected'] is True:
            selected_containers.append(containers[container]['index'])
    while True:
        height, width = screen.getmaxyx()
        if height < 30 or width < 110:
            raise EnvironmentError("Window too small!")

        show_warning = False
        if k == ord('q'):
            exit_app()
        elif k == ord('n') or k == ord("\n") or k == ord('\r') or k == curses.KEY_ENTER:
            page = 5
            if len(selected_containers):
                for container in containers:
                    if containers[container]['index'] in selected_containers:
                        containers[container]['selected'] = True
                return
            else:
                show_warning = True
        elif k == ord('p'):
            page = 1
            return
        elif k == ord('i'):
            for container in containers:
                if containers[container]['index'] == curs_y - 2:
                    container_info(screen, containers[container])
                    continue
        elif k == curses.KEY_DOWN:
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
                    output = "The container {} requires the installation of ".format(selected_container_name)
                    show = False
                    containers_to_show = []
                    for item in required_containers:
                        for container in containers:
                            if containers[container]['container_name'] == item and containers[container]['index'] not in selected_containers:
                                show = True
                                required_containers_index.append(containers[container]['index'])
                                containers_to_show.append(containers[container]['container_display_name'])
                    output += ", ".join(i for i in containers_to_show) + "."
                    if show:
                        clear_screen(screen)
                        screen.addstr(int(height // 2), int((width // 2) - (len(output) // 2) - len(output) % 2), output)
                        output = "Press (Y) to select these containers or (N) to skip."
                        screen.addstr(int(height // 2) + 1, int((width // 2) - (len(output) // 2) - len(output) % 2), output)
                        while True:
                            k = screen.getch()

                            if k == ord('n'):
                                break
                            elif k == ord('y'):
                                selected_containers.extend(required_containers_index)
                                break

                if len(recommended_containers):
                    output = "The container {} recommends the installation of ".format(selected_container_name)
                    show = False
                    containers_to_show = []
                    for item in recommended_containers:
                        for container in containers:
                            if containers[container]['container_name'] == item and containers[container]['index'] not in selected_containers:
                                show = True
                                recommended_containers_index.append(containers[container]['index'])
                                containers_to_show.append(containers[container]['container_display_name'])
                    output += ", ".join(i for i in containers_to_show) + "."
                    if show:
                        clear_screen(screen)
                        screen.addstr(int(height // 2), int((width // 2) - (len(output) // 2) - len(output) % 2), output)
                        output = "Press (Y) to select these containers or (N) to skip."
                        screen.addstr(int(height // 2) + 1, int((width // 2) - (len(output) // 2) - len(output) % 2), output)
                        while True:
                            k = screen.getch()

                            if k == ord('n'):
                                break
                            elif k == ord('y'):
                                selected_containers.extend(recommended_containers_index)
                                break
        while curs_y in cat_header_indexes:
            if k == curses.KEY_DOWN:
                curs_y += 1
            elif k == curses.KEY_UP:
                curs_y -= 1
        if curs_y > len(containers) + len(config['categories']) + 1:
            curs_y = len(containers) + len(config['categories']) + 1
        elif curs_y < 3:
            curs_y = 3

        prompt = "Please select the container(s) you wish to install"
        status_bar = "Press Space to (de)select a container | Up and Down Arrows to Navigate | Press 'n' or 'Enter' to Proceed | 'i' for container info | Press 'q' or Control + C to exit"

        for i in range(1, height - 1):  # clear all the old lines out, just in case
            screen.addstr(i, 0, " " * (width - 1))
        screen.addstr(0, 0, prompt)
        # show status bar
        if len(status_bar) > width - 1:
            status_bar = status_bar[:width - 1]
        screen.attron(curses.color_pair(3))
        screen.addstr(height - 1, 0, status_bar)
        screen.addstr(height - 1, len(status_bar), " " * (width - len(status_bar) - 1))
        screen.attroff(curses.color_pair(3))
        screen.move(curs_y, curs_x)
        index = 2
        cat_index = 0
        if show_warning:
            screen.addstr(height - 2, 0, "Please select at least one container. If you want to exit the setup press 'q'")

        for cat_key, cat_item in config['categories'].items():
            if len(cat_item) % 2 == 0:
                padding = 1
            else:
                padding = 0

            screen.addstr(index + cat_index, 0, "=" * (30 - int(len(cat_item) / 2)) + cat_item + "=" * (30 - int(len(cat_item) / 2) + padding))
            cat_index += 1
            for container in containers:
                if containers[container]['category'] == cat_key:
                    if containers[container]['index'] not in selected_containers:
                        screen.addstr(index + cat_index, 0, "[ ] " + containers[container]['container_display_name'])
                    else:
                        screen.addstr(index + cat_index, 0, "[X] " + containers[container]['container_display_name'])
                    index += 1
        screen.move(curs_y, curs_x)
        screen.refresh()
        k = screen.getch()


def container_info(screen=None, container=None):
    if screen is None or container is None:
        return

    height, width = screen.getmaxyx()

    for i in range(1, height - 1):  # clear all the old lines out, just in case
        screen.addstr(i, 0, " " * (width - 1))

    screen.addstr(3, 0, "Container Name: " + container['container_display_name'])
    screen.addstr(4, 0, "Container Website: " + container['container_website'])
    screen.addstr(5, 0, "Container Image: " + container['container_image'])
    screen.addstr(6, 0, "Description: " + container['user_full_description'])

    status_bar = "Press p or space to return to container selection"
    if len(status_bar) > width - 1:
        status_bar = status_bar[:width - 1]
    screen.attron(curses.color_pair(3))
    screen.addstr(height - 1, 0, status_bar)
    screen.addstr(height - 1, len(status_bar), " " * (width - len(status_bar) - 1))
    screen.attroff(curses.color_pair(3))
    k = ""
    while True:
        k = screen.getch()

        if k == ord("p") or k == ord(' '):
            return


def exit_app(exit_code=0):
    global exit_message
    curses.nocbreak()
    curses.echo()
    curses.endwin()
    if exit_message is not None:
        print(exit_message)
    sys.exit(exit_code)


def clear_screen(screen):
    height, width = screen.getmaxyx()
    if height < 30 or width < 110:
        raise EnvironmentError("Window too small!")

    screen.clear()
    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
    screen.bkgd(' ', curses.color_pair(2))
    screen.refresh()


def config_container(screen, f):
    global page
    global containers
    global volumes
    global advanced
    global output_container_config
    global global_vars
    global system_serials

    height, width = screen.getmaxyx()
    if height < 30 or width < 110:
        raise EnvironmentError("Window too small!")

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
    if len(status_bar) > width - 1:
        status_bar = status_bar[:width - 1]
    screen.attron(curses.color_pair(3))
    screen.addstr(height - 1, 0, status_bar)
    screen.addstr(height - 1, len(status_bar), " " * (width - len(status_bar) - 1))
    screen.attroff(curses.color_pair(3))

    container_list = []

    for container in containers:
        item = containers[container]
        if 'selected' in item and item['selected'] is True:
            container_list.append(item)
    num_containers = 0

    while num_containers < len(container_list) and num_containers >= 0:
        item = container_list[num_containers]
        container_advanced = False
        if 'advanced'in item and item['advanced'] == True:
            container_advanced = True
        # clear the first line
        container_config = item['container_config']
        if not container_advanced or advanced:
            screen.addstr(0, 0, " " * (width - 1))
            screen.addstr(0, 0, item['container_display_name'])
            response = show_proceed_screen(screen, item['container_display_name'])
        else:
            response = None
        env_settings = {}
        container_keys = []
        container_values = []

        if response is None:
            print("doing container", file=f)  # TODO Remove
            for section, section_values in container_config.items():
                if len(re.findall(r"^section_\d+", section)) == 1:
                    container_keys.append(section)
                    container_values.append(section_values)

            section_index = 0
            while section_index < len(container_keys) and section_index >= 0:
                section_values = container_values[section_index]
                section = container_keys[section_index]
                previous_responses = {}
                section_responses = {}
                if len(re.findall(r"^section_\d+", section)) == 1:
                    run_section = False
                    loops = 0
                    starting_value = 0

                    if 'loops' in section_values and 'starting_value' in section_values['loops']:
                        starting_value = section_values['loops']['starting_value']

                    if 'run_if' in section_values and ('loops' not in section_values or (('loops' in section_values and 'min_loops' in section_values['loops'] and section_values['loops']['min_loops'] == 0)) or (('loops' in section_values and 'min_loops' not in section_values['loops']))):
                        run_section = do_run_section(screen=screen, user_question=section_values['run_if']['user_question'])
                        if run_section == -1:
                            section_index -= 2
                            run_section = False
                    elif 'depends_on' in section_values:
                        old_value = None
                        for depends_section_key, depends_section_value in env_settings.items():
                            for sub_section_key, sub_section_value in depends_section_value.items():
                                print(sub_section_key, file=f)
                                if sub_section_key == section_values['depends_on']['env_name']:
                                    old_value = sub_section_value
                                    continue
                            if old_value is not None:
                                continue

                        if old_value is not None:  # config file has a value set that should trigger running of this section
                            if 'env_name_value' in section_values['depends_on']:
                                if old_value == str(section_values['depends_on']['env_name_value']):  # need to cast the json value to string because it may be a boolean
                                    run_section = True
                            else:  # we need to grab the default value for the original variable and see if we need to run
                                for key_depends, item_depends in container_config.items():
                                    if len(re.findall(r"^section_\d+", key_depends)) == 1:
                                        for key_depends_in, item_depends_in in item_depends.items():
                                            default_value = ""
                                            if len(re.findall(r"^option_\d+", key_depends_in)) == 1 or len(re.findall(r"^group_\d+", key_depends_in)) == 1:
                                                if 'env_name' in item_depends_in and item_depends_in['env_name'] == section_values['depends_on']['env_name']:
                                                    if 'env_name_value' in item_depends_in:
                                                        default_value = str(item_depends_in['env_name_value'])
                                                    elif 'variable_type' in item_depends_in and item_depends_in['variable_type'] == "boolean":
                                                        if ('default_value' in item_depends_in and item_depends_in['default_value'] is False) or 'default_value' not in item_depends_in:
                                                            if 'boolean_override_false' in item_depends_in:
                                                                default_value = item_depends_in['boolean_override_false']
                                                            else:
                                                                default_value = "False"
                                                        elif 'default_value' in item_depends_in and item_depends_in['default_value'] is True:
                                                            if 'boolean_override_true' in item_depends_in:
                                                                default_value = item_depends_in['boolean_override_true']
                                                            else:
                                                                default_value = "True"
                                                    else:
                                                        if 'default_value' in item_depends_in:
                                                            default_value = item_depends_in['default_value']
                                                    if default_value == old_value:
                                                        run_section = True
                                                    continue

                    else:
                        run_section = True

                    if 'volumes' in section_values:
                        volumes = True

                    print("env_settings", env_settings, "section", section, file=f)  # TODO Remove
                    if section in env_settings:
                        previous_responses = env_settings[section]
                        del env_settings[section]
                    print("after", env_settings, file=f)
                    if run_section:
                        option_keys = []
                        option_items = []
                        for key, value in section_values.items():
                            if len(re.findall(r"^option_\d+", key)) == 1 or len(re.findall(r"^group_\d+", key)) == 1:
                                option_keys.append(key)
                                option_items.append(value)
                        if 'user_description' in section_values:
                            response = show_section_info(screen, section_values['user_description'])

                            if response is not None:
                                section_index -= 2
                                run_section = False

                    while run_section:
                        print("running section", file=f)
                        loops += 1
                        options_index = 0

                        while options_index < len(option_keys) and options_index >= 0:
                            options = option_keys[options_index]
                            option_values = option_items[options_index]
                            print("key ", options, file=f)  # TODO Remove
                            if len(re.findall(r"^group_\d+", options)) == 1:
                                result = handle_groups(screen, option_values, options)
                                if result != -1:
                                    if option_values['env_name'].replace("[]", str(starting_value)) in section_responses:
                                        section_responses[option_values['env_name'].replace("[]", str(starting_value))] = option_values['field_combine'].join((section_responses[option_values['env_name'].replace("[]", str(starting_value))], result))
                                    else:
                                        section_responses[option_values['env_name'].replace("[]", str(starting_value))] = result
                                else:
                                    if option_values['env_name'].replace("[]", str(starting_value - 1)) in section_responses:
                                        del section_responses[option_values['env_name'].replace("[]", str(starting_value - 1))]
                                    if option_values['env_name'].replace("[]", str(starting_value)) in section_responses:
                                        del section_responses[option_values['env_name'].replace("[]", str(starting_value))]
                                    sub_iterator = options_index - 1
                                    while True:
                                        if sub_iterator < 0:
                                            break

                                        if advanced or (('disable_user_set' not in option_items[sub_iterator] or option_items[sub_iterator]['disable_user_set'] is False) and ('advanced' not in option_items[sub_iterator] or option_items[sub_iterator]['advanced'] is False)):
                                            sub_iterator -= 1
                                            break
                                        else:
                                            sub_iterator -= 1
                                    options_index = sub_iterator
                                    starting_value -= 1

                            elif len(re.findall(r"^option_\d+", options)) == 1:
                                if ('advanced' in option_values and option_values['advanced'] is True and advanced is False) or ('disable_user_set' in option_values and option_values['disable_user_set'] is True):
                                    if 'compose_required' in option_values and option_values['compose_required'] is True:
                                        if 'variable_type' not in option_values or option_values['variable_type'] == "string":
                                            section_responses[option_values['env_name'].replace("[]", str(starting_value))] = option_values['default_value']
                                        elif option_values['variable_type'] == 'boolean':
                                            section_responses[option_values['env_name'].replace("[]", str(starting_value))] = option_values['default_value']
                                elif advanced or ('disable_user_set' not in option_values or option_values['disable_user_set'] is False):
                                    for i in range(1, height - 1):  # clear all the old lines out, just in case
                                        screen.addstr(i, 0, " " * (width - 1))
                                    screen.addstr(3, 0, "Container Variable: {}".format(option_values['display_name']))
                                    screen.addstr(4, 0, "Container Variable: {}".format(option_values['user_description']))
                                    if 'user_required_description' in option_values:
                                        screen.addstr(5, 0, "Required Formatting: {}".format(option_values['user_required_description']))

                                    if 'variable_type' not in option_values or option_values['variable_type'] == "string":
                                        previous = None
                                        if option_values['env_name'].replace("[]", str(starting_value)) in section_responses:
                                            previous = section_responses[option_values['env_name'].replace("[]", str(starting_value))]
                                            del section_responses[option_values['env_name'].replace("[]", str(starting_value))]
                                        elif option_values['env_name'].replace("[]", str(starting_value)) in previous_responses:
                                            previous = previous_responses[option_values['env_name'].replace("[]", str(starting_value))]
                                        response = handle_string(screen, option_values, options, previous)

                                        if response == -1:
                                            sub_iterator = options_index - 1
                                            while True:
                                                if sub_iterator < 0:
                                                    sub_iterator -= 1
                                                    break

                                                if advanced or (('disable_user_set' not in option_items[sub_iterator] or option_items[sub_iterator]['disable_user_set'] is False) and ('advanced' not in option_items[sub_iterator] or option_items[sub_iterator]['advanced'] is False)):
                                                    sub_iterator -= 1
                                                    break
                                                else:
                                                    sub_iterator -= 1

                                            options_index = sub_iterator
                                            starting_value -= 1
                                        elif ('default_value' in option_values and response != option_values['default_value']) or ('compose_required' in option_values and option_values['compose_required'] is True):
                                            print(response, option_values['env_name'].replace("[]", str(starting_value)), file=f)
                                            section_responses[option_values['env_name'].replace("[]", str(starting_value))] = response
                                            print(section_responses, file=f)
                                    elif option_values['variable_type'] == 'boolean':
                                        previous = None
                                        if option_values['env_name'].replace("[]", str(starting_value)) in section_responses:
                                            temp_working_value = section_responses[option_values['env_name'].replace("[]", str(starting_value))]
                                            del section_responses[option_values['env_name'].replace("[]", str(starting_value))]
                                            if ('boolean_override_false' in option_values and temp_working_value == option_values['boolean_override_false']) or temp_working_value == "False":
                                                previous = False
                                            else:
                                                previous = True
                                        elif option_values['env_name'].replace("[]", str(starting_value)) in previous_responses:
                                            temp_working_value = previous_responses[option_values['env_name'].replace("[]", str(starting_value))]

                                            if ('boolean_override_false' in option_values and temp_working_value == option_values['boolean_override_false']) or temp_working_value == "False":
                                                previous = False
                                            else:
                                                previous = True
                                        response = handle_boolean(screen, option_values, options, previous)
                                        if response == -1:
                                            sub_iterator = options_index - 1
                                            while True:
                                                if sub_iterator < 0:
                                                    sub_iterator -= 1
                                                    break

                                                if advanced or (('disable_user_set' not in option_items[sub_iterator] or option_items[sub_iterator]['disable_user_set'] is False) and ('advanced' not in option_items[sub_iterator] or option_items[sub_iterator]['advanced'] is False)):
                                                    sub_iterator -= 1
                                                    break
                                                else:
                                                    sub_iterator -= 1

                                            options_index = sub_iterator
                                            starting_value -= 1
                                        elif response == 0:
                                            if option_values['default_value'] is False or option_values['compose_required'] is True:
                                                if 'boolean_override_true' in option_values:
                                                    section_responses[option_values['env_name'].replace("[]", str(starting_value))] = option_values['boolean_override_true']
                                                else:
                                                    section_responses[option_values['env_name'].replace("[]", str(starting_value))] = "True"
                                        else:
                                            if option_values['default_value'] is True or option_values['compose_required'] is True:
                                                if 'boolean_override_false' in option_values:
                                                    section_responses[option_values['env_name'].replace("[]", str(starting_value))] = option_values['boolean_override_false']
                                                else:
                                                    section_responses[option_values['env_name'].replace("[]", str(starting_value))] = "False"
                                    elif option_values['variable_type'] == 'multi-choice':
                                        previous = None
                                        if option_values['env_name'].replace("[]", str(starting_value)) in section_responses:
                                            temp_working_value = section_responses[option_values['env_name'].replace("[]", str(starting_value))]
                                            del section_responses[option_values['env_name'].replace("[]", str(starting_value))]
                                            multi_counter = 0
                                            for multi_key, multi_item in option_values['multi_choice_options'].items():
                                                if multi_item['env_text'] == temp_working_value:
                                                    previous = multi_counter
                                                else:
                                                    multi_counter += 1
                                        elif option_values['env_name'].replace("[]", str(starting_value)) in previous_responses:
                                            temp_working_value = previous_responses[option_values['env_name'].replace("[]", str(starting_value))]

                                            multi_counter = 0
                                            for multi_key, multi_item in option_values['multi_choice_options'].items():
                                                if multi_item['env_text'] == temp_working_value:
                                                    previous = multi_counter
                                                else:
                                                    multi_counter += 1

                                        response = handle_multi_choice(screen, option_values, options, previous)

                                        if response == -1:
                                            sub_iterator = options_index - 1
                                            while True:
                                                if sub_iterator < 0:
                                                    break

                                                if advanced or (('disable_user_set' not in option_items[sub_iterator] or option_items[sub_iterator]['disable_user_set'] is False) and ('advanced' not in option_items[sub_iterator] or option_items[sub_iterator]['advanced'] is False)):
                                                    sub_iterator -= 1
                                                    break
                                                else:
                                                    sub_iterator -= 1

                                            options_index = sub_iterator
                                            starting_value -= 1
                                        else:
                                            section_responses[option_values['env_name'].replace("[]", str(starting_value))] = response
                                    elif option_values['variable_type'] == "serial":
                                        previous = None
                                        if option_values['env_name'].replace("[]", str(starting_value)) in section_responses:
                                            previous = section_responses[option_values['env_name'].replace("[]", str(starting_value))]
                                            del section_responses[option_values['env_name'].replace("[]", str(starting_value))]
                                        elif option_values['env_name'].replace("[]", str(starting_value)) in previous_responses:
                                            previous = previous_responses[option_values['env_name'].replace("[]", str(starting_value))]
                                            del previous_responses[option_values['env_name'].replace("[]", str(starting_value))]
                                        response = handle_serial(screen, option_values, options, previous)

                                        if response == -1:
                                            sub_iterator = options_index - 1
                                            while True:
                                                if sub_iterator < 0:
                                                    break

                                                if advanced or (('disable_user_set' not in option_items[sub_iterator] or option_items[sub_iterator]['disable_user_set'] is False) and ('advanced' not in option_items[sub_iterator] or option_items[sub_iterator]['advanced'] is False)):
                                                    sub_iterator -= 1
                                                    break
                                                else:
                                                    sub_iterator -= 1

                                            options_index = sub_iterator
                                            starting_value -= 1
                                        else:
                                            system_serials[response]['used'] = True
                                            section_responses[option_values['env_name'].replace("[]", str(starting_value))] = response
                            print("end of options loop. options_index", options_index, "starting value ", starting_value, file=f)
                            if options_index <= -1:
                                run_section = False
                                section_index -= 1
                            else:
                                options_index += 1
                        starting_value += 1

                        if options_index >= 0 and 'run_if' in section_values and run_section:
                            # first, lets make sure the loop actually ran if required
                            did_run_check = False

                            if 'loops' in section_values:
                                if 'min_loops' in section_values['loops'] and loops < section_values['loops']['min_loops']:
                                    for i in range(1, height - 1):  # clear all the old lines out, just in case
                                        screen.addstr(i, 0, " " * (width - 1))
                                    did_run_check = True
                                    screen.addstr(3, 0, "This section needs to be ran at least once. Please select yes on the next screen")
                                    run_section = do_run_section(screen=screen, user_question=section_values['run_if']['user_question'], first=True)
                                elif 'max_loops' in section_values['loops'] and section_values['loops']['max_loops'] >= loops:
                                    did_run_check = True
                                    run_section = False

                            if not did_run_check and 'user_question_after' not in section_values['run_if']:
                                run_section = do_run_section(screen=screen, user_question=section_values['run_if']['user_question'], first=False)
                                if run_section == -1:
                                    run_section = False
                                    section_index -= 2
                                elif not run_section:
                                    if len(section_responses):
                                        print("writing values", section_responses, section, file=f)  # TODO Remove
                                        env_settings[section] = copy.deepcopy(section_responses)
                                        section_responses = {}
                                        print("wrote sections", env_settings, file=f)  # TODO Remove
                            elif not did_run_check:
                                run_section = do_run_section(screen=screen, user_question=section_values['run_if']['user_question'], user_question_after=section_values['run_if']['user_question_after'], first=False)
                                if run_section == -1:
                                    run_section = False
                                    section_index -= 2
                                elif not run_section:
                                    if len(section_responses):
                                        print("writing values", section_responses, section, file=f)  # TODO Remove
                                        env_settings[section] = copy.deepcopy(section_responses)
                                        section_responses = {}
                                        print("wrote sections", env_settings, file=f)  # TODO Remove
                            elif did_run_check:
                                if len(section_responses):
                                    print("writing values", section_responses, section, file=f)  # TODO Remove
                                    env_settings[section] = copy.deepcopy(section_responses)
                                    section_responses = {}
                                    print("wrote sections", env_settings, file=f)  # TODO Remove
                        else:
                            run_section = False
                            if len(section_responses):
                                print("writing values", section_responses, section, file=f)  # TODO Remove
                                env_settings[section] = copy.deepcopy(section_responses)
                                section_responses = {}
                                print("wrote sections", env_settings, file=f)  # TODO Remove
                            print("ending container", file=f)  # TODO Remove

                if section_index < -1:
                    num_containers -= 1
                else:
                    section_index += 1

            if num_containers < 0:
                page = 2
                output_container_config = collections.OrderedDict()
                return
            else:
                print("env_settings for ", item['container_name'], env_settings, file=f)  # TODO Remove
                for env_key, env_item in env_settings.items():
                    if item['container_name'] not in output_container_config:
                        output_container_config[item['container_name']] = {k: v for k, v in env_item.items()}
                    else:
                        output_container_config[item['container_name']].update({k: v for k, v in env_item.items()})
                num_containers += 1
        else:
            num_containers -= 1

            if num_containers < 0:
                page = 2
                output_container_config = collections.OrderedDict()
                return
    if num_containers < 0:
        page = 2
        output_container_config = collections.OrderedDict()
        return
    page = 0


def show_proceed_screen(screen, container_name):
    height, width = screen.getmaxyx()
    if height < 30 or width < 110:
        raise EnvironmentError("Window too small!")
    for i in range(1, height - 1):  # clear all the old lines out, just in case
        screen.addstr(i, 0, " " * (width - 1))
    output = "It it now time to configure {}. Press enter to proceed.".format(container_name)
    screen.addstr(int(height // 2), int((width // 2) - (len(output) // 2) - len(output) % 2), output)
    screen.refresh()
    while True:
        height, width = screen.getmaxyx()
        if height < 30 or width < 110:
            raise EnvironmentError("Window too small!")
        k = screen.getch()

        if k == curses.KEY_ENTER or k == ord("\n") or k == ord("\r"):
            return None
        elif k == curses.KEY_PPAGE:
            return -1
        elif k == curses.KEY_NPAGE:
            return -1


def show_section_info(screen, info):
    height, width = screen.getmaxyx()
    if height < 30 or width < 110:
        raise EnvironmentError("Window too small!")
    for i in range(1, height - 1):  # clear all the old lines out, just in case
        screen.addstr(i, 0, " " * (width - 1))
    output = "{}. Press enter to proceed.".format(info)
    screen.addstr(int(height // 2), int((width // 2) - (len(output) // 2) - len(output) % 2), output)
    screen.refresh()
    while True:
        height, width = screen.getmaxyx()
        if height < 30 or width < 110:
            raise EnvironmentError("Window too small!")
        k = screen.getch()

        if k == curses.KEY_ENTER or k == ord("\n") or k == ord("\r"):
            return None
        if k == curses.KEY_ENTER or k == ord("\n") or k == ord("\r"):
            return None
        elif k == curses.KEY_PPAGE:
            return -1
        elif k == curses.KEY_NPAGE:
            return -1


def handle_groups(screen, option_values, option):
    height, width = screen.getmaxyx()
    if height < 30 or width < 110:
        raise EnvironmentError("Window too small!")
    global advanced
    output = []
    separator = option_values['field_combine']
    group_keys = []
    group_items = []

    for key, group in option_values.items():
        if len(re.findall(r"group_\d+", key)) == 1 or len(re.findall(r"option_\d+", key)):
            group_keys.append(key)
            group_items.append(group)
    index = 0

    while index < len(group_keys) and index >= 0:
        key = group_keys[index]
        group = group_items[index]
        if re.findall(r"^option_\d+", key):
            if (not advanced and 'advanced' in group and group['advanced'] is True) or (not advanced and 'disable_user_set' in group and group['disable_user_set'] is True):
                if 'compose_required' in group and group['compose_required'] is True:
                    output.append(group['default_value'])
            else:
                for i in range(1, height - 1):  # clear all the old lines out, just in case
                    screen.addstr(i, 0, " " * (width - 1))
                screen.addstr(3, 0, "Container Variable: {}".format(group['display_name']))
                screen.addstr(4, 0, "Container Variable: {}".format(group['user_description']))

                if 'variable_type' not in group or group['variable_type'] == "string":
                    result = handle_string(screen, group, key)
                elif group['variable_type'] == "multi-choice":
                    result = handle_multi_choice(screen, group, key)
                elif group['variable_type'] == "serial":
                    result = handle_serial(screen, group, key)

                if result == -1:
                    sub_iterator = index - 1

                    while True:
                        if sub_iterator < 0:
                            sub_iterator -= 1
                            break

                        if advanced or (('disable_user_set' not in group_items[sub_iterator] or group_items[sub_iterator]['disable_user_set'] is False) and ('advanced' not in group_items[sub_iterator] or group_items[sub_iterator]['advanced'] is False)):
                            sub_iterator -= 1
                            break
                        else:
                            sub_iterator -= 1

                    index = sub_iterator
                else:
                    output.append(result)

        elif re.findall(r"^group_\d", key):
            result = handle_groups(screen, group, key)

            if result == -1:
                sub_iterator = index - 1

                while True:
                    if sub_iterator < 0:
                        sub_iterator -= 1
                        break

                    if advanced or (('disable_user_set' not in group_items[sub_iterator] or group_items[sub_iterator]['disable_user_set'] is False) and ('advanced' not in group_items[sub_iterator] or group_items[sub_iterator]['advanced'] is False)):
                        sub_iterator -= 1
                        break
                    else:
                        sub_iterator -= 1
                index = sub_iterator
            else:
                output.append(result)
        if index <= -1:
            return -1
        index += 1
    return separator.join(i for i in output)


def handle_string(screen, option_values, options, previous=None):
    height, width = screen.getmaxyx()
    if height < 30 or width < 110:
        raise EnvironmentError("Window too small!")
    curses.curs_set(1)
    curs_x = 0
    curs_y = height - 2
    screen.addstr(7, 0, "Input your answer below")
    variable_string = ""
    if previous is not None:
        variable_string = previous
    elif "default_value" in option_values:
        variable_string = option_values['default_value']
        curs_x = len(variable_string)
    exit = False

    screen.addstr(curs_y, 0, variable_string)
    screen.move(curs_y, curs_x)
    while not exit:
        height, width = screen.getmaxyx()
        if height < 30 or width < 110:
            raise EnvironmentError("Window too small!")
        k = screen.getch()
        if k == curses.KEY_LEFT:
            curs_x -= 1
            if curs_x < 0:
                curs_x = 0
        elif k == curses.KEY_RIGHT:
            curs_x += 1
            if curs_x > width:
                curs_x = width
        elif k == 127 or k == curses.KEY_BACKSPACE or k == '\b' or k == '\x7f' or k == 263:
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
        elif k == curses.KEY_HOME:  # secret sauce to bypass validator
            if ('user_required' in option_values and option_values['user_required'] is True and variable_string != option_values['default_value']) or 'user_required' not in option_values or ('user_required' in option_values and option_values['user_required'] is False):
                if 'validator' not in option_values or len(re.findall(option_values['validator'], variable_string)) == 1:
                    return variable_string
        elif k == curses.KEY_ENTER or k == 10 or k == ord("\r"):
            if ('user_required' in option_values and option_values['user_required'] is True and variable_string != option_values['default_value']) or 'user_required' not in option_values or ('user_required' in option_values and option_values['user_required'] is False):
                if 'validator' not in option_values or len(re.findall(option_values['validator'], variable_string)) == 1:
                    return variable_string
                else:
                    screen.addstr(curs_y - 1, 0, " " * (width - 1))
                    if 'user_required_description' in option_values:
                        screen.addstr(curs_y - 1, 0, "Formatting error: " + option_values['user_required_description'])
                    else:
                        screen.addstr(curs_y - 1, 0, "Formatting error")
            else:
                screen.addstr(curs_y - 1, 0, " " * (width - 1))
                screen.addstr(curs_y - 1, 0, "The value should not be blank. Please input a value")
        elif k == curses.KEY_PPAGE:
            return -1
        elif k == curses.KEY_NPAGE:
            return -1
        if not exit:
            screen.addstr(curs_y, 0, " " * (width - 1))
            screen.addstr(curs_y, 0, variable_string)
            screen.move(curs_y, curs_x)
            screen.refresh()


def handle_boolean(screen, option_values, options, value_override=None):
    height, width = screen.getmaxyx()
    if height < 30 or width < 110:
        raise EnvironmentError("Window too small!")
    exit = False
    curses.noecho()
    screen.addstr(7, 0, "Make your selection below")
    if value_override is not None:
        if value_override:
            selection = 0
        else:
            selection = 1
    elif 'default_value' not in option_values or option_values['default_value'] is True:
        selection = 0
    else:
        selection = 1

    curses.curs_set(0)
    k = ""
    while not exit:
        height, width = screen.getmaxyx()
        if height < 30 or width < 110:
            raise EnvironmentError("Window too small!")
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
                return 0
            elif selection == 1:
                return 1
                exit = True
        elif k == curses.KEY_PPAGE:
            return -1
        elif k == curses.KEY_NPAGE:
            return -1
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
    if height < 30 or width < 110:
        raise EnvironmentError("Window too small!")
    clear_screen(screen)
    curses.noecho()
    screen.addstr(2, 0, "Some containers may have advanced configuration settings. These configuration options are not necessary")
    screen.addstr(3, 0, "To change for most users. Would you like to configure advanced options?")
    selection = 1

    status_bar = "Up and Down arrow keys to select | Enter to proceed"

    # show status bar
    if len(status_bar) > width - 1:
        status_bar = status_bar[:width - 1]
    screen.attron(curses.color_pair(3))
    screen.addstr(height - 1, 0, status_bar)
    screen.addstr(height - 1, len(status_bar), " " * (width - len(status_bar) - 1))
    screen.attroff(curses.color_pair(3))

    curses.curs_set(0)
    k = ""
    while not exit:
        height, width = screen.getmaxyx()
        if height < 30 or width < 110:
            raise EnvironmentError("Window too small!")
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


def handle_multi_choice(screen, option_values, options, previous=None):
    height, width = screen.getmaxyx()
    if height < 30 or width < 110:
        raise EnvironmentError("Window too small!")
    exit = False
    curses.noecho()
    screen.addstr(7, 0, "Make your selection below")
    selection = 0
    if previous is not None:
        selection = previous
    curses.curs_set(0)
    max_selection = len(option_values['multi_choice_options'])
    k = ""

    while not exit:
        height, width = screen.getmaxyx()
        if height < 30 or width < 110:
            raise EnvironmentError("Window too small!")
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
        elif k == curses.KEY_PPAGE:
            return -1
        elif k == curses.KEY_NPAGE:
            return -1
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


def handle_serial(screen, option_values, options, previous=None):
    global system_serials
    height, width = screen.getmaxyx()
    if height < 30 or width < 110:
        raise EnvironmentError("Window too small!")
    if not len(system_serials):
        return handle_string(screen, option_values, options, previous)
    exit = False
    found_good_serials = False
    curses.noecho()
    screen.addstr(7, 0, "Make your selection below")
    selection = 0
    if previous is not None:
        for key, item in system_serials.items():
            if key == previous:
                selection = item['index']
    else:
        for key, item in system_serials.items():
            if item['used'] == False:
                selection = item['index']
                found_good_serials = True
                break

    if not found_good_serials:
        return handle_string(screen, option_values, options, previous)
    curses.curs_set(0)
    max_selection = len(system_serials)
    k = ""

    while not exit:
        height, width = screen.getmaxyx()
        if height < 30 or width < 110:
            raise EnvironmentError("Window too small!")
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
            for key, item in system_serials.items():
                if selection == item['index']:
                    return key
                index += 1
        elif k == curses.KEY_PPAGE:
            return -1
        elif k == curses.KEY_NPAGE:
            return -1
        if not exit:
            index = 0
            for key, item in system_serials.items():
                if item['used'] == False:
                    if selection == item['index']:
                        screen.attron(curses.A_REVERSE)
                        screen.addstr(8 + index, 0, key)
                        screen.attroff(curses.A_REVERSE)
                    else:
                        screen.addstr(8 + index, 0, key)
                index += 1
            screen.refresh()
            k = screen.getch()


def do_run_section(screen, user_question, user_question_after=None, first=True):
    height, width = screen.getmaxyx()
    if height < 30 or width < 110:
        raise EnvironmentError("Window too small!")
    for i in range(1, height - 1):  # clear all the old lines out, just in case
        screen.addstr(i, 0, " " * (width - 1))

    if first or user_question_after is None:
        screen.addstr(3, 0, "{}".format(user_question))
    else:
        screen.addstr(3, 0, "{}".format(user_question_after))

    selection = 0
    exit = False
    k = ""
    while not exit:
        height, width = screen.getmaxyx()
        if height < 30 or width < 110:
            raise EnvironmentError("Window too small!")
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
        elif k == curses.KEY_PPAGE:
            return -1
        elif k == curses.KEY_NPAGE:
            return -1
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


def raise_on_duplicate_keys(ordered_pairs):
    """Raise ValueError if a duplicate key exists in provided ordered list of pairs, otherwise return a dict."""
    dict_out = collections.OrderedDict()
    for key, val in ordered_pairs:
        if key in dict_out:
            raise ValueError('Duplicate key: {}'.format(key))
        else:
            dict_out[key] = val
    return dict_out


def get_containers():
    global config
    global containers
    index = 0
    cat_index = 0
    for cat_key, cat_item in config['categories'].items():
        cat_index += 1
        for config_key, config_item in config.items():
            if len(re.findall(r"^container_\d+", config_key)) and config_item['category'] == cat_key:
                config_item['index'] = index + cat_index
                index += 1
                containers[config_item['container_name']] = config_item


def write_compose(screen):
    import shutil
    import datetime

    global volumes
    global output_container_config
    global containers
    global exit_message
    global install_path
    global global_vars
    global yaml_extension
    global auto_run_post_install
    yaml_file = "docker-compose"
    env_file = ".env"
    ports = []
    ports_output = []
    installed_containers = []
    addtional_setup_required = []
    post_run_commands = []  # tuple with container name, desription, command string
    exit_message = ""

    try:
        if not os.path.isdir(install_path):
            os.makedirs(install_path)

        if os.path.isfile(install_path + yaml_file + yaml_extension):
            exit = False
            clear_screen(screen)
            height, width = screen.getmaxyx()

            screen.addstr(7, 0, "Make your selection below")
            screen.addstr(0, 0, "There is already a {}{} file in the {} directory. Would you like to overwrite or backup this file?".format(yaml_file, yaml_extension, install_path))
            selection = 0

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
                        break
                    elif selection == 1:
                        shutil.copyfile(install_path + yaml_file + yaml_extension, install_path + yaml_file + yaml_extension + ".backup." + datetime.datetime.now().strftime("%Y%m%d-%H%M"))
                        break
                if not exit:
                    if selection == 0:
                        screen.attron(curses.A_REVERSE)
                        screen.addstr(8, 0, "Overwrite")
                        screen.attroff(curses.A_REVERSE)
                        screen.addstr(9, 0, "Backup")
                    else:
                        screen.addstr(8, 0, "Overwrite")
                        screen.attron(curses.A_REVERSE)
                        screen.addstr(9, 0, "Backup")
                        screen.attroff(curses.A_REVERSE)
                    screen.refresh()
                    k = screen.getch()

        if os.path.isfile(install_path + env_file):
            exit = False
            clear_screen(screen)
            height, width = screen.getmaxyx()

            screen.addstr(7, 0, "Make your selection below")
            screen.addstr(0, 0, "There is already a {} file in the {} directory. Would you like to overwrite or backup this file?".format(env_file, install_path))
            selection = 0

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
                        break
                    elif selection == 1:
                        shutil.copyfile(install_path + env_file, install_path + env_file + ".backup." + datetime.datetime.now().strftime("%Y%m%d-%H%M"))
                        break
                if not exit:
                    if selection == 0:
                        screen.attron(curses.A_REVERSE)
                        screen.addstr(8, 0, "Overwrite")
                        screen.attroff(curses.A_REVERSE)
                        screen.addstr(9, 0, "Backup")
                    else:
                        screen.addstr(8, 0, "Overwrite")
                        screen.attron(curses.A_REVERSE)
                        screen.addstr(9, 0, "Backup")
                        screen.attroff(curses.A_REVERSE)
                    screen.refresh()
                    k = screen.getch()

        tab = "  "
        with open(install_path + yaml_file + yaml_extension, "w") as compose:
            compose.write("version: '3.8'\n\n")
            # write the volumes first
            wrote_volumes = False

            for container_volumes in output_container_config:
                if 'volumes' in containers[container_volumes]['container_config']:
                    for key, volume in containers[container_volumes]['container_config']['volumes'].items():
                        if 'docker_volume_name' in volume:
                            if 'volume_override' not in volume or volume['volume_override'] == "":
                                volume_options = ""
                                if 'volume_options' in volume:
                                    volume_options += "\n" + volume['volume_options']
                                if not wrote_volumes:
                                    compose.write("volumes:\n")
                                    wrote_volumes = True
                                compose.write(tab + volume['docker_volume_name'] + ":" + volume_options + "\n")

            compose.write("services:\n")
            for container in output_container_config:
                installed_containers.append(containers[container]['container_display_name'])
                if 'post_install_actions' in containers[container]:
                    post_run_commands.append((containers[container]['container_display_name'], containers[container]['post_install_user_description'], containers[container]['post_install_actions']))
                compose.write(tab + container + ":\n")
                compose.write(tab + tab + "image: " + containers[container]['container_image'] + '\n')
                compose.write(tab + tab + "tty: true\n")
                compose.write(tab + tab + "container_name: " + container + "\n")
                compose.write(tab + tab + "restart: always\n")

                if 'requires' in containers[container]:
                    did_write = False
                    for required_key, required_item in containers[container]['requires'].items():
                        if required_item in output_container_config:
                            if not did_write:
                                compose.write(tab + tab + "depends_on:\n")
                                did_write = True
                            compose.write(tab + tab + tab + "- " + required_item + "\n")
                if 'devices' in containers[container]['container_config']:
                    compose.write(tab + tab + "devices:\n")
                    for device, device_config in containers[container]['container_config']['devices'].items():
                        if device == 'usb' and device_config is True:
                            compose.write(tab + tab + tab + "- /dev/bus/usb:/dev/bus/usb\n")
                        else:
                            compose.write(tab + tab + tab + "- " + device_config['host_device_path'] + ":" + device_config['container_device_path'] + "\n")
                if 'ports' in containers[container]['container_config']:
                    compose.write(tab + tab + "ports:\n")
                    for port, port_config in containers[container]['container_config']['ports'].items():
                        if 'exclude' not in port_config or port_config['exclude'] is not False:
                            if 'description' in port_config:
                                description = port_config['description']
                            else:
                                description = ""
                            host_port = port_config['container_port']
                            while host_port in ports:
                                host_port += 1
                            ports.append(host_port)
                            ports_output.append((containers[container]['container_display_name'], host_port, description))
                            compose.write(tab + tab + tab + "- " + str(host_port) + ":" + str(port_config['container_port']) + "\n")
                compose.write(tab + tab + "environment:\n")
                for variable, value in output_container_config[container].items():
                    try:
                        bypass_yaml = ""
                        output_string = value
                        add_to_env = False
                        # now we need to decide if the yaml should be bypassed
                        # TODO: rewrite this to loop once and save each value to a list we can check against
                        for section_key, section_item in containers[container]['container_config'].items():
                            if len(re.findall(r"^section_\d+", section_key)) > 0:
                                for option_key, option_item in section_item.items():
                                    if len(re.findall(r"option_\d+", option_key)):
                                        if option_item['env_name'] == variable:
                                            if 'env' in option_item and option_item['env']== True:
                                                add_to_env = True
                                            if 'addtional_setup_required' in option_item and value == option_item['default_value']:
                                                if containers[container]['container_display_name'] not in addtional_setup_required:
                                                    addtional_setup_required.append(containers[container]['container_display_name'])
                                            if 'bypass_yaml' in option_item and option_item['bypass_yaml'] is True:
                                                bypass_yaml = "'"
                                                if 'replace_characters' in option_item:
                                                    for character in option_item['replace_characters']:
                                                        output_string = output_string.replace(character, character * 2)
                                            continue
                        if not add_to_env:
                            compose.write(tab + tab + tab + "- {}".format(bypass_yaml) + variable + "=" + str(output_string) + "{}\n".format(bypass_yaml))
                        else:
                            compose.write(tab + tab + tab + "- {}".format(bypass_yaml) + variable + "=${" + container.upper() + "_" + variable.upper() + "}" + "{}\n".format(bypass_yaml))
                            if container.upper() + "_" + variable.upper() not in global_vars:
                                global_vars[container.upper() + "_" + variable.upper()] = str(output_string)
                    except Exception as e:
                        import time
                        print(e)
                        time.sleep(10)
                # check for template variables
                for template_key, template_item in containers[container]['container_config'].items():
                    if len(re.findall(r"^template_\d+", template_key)) > 0:
                        output_template = ""
                        separator = ""
                        if "separator" in template_item:
                            separator = template_item['separator']
                        for sub_template_key, sub_template_item in template_item.items():
                            if len(re.findall(r"^include_\d+", sub_template_key)):
                                if sub_template_item['container'] in output_container_config and sub_template_item['env_name'] in output_container_config[sub_template_item['container']]:
                                    if "value_is" in sub_template_item and sub_template_item['value_is'] == output_container_config[sub_template_item['container']][sub_template_item['env_name']]:
                                        value_to_append = ""
                                        if "value" in sub_template_item:
                                            value_to_append = sub_template_item['value']
                                        else:
                                            value_to_append = output_container_config[sub_template_item['container']][sub_template_item['env_name']]

                                        if len(output_template) != 0:
                                            output_template += separator + value_to_append
                                        else:
                                            output_template += value_to_append
                                    elif "value_is_not" in sub_template_item and sub_template_item['value_is_not'] != output_container_config[sub_template_item['container']][sub_template_item['env_name']]:
                                        value_to_append = ""
                                        if "value" in sub_template_item:
                                            value_to_append = sub_template_item['value']
                                        else:
                                            value_to_append = output_container_config[sub_template_item['container']][sub_template_item['env_name']]

                                        if len(output_template) != 0:
                                            output_template += separator + value_to_append
                                        else:
                                            output_template += value_to_append
                                    elif "port" in sub_template_item:
                                        if len(output_template) != 0:
                                            output_template += separator + str(containers[container]['container_config']['ports'][sub_template_item['port']]['container_port'])
                                        else:
                                            output_template += str(containers[container]['container_config']['ports'][sub_template_item['port']]['container_port'])
                        if len(output_template) > 0:
                            compose.write(tab + tab + tab + "- " + template_item['env_name_out'] + "=" + output_template + "\n")

                if 'volumes' in containers[container]['container_config']:
                    volumes_strings = []
                    tmpfs_strings = []
                    for volume, volumes_config in containers[container]['container_config']['volumes'].items():
                        if len(re.findall(r"^volume_\d+", volume)):
                            if 'volume_override' in volumes_config and volumes_config['volume_override'] != "":
                                volumes_strings.append(tab + tab + tab + "- {}:{}\n".format(volumes_config['volume_override'], volumes_config['container_path']))
                            else:
                                volumes_strings.append(tab + tab + tab + "- {}:{}\n".format(volumes_config['docker_volume_name'], volumes_config['container_path']))
                        elif len(re.findall(r"^tmpfs_\d+", volume)):
                            tmpfs_strings.append(tab + tab + tab + "- {}:{}\n".format(volumes_config['container_path'], volumes_config['tmpfs_options']))

                    if len(volumes_strings):
                        compose.write(tab + tab + "volumes:\n")
                        for line in volumes_strings:
                            compose.write(line)
                    if len(tmpfs_strings):
                        compose.write(tab + tab + "tmpfs:\n")
                        for line in tmpfs_strings:
                            compose.write(line)

                    exit = False
            with open(install_path + env_file, "w") as env:
                for env_key, env_item in global_vars.items():
                    env.write(env_key + "=" + env_item + "\n")
            if len(post_run_commands):
                if not auto_run_post_install:
                    import subprocess
                    clear_screen(screen)
                    command_index = 0
                    while command_index < len(post_run_commands):
                        exit = False
                        height, width = screen.getmaxyx()
                        command_container, description, command = post_run_commands[command_index]
                        screen.addstr(7, 0, "Make your selection below")
                        screen.addstr(0, 0, "The container {} requires addtional setup.\n{}".format(command_container, description))
                        selection = 0

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
                                    try:
                                        run_command = subprocess.run(command.replace("{path}", install_path), stdout=subprocess.DEVNULL, shell=True)
                                        run_command.wait()
                                    except Exception as e:
                                        print(e)
                                        print(command)
                                        traceback.print_exc()
                                    break
                                elif selection == 1:
                                    break
                            if not exit:
                                if selection == 0:
                                    screen.attron(curses.A_REVERSE)
                                    screen.addstr(8, 0, "Run Command")
                                    screen.attroff(curses.A_REVERSE)
                                    screen.addstr(9, 0, "Skip Command")
                                else:
                                    screen.addstr(8, 0, "Run Command")
                                    screen.attron(curses.A_REVERSE)
                                    screen.addstr(9, 0, "Skip Command")
                                    screen.attroff(curses.A_REVERSE)
                                screen.refresh()
                                k = screen.getch()
                        command_index += 1
                else:
                    clear_screen(screen)
                    screen.addstr(0,0, "Some containers require additional setup. Running these commands now. Please stand by!")
                    try:
                        for command_container, description, command in post_run_commands:
                            run_command = subprocess.run(command.replace("{path}", install_path), stdout=subprocess.DEVNULL, shell=True)
                            run_command.wait()
                    except Exception as e:
                        print(e)
                        print(command)
                        traceback.print_exc()

                    time.sleep(4)  # these commands probably will finish lighting fast. Adding a delay in just to let the user know something is happening

            # display summary screen
            clear_screen(screen)
            exit_message += "Your {}{}{} file has been written. This is the file docker-compose will get all of its information from.\n\n".format(install_path, yaml_file, yaml_extension)
            exit_message += "Your {}{} file has been written. This file saves sensitive or common values that are shared between a lot of containers.".format(install_path, env_file)
            exit_message += "\n\n" + "The following containers have been set up:\n\n"

            screen.addstr(0, 0, "Your {}{}{} file has been written. After you have reviewed this press enter to exit".format(install_path, yaml_file, yaml_extension))
            screen.addstr(1, 0, "Your {}{} file has been written. This file saves sensitive or common values that are shared between a lot of containers.".format(install_path, env_file))
            screen.addstr(4, 0, "The following containers have been set up:")

            container_index = 6
            for item in installed_containers:
                information = ""
                if item in addtional_setup_required:
                    information = " (*****!!!!!ADDITONAL SETUP REQUIRED!!!!!*****)"
                exit_message += item + information + "\n"
                screen.addstr(container_index, 0, item + information)
                container_index += 1

            container_index += 2

            if len(ports_output):
                exit_message += "\nThe following ports have been mapped and will be accessable at this computer's LAN IP address:\n\n"
                screen.addstr(container_index, 0, "The following ports have been mapped and will be accessable at this computer's LAN IP address:")

                container_index += 1
                for name, item, port_description in ports_output:
                    exit_message += name + ": " + str(item) + " " + port_description + "\n"
                    screen.addstr(container_index, 0, name + ": " + str(item) + " " + port_description)
                    container_index += 1

            if len(addtional_setup_required):
                exit_message += "\nSome containers require addtional setup. Please review the www.sdrdockerconfig.com website (link for each container is above) for specifics on what each container needs\n"

            exit_message += "\nPlease see the www.sdrdockerconfig.com tutorial section for next steps. Once all pre-requisites have been met you can 'cd {}' and run 'docker-compose up -d' to start all of the containers".format(install_path)
            curses.curs_set(0)
            k = ""
            exit = False
            while not exit:
                if k == curses.KEY_ENTER or k == 10 or k == ord("\r"):
                    exit = True
                else:
                    k = screen.getch()
    except Exception as e:
        print(e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate docker-compose yaml file')

    parser.add_argument(
        '--files', '-f',
        type=str,
        help='The plugin file to use. By default the program will grab the plugin file from the www.sdrdockerconfig.com website. Using this option you can override and use a local copy',
        required=False,
    )

    parser.add_argument(
        '--install', '-i',
        type=str,
        help='Override the install path. Default path is /opt/adsb/',
        required=False,
    )

    parser.add_argument(
        '--yaml', '-y',
        action='store_true',
        help='Use .yaml instead of the default .yml for the docker-compose file'
    )

    parser.add_argument(
        '--auto', '-a',
        action='store_true',
        help='Auto run any post-installation commands required by the container without prompting.'
    )

    parser.add_argument(
        '--serials', '-s',
        type=str,
        help="List of SDR serial numbers",
        nargs="+",
        required=False
    )

    args = parser.parse_args()

    if args.yaml:
        yaml_extension = ".yaml"

    if args.auto:
        auto_run_post_install = True

    serial_index = 0
    for serial in [serial for serial  in (args.serials or [])]:
        if serial in system_serials:
            print("Duplicate serials detected! Aborting! Input {}".format(sys.argv))
            sys.exit(1)

        system_serials[serial] = {"number": serial, "used": False, "container": None, "index": serial_index}
        serial_index += 1

    if args.install is not None:
        install_path = args.install
        if not install_path.endswith("/") or not install_path.endswith("\\"):
            install_path += "/"  # going to assume unix pathing...too lazy to figure out if it's windows
    try:
        if args.files is not None:
            config = json.load(open(args.files), object_pairs_hook=raise_on_duplicate_keys)
        else:
            # open the file. Using try/except so that the correct libraries are used
            try:
                config = json.loads(urllib.request.urlopen("https://raw.githubusercontent.com/fredclausen/sdr-docker-config/main/plugins/plugin.json").read().decode(), object_pairs_hook=raise_on_duplicate_keys)
            except Exception:
                try:
                    config = json.loads(urllib2.urlopen(urllib2.Request("https://raw.githubusercontent.com/fredclausen/sdr-docker-config/main/plugins/plugin.json")).read().decode(), object_pairs_hook=raise_on_duplicate_keys)
                except Exception:
                    pass

        if not config:
            print("Error with loading plugins.")
            sys.exit(1)
        get_containers()
        while True:
            if page == 1:
                curses.wrapper(init)
            elif page == 5:
                curses.wrapper(global_configs)
            elif page == 2:
                curses.wrapper(select_containers)
            elif page == 3:
                # TODO: Remove this. Debugging
                with open('output.txt', "w", buffering=1) as f:
                    print("starting program", file=f)
                    curses.wrapper(config_container, f)
            elif page == 4:
                curses.wrapper(ask_advanced)
            elif page == 0:
                curses.wrapper(write_compose)
                exit_app()
            else:
                exit_app()

    except KeyboardInterrupt:
        exit_app(exit_code=1)
    except ValueError as e:
        print("Duplicate key detected: ", e)
        exit_app(exit_code=3)
    except EnvironmentError as e:
        print(e)
        exit_app(exit_code=3)
    except Exception as e:
        print("Exception: ", e, repr(e))
        traceback.print_exc()
        exit_app(exit_code=2)
