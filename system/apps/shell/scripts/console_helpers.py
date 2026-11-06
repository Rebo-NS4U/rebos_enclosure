"""Finish an interactive command without losing its original exit status."""


def close_console(code):
    try:
        input('\nPress Enter to close this window.')
    except (EOFError, KeyboardInterrupt):
        pass
    return code
