import curses
import sys
import time

def init(screen):
    # Create the curses enviornment
    screen = curses.initscr()
    height, width = screen.getmaxyx()
    
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
            show_containers(screen)
    screen.refresh()

def show_containers(screen):
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
    status_bar = "Press 'n' to Proceed | Press 'q' or Control + C to exit"
    container_list = ["ACARS Hub", "ADSB Exchange"]

    screen.addstr(0, 0, prompt)
    index = 2
    for container in container_list:
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
            pass
        if k == curses.KEY_DOWN:
            curs_y = curs_y + 1
        elif k == curses.KEY_UP:
            curs_y = curs_y - 1
        
        if curs_y > len(container_list) + 1:
            curs_y = len(container_list) + 1
        elif curs_y < 2:
            curs_y = 2
        
        index = 2

        for container in container_list:
            screen.addstr(index, 0, "[ ] " + container)
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

if __name__ == "__main__":
    try:
        curses.wrapper(init)
    except KeyboardInterrupt as e:
        print(e)
        exit_app()
    except Exception as e:
        print(e)
        exit_app()

