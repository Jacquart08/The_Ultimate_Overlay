import pygetwindow as gw

def get_active_window_title():
    try:
        win = gw.getActiveWindow()
        if win:
            return win.title
    except Exception:
        pass
    return None 