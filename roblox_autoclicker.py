import ctypes
import json
import os
import subprocess
import threading
import time
import tkinter as tk
from tkinter import filedialog, ttk


user32 = ctypes.WinDLL("user32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_MBUTTON = 0x04
VK_XBUTTON1 = 0x05
VK_XBUTTON2 = 0x06
VK_SHIFT = 0x10
VK_F7 = 0x76
VK_F8 = 0x77
VK_NUMPAD0 = 0x60
VK_MULTIPLY = 0x6A

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010

WH_MOUSE_LL = 14
HC_ACTION = 0
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
LLMHF_INJECTED = 0x00000001
SEE_MASK_NOCLOSEPROCESS = 0x00000040
SW_SHOWNORMAL = 1
STILL_ACTIVE = 259

VK_NAMES = {
    0x08: "Backspace",
    0x09: "Tab",
    0x0D: "Enter",
    0x10: "Shift",
    0x11: "Ctrl",
    0x12: "Alt",
    0x14: "Caps Lock",
    0x1B: "Esc",
    0x20: "Space",
    0x21: "Page Up",
    0x22: "Page Down",
    0x23: "End",
    0x24: "Home",
    0x25: "Left",
    0x26: "Up",
    0x27: "Right",
    0x28: "Down",
    0x2D: "Insert",
    0x2E: "Delete",
    VK_MBUTTON: "Middle Mouse",
    VK_XBUTTON1: "Mouse 4",
    VK_XBUTTON2: "Mouse 5",
    0x6A: "Numpad *",
    0x6B: "Numpad +",
    0x6D: "Numpad -",
    0x6E: "Numpad .",
    0x6F: "Numpad /",
}
VK_NAMES.update({vk: chr(vk) for vk in range(0x30, 0x3A)})
VK_NAMES.update({vk: chr(vk) for vk in range(0x41, 0x5B)})
VK_NAMES.update({VK_NUMPAD0 + index: f"Numpad {index}" for index in range(10)})
VK_NAMES.update({0x70 + index: f"F{index + 1}" for index in range(12)})

KEYBIND_VKS = list(VK_NAMES.keys())

CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Autoclicker")
CONFIG_PATH = os.path.join(CONFIG_DIR, "settings.json")


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class SHELLEXECUTEINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("fMask", ctypes.c_ulong),
        ("hwnd", ctypes.c_void_p),
        ("lpVerb", ctypes.c_wchar_p),
        ("lpFile", ctypes.c_wchar_p),
        ("lpParameters", ctypes.c_wchar_p),
        ("lpDirectory", ctypes.c_wchar_p),
        ("nShow", ctypes.c_int),
        ("hInstApp", ctypes.c_void_p),
        ("lpIDList", ctypes.c_void_p),
        ("lpClass", ctypes.c_wchar_p),
        ("hkeyClass", ctypes.c_void_p),
        ("dwHotKey", ctypes.c_ulong),
        ("hIcon", ctypes.c_void_p),
        ("hProcess", ctypes.c_void_p),
    ]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", POINT),
        ("mouseData", ctypes.c_ulong),
        ("flags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, ctypes.c_size_t, ctypes.c_ssize_t)


shell32.ShellExecuteExW.argtypes = [ctypes.POINTER(SHELLEXECUTEINFO)]
shell32.ShellExecuteExW.restype = ctypes.c_bool
kernel32.TerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_uint]
kernel32.TerminateProcess.restype = ctypes.c_bool
kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
kernel32.CloseHandle.restype = ctypes.c_bool
kernel32.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
kernel32.GetExitCodeProcess.restype = ctypes.c_bool
kernel32.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
kernel32.GetModuleHandleW.restype = ctypes.c_void_p
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, ctypes.c_void_p, ctypes.c_ulong]
user32.SetWindowsHookExW.restype = ctypes.c_void_p
user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t, ctypes.c_ssize_t]
user32.CallNextHookEx.restype = ctypes.c_ssize_t
user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
user32.UnhookWindowsHookEx.restype = ctypes.c_bool


def key_down(vk):
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def key_pressed(vk, previous_down):
    now = key_down(vk)
    return now and not previous_down, now


def foreground_hwnd():
    return user32.GetForegroundWindow()


def window_title(hwnd):
    if not hwnd:
        return ""
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def is_roblox_window(hwnd):
    return "roblox" in window_title(hwnd).lower()


def cursor_center_distance(hwnd):
    rect = RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return None

    width = rect.right - rect.left
    height = rect.bottom - rect.top
    if width <= 0 or height <= 0:
        return None

    center = POINT(width // 2, height // 2)
    if not user32.ClientToScreen(hwnd, ctypes.byref(center)):
        return None

    cursor = POINT()
    if not user32.GetCursorPos(ctypes.byref(cursor)):
        return None

    tolerance = max(8, min(26, int(min(width, height) * 0.020)))
    distance = max(abs(cursor.x - center.x), abs(cursor.y - center.y))
    return distance, tolerance


def release_button(button):
    if button == "left":
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    else:
        user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)


def click(button):
    release_button(button)
    if button == "left":
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    else:
        user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)


class AutoClickerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Autoclicker")
        self.root.minsize(440, 280)

        self.running = tk.BooleanVar(value=False)
        self.left_enabled = tk.BooleanVar(value=True)
        self.right_enabled = tk.BooleanVar(value=True)
        self.require_shiftlock = tk.BooleanVar(value=True)
        self.roblox_only = tk.BooleanVar(value=True)
        self.always_on_top = tk.BooleanVar(value=False)
        self.shiftlock_on = tk.BooleanVar(value=False)
        self.cps = tk.IntVar(value=20)
        self.theme = tk.StringVar(value="light")

        self.keybind_vk = VK_F8
        self.keybind_name = VK_NAMES[VK_F8]
        self.mini_keybind_vk = VK_F7
        self.mini_keybind_name = VK_NAMES[VK_F7]
        self._last_toggle_key = False
        self._last_mini_key = False
        self._capture_target = None
        self._capture_armed = False
        self._mini_window = None
        self._mini_tile = None
        self._mini_drag = None
        self._mini_moved = False
        self.mini_x = 80
        self.mini_y = 80
        self._last_shift_key = False
        self._last_click_time = 0.0
        self._active_button = None
        self._synthetic_button_down = None
        self._cps_value = self.cps.get()
        self._click_lock = threading.RLock()
        self._click_thread_stop = threading.Event()
        self._click_thread = None
        self._mouse_hook = None
        self._mouse_hook_proc = None
        self._physical_left_down = False
        self._physical_right_down = False
        self._right_block_until_release = False
        self._left_was_down = False
        self._right_was_down = False
        self._press_sequence = 0
        self._left_press_sequence = 0
        self._right_press_sequence = 0
        self._active_hwnd = None
        self._shiftlock_by_hwnd = {}
        self._last_center_distance_by_hwnd = {}
        self._shift_verify_until_by_hwnd = {}
        self._shift_unlock_until_by_hwnd = {}
        self._centered_since_by_hwnd = {}
        self._off_center_since_by_hwnd = {}
        self.checkbuttons = []
        self.theme_options = []
        self.ahk_folder = ""
        self.ahk_panel_visible = False
        self.ahk_macros = []
        self.ahk_favorites = set()
        self.ahk_processes = {}
        self._ahk_menu_index = None
        self._last_macro_check = 0.0
        self._foreground = "#111827"
        self._box_background = "#ffffff"
        self._list_background = "#ffffff"
        self._list_foreground = "#111827"
        self._list_select_background = "#d1d5db"
        self._list_active_background = "#bbf7d0"
        self._list_favorite_foreground = "#ca8a04"

        self.load_settings()
        self._cps_value = max(1, min(100, int(self.cps.get())))
        self.style = ttk.Style()
        self._build_ui()
        self.apply_theme()
        self.apply_always_on_top()
        self.add_setting_traces()
        self.install_mouse_hook()
        self.start_click_worker()
        self.root.after(5, self._loop)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        outer = ttk.Frame(self.root, padding=14)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1)
        outer.columnconfigure(1, weight=0)
        outer.rowconfigure(1, weight=1)

        title = ttk.Label(outer, text="Autoclicker", font=("Segoe UI", 14, "bold"))
        title.grid(row=0, column=0, sticky="w")

        self.ahk_toggle_box = tk.Label(
            outer,
            text="AHK macros",
            relief="solid",
            borderwidth=1,
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=6,
            anchor="center",
        )
        self.ahk_toggle_box.grid(row=0, column=1, sticky="e", padx=(12, 0))
        self.ahk_toggle_box.bind("<Button-1>", lambda _event: self.toggle_ahk_panel())

        notebook = ttk.Notebook(outer)
        notebook.grid(row=1, column=0, sticky="nsew", pady=(10, 0))

        functions_tab = ttk.Frame(notebook, padding=12)
        themes_tab = ttk.Frame(notebook, padding=12)
        notebook.add(functions_tab, text="Functions")
        notebook.add(themes_tab, text="Themes")

        functions_tab.columnconfigure(0, weight=1)
        functions_tab.columnconfigure(1, weight=1)
        functions_tab.columnconfigure(2, weight=1)
        functions_tab.rowconfigure(7, weight=1)
        themes_tab.columnconfigure(0, weight=1)

        self.state_box = tk.Label(
            functions_tab,
            text="OFF",
            relief="solid",
            borderwidth=1,
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=8,
            anchor="center",
        )
        self.state_box.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=(0, 10))

        self.roblox_only_box = tk.Label(
            functions_tab,
            text="Roblox only: ON",
            relief="solid",
            borderwidth=1,
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=8,
            anchor="center",
        )
        self.roblox_only_box.grid(row=0, column=1, sticky="ew", padx=6, pady=(0, 10))
        self.roblox_only_box.bind("<Button-1>", lambda _event: self.toggle_roblox_only())

        self.keybind_box = tk.Label(
            functions_tab,
            text=f"Keybind: {self.keybind_name}",
            relief="solid",
            borderwidth=1,
            cursor="hand2",
            padx=12,
            pady=8,
            anchor="center",
        )
        self.keybind_box.grid(row=0, column=2, sticky="ew", padx=(6, 0), pady=(0, 10))
        self.keybind_box.bind("<Button-1>", lambda _event: self.start_keybind_capture("toggle"))

        self.mini_box = tk.Label(
            functions_tab,
            text="Minimize",
            relief="solid",
            borderwidth=1,
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=8,
            anchor="center",
        )
        self.mini_box.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(0, 10))
        self.mini_box.bind("<Button-1>", lambda _event: self.enter_mini_mode())

        self.mini_keybind_box = tk.Label(
            functions_tab,
            text=f"Mini keybind: {self.mini_keybind_name}",
            relief="solid",
            borderwidth=1,
            cursor="hand2",
            padx=12,
            pady=8,
            anchor="center",
        )
        self.mini_keybind_box.grid(row=1, column=1, columnspan=2, sticky="ew", padx=(6, 0), pady=(0, 10))
        self.mini_keybind_box.bind("<Button-1>", lambda _event: self.start_keybind_capture("mini"))

        ttk.Label(functions_tab, text="Clicks per second").grid(row=2, column=0, sticky="w")
        self.cps_label = ttk.Label(functions_tab, text=f"{self.cps.get()} CPS")
        self.cps_label.grid(row=2, column=2, sticky="e")
        cps_slider = ttk.Scale(
            functions_tab,
            from_=1,
            to=100,
            orient="horizontal",
            command=self.update_cps_from_slider,
        )
        cps_slider.set(self.cps.get())
        cps_slider.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(4, 12))

        self.make_checkbutton(functions_tab, "Left click", self.left_enabled).grid(
            row=4, column=0, sticky="w", pady=(0, 8)
        )
        self.make_checkbutton(functions_tab, "Right click", self.right_enabled).grid(
            row=4, column=1, sticky="w", pady=(0, 8)
        )

        self.make_checkbutton(
            functions_tab,
            "Shift lock check",
            self.require_shiftlock,
            "(Disables m2 autoclick when you are unshiftlocked)",
        ).grid(
            row=5, column=0, columnspan=3, sticky="w"
        )
        self.make_checkbutton(functions_tab, "Always on top", self.always_on_top).grid(
            row=6, column=0, columnspan=3, sticky="w", pady=(8, 0)
        )
        self.shift_label = ttk.Label(functions_tab, text="Shift lock: no Roblox focused", foreground="#6b7280")
        self.shift_label.grid(row=7, column=0, columnspan=3, sticky="w", pady=(8, 0))

        self.make_radiobutton(themes_tab, "Light", "light").grid(
            row=0, column=0, sticky="w", pady=2
        )
        self.make_radiobutton(themes_tab, "Dark", "dark").grid(
            row=1, column=0, sticky="w", pady=2
        )

        self.build_ahk_panel(outer)
        if not self.ahk_panel_visible:
            self.ahk_panel.grid_remove()
        self.refresh_ahk_list()

    def build_ahk_panel(self, parent):
        self.ahk_panel = ttk.Frame(parent, padding=12)
        self.ahk_panel.grid(row=1, column=1, sticky="nsew", padx=(12, 0), pady=(10, 0))
        self.ahk_panel.columnconfigure(0, weight=1)
        self.ahk_panel.rowconfigure(3, weight=1)

        self.ahk_title = ttk.Label(self.ahk_panel, text="AHK macros", font=("Segoe UI", 11, "bold"))
        self.ahk_title.grid(row=0, column=0, sticky="w")

        self.ahk_browse_box = tk.Label(
            self.ahk_panel,
            text="Browse folder",
            relief="solid",
            borderwidth=1,
            cursor="hand2",
            padx=10,
            pady=7,
            anchor="center",
        )
        self.ahk_browse_box.grid(row=1, column=0, sticky="ew", pady=(10, 6))
        self.ahk_browse_box.bind("<Button-1>", lambda _event: self.browse_ahk_folder())

        self.ahk_folder_label = ttk.Label(self.ahk_panel, text="", width=28)
        self.ahk_folder_label.grid(row=2, column=0, sticky="ew", pady=(0, 6))

        self.ahk_list_frame = tk.Frame(self.ahk_panel, borderwidth=1, relief="solid")
        self.ahk_list_frame.grid(row=3, column=0, sticky="nsew")
        self.ahk_list_frame.columnconfigure(0, weight=1)
        self.ahk_list_frame.rowconfigure(0, weight=1)

        self.ahk_list = tk.Listbox(
            self.ahk_list_frame,
            height=12,
            activestyle="none",
            exportselection=False,
            borderwidth=0,
            highlightthickness=0,
        )
        self.ahk_scrollbar = ttk.Scrollbar(self.ahk_list_frame, orient="vertical", command=self.ahk_list.yview)
        self.ahk_list.configure(yscrollcommand=self.ahk_scrollbar.set)
        self.ahk_list.grid(row=0, column=0, sticky="nsew")
        self.ahk_scrollbar.grid(row=0, column=1, sticky="ns")
        self.ahk_list.bind("<ButtonRelease-1>", self.toggle_ahk_from_click)
        self.ahk_list.bind("<Button-3>", self.show_ahk_menu)

        self.ahk_status_label = ttk.Label(self.ahk_panel, text="", width=28)
        self.ahk_status_label.grid(row=4, column=0, sticky="ew", pady=(8, 0))

        self.ahk_menu = tk.Menu(self.root, tearoff=0)
        self.ahk_menu.add_command(label="Favorite", command=self.toggle_selected_ahk_favorite)
        self.ahk_menu.add_command(label="Edit", command=self.edit_selected_ahk)
        self.ahk_menu.add_command(label="Refresh", command=self.refresh_selected_ahk)

    def make_checkbutton(self, parent, text, variable, note=None):
        row = tk.Frame(parent, cursor="hand2")
        indicator = tk.Canvas(row, width=12, height=12, highlightthickness=0, borderwidth=0, cursor="hand2")
        square = indicator.create_rectangle(1, 1, 11, 11, fill="#000000", outline="#4b5563")
        label = tk.Label(row, text=text, cursor="hand2", padx=6, pady=0, anchor="w")
        note_label = None

        indicator.grid(row=0, column=0, sticky="w")
        label.grid(row=0, column=1, sticky="w")
        if note:
            note_label = tk.Label(row, text=note, cursor="hand2", padx=4, pady=0, anchor="w")
            note_label.grid(row=0, column=2, sticky="w")

        item = {
            "row": row,
            "indicator": indicator,
            "square": square,
            "label": label,
            "note": note_label,
            "variable": variable,
        }

        def toggle(_event=None):
            variable.set(not variable.get())

        for widget in (row, indicator, label, note_label):
            if widget is None:
                continue
            widget.bind("<Button-1>", toggle)

        variable.trace_add("write", lambda *_args, item=item: self.update_custom_checkbutton(item))
        self.checkbuttons.append(item)
        self.update_custom_checkbutton(item)
        return row

    def update_custom_checkbutton(self, item):
        if item["variable"].get():
            fill = "#16a34a"
            outline = "#22c55e"
        else:
            fill = "#000000"
            outline = "#4b5563"

        item["indicator"].itemconfigure(item["square"], fill=fill, outline=outline)

    def make_radiobutton(self, parent, text, value):
        row = tk.Frame(parent, cursor="hand2")
        indicator = tk.Canvas(row, width=12, height=12, highlightthickness=0, borderwidth=0, cursor="hand2")
        square = indicator.create_rectangle(1, 1, 11, 11, fill="#000000", outline="#4b5563")
        label = tk.Label(row, text=text, cursor="hand2", padx=6, pady=0, anchor="w")

        indicator.grid(row=0, column=0, sticky="w")
        label.grid(row=0, column=1, sticky="w")

        item = {
            "row": row,
            "indicator": indicator,
            "square": square,
            "label": label,
            "value": value,
        }

        def select(_event=None):
            self.theme.set(value)
            self.apply_theme()

        for widget in (row, indicator, label):
            widget.bind("<Button-1>", select)

        self.theme_options.append(item)
        self.update_theme_option(item)
        return row

    def update_theme_option(self, item):
        if self.theme.get() == item["value"]:
            fill = "#16a34a"
            outline = "#22c55e"
        else:
            fill = "#000000"
            outline = "#4b5563"

        item["indicator"].itemconfigure(item["square"], fill=fill, outline=outline)

    def toggle_ahk_panel(self):
        self.ahk_panel_visible = not self.ahk_panel_visible
        if self.ahk_panel_visible:
            self.ahk_panel.grid()
            self.refresh_ahk_list()
        else:
            self.ahk_panel.grid_remove()
        self.save_settings()

    def browse_ahk_folder(self):
        initial = self.ahk_folder if os.path.isdir(self.ahk_folder) else os.path.expanduser("~")
        folder = filedialog.askdirectory(title="Select AHK folder", initialdir=initial)
        if folder:
            self.ahk_folder = folder
            self.refresh_ahk_list()
            self.save_settings()

    def format_ahk_folder(self):
        if not self.ahk_folder:
            return "No folder selected"
        folder = self.ahk_folder.rstrip("\\/")
        name = os.path.basename(folder) or folder
        if len(name) <= 28:
            return name
        return f"...{name[-25:]}"

    def format_ahk_name(self, path):
        name = os.path.basename(path)
        if name.lower().endswith(".ahk"):
            name = name[:-4]
        if path in self.ahk_favorites:
            return f"★ {name}"
        return name

    def ahk_sort_key(self, path):
        return (0 if path in self.ahk_favorites else 1, os.path.basename(path).casefold())

    def set_ahk_status(self, text):
        self.ahk_status_label.configure(text=text)

    def update_ahk_loaded_status(self):
        if not self.ahk_folder:
            self.set_ahk_status("Select a macro folder")
        elif not os.path.isdir(self.ahk_folder):
            self.set_ahk_status("Folder not found")
        elif not self.ahk_macros:
            self.set_ahk_status("No AHK files")
        else:
            self.set_ahk_status(f"{len(self.ahk_macros)} macro loaded")

    def refresh_ahk_list(self):
        self.ahk_folder_label.configure(text=self.format_ahk_folder())
        old_paths = set(self.ahk_macros)
        if self.ahk_folder and os.path.isdir(self.ahk_folder):
            try:
                files = [
                    os.path.join(self.ahk_folder, name)
                    for name in os.listdir(self.ahk_folder)
                    if name.lower().endswith(".ahk")
                ]
            except OSError:
                files = []
        else:
            files = []

        self.ahk_favorites.intersection_update(files)
        self.ahk_macros = sorted(files, key=self.ahk_sort_key)
        for path in old_paths - set(self.ahk_macros):
            self.stop_ahk_macro(path, silent=True, repaint=False)

        self.ahk_list.delete(0, "end")
        for path in self.ahk_macros:
            self.ahk_list.insert("end", self.format_ahk_name(path))

        self.update_ahk_loaded_status()
        self.update_ahk_list_colors()

    def selected_ahk_path(self):
        index = self._ahk_menu_index
        if index is None:
            selection = self.ahk_list.curselection()
            if not selection:
                return None
            index = selection[0]
        if index < 0 or index >= len(self.ahk_macros):
            return None
        return self.ahk_macros[index]

    def toggle_ahk_from_click(self, event):
        if not self.ahk_macros:
            return
        index = self.ahk_list.nearest(event.y)
        if index < 0 or index >= len(self.ahk_macros):
            return
        bounds = self.ahk_list.bbox(index)
        if bounds and not (bounds[1] <= event.y <= bounds[1] + bounds[3]):
            return
        self.ahk_list.selection_clear(0, "end")
        self.ahk_list.selection_set(index)
        self.ahk_list.activate(index)
        self.toggle_ahk_macro(self.ahk_macros[index])

    def show_ahk_menu(self, event):
        if not self.ahk_macros:
            return
        index = self.ahk_list.nearest(event.y)
        if index < 0 or index >= len(self.ahk_macros):
            return
        bounds = self.ahk_list.bbox(index)
        if bounds and not (bounds[1] <= event.y <= bounds[1] + bounds[3]):
            return
        self._ahk_menu_index = index
        self.ahk_list.selection_clear(0, "end")
        self.ahk_list.selection_set(index)
        self.ahk_list.activate(index)
        path = self.ahk_macros[index]
        if path in self.ahk_favorites:
            self.ahk_menu.entryconfigure(0, label="Unfavorite")
        else:
            self.ahk_menu.entryconfigure(0, label="Favorite")
        try:
            self.ahk_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.ahk_menu.grab_release()

    def toggle_selected_ahk_favorite(self):
        path = self.selected_ahk_path()
        self._ahk_menu_index = None
        if not path:
            return
        if path in self.ahk_favorites:
            self.ahk_favorites.remove(path)
        else:
            self.ahk_favorites.add(path)
        self.refresh_ahk_list()
        self.select_ahk_path(path)
        self.save_settings()

    def edit_selected_ahk(self):
        path = self.selected_ahk_path()
        self._ahk_menu_index = None
        if not path:
            return
        try:
            subprocess.Popen(["notepad.exe", path])
            self.update_ahk_loaded_status()
        except OSError:
            self.set_ahk_status("Could not open Notepad")

    def refresh_selected_ahk(self):
        path = self.selected_ahk_path()
        self._ahk_menu_index = None
        if not path:
            self.refresh_ahk_list()
            return
        was_running = self.is_ahk_running(path)
        if was_running:
            self.stop_ahk_macro(path, silent=True)
        self.refresh_ahk_list()
        if os.path.exists(path) and was_running:
            self.start_ahk_macro(path)
        elif os.path.exists(path):
            self.update_ahk_loaded_status()
        self.select_ahk_path(path)

    def select_ahk_path(self, path):
        if path not in self.ahk_macros:
            return
        index = self.ahk_macros.index(path)
        self.ahk_list.selection_clear(0, "end")
        self.ahk_list.selection_set(index)
        self.ahk_list.activate(index)
        self.ahk_list.see(index)

    def toggle_ahk_macro(self, path):
        if self.is_ahk_running(path):
            self.stop_ahk_macro(path)
        else:
            self.start_ahk_macro(path)
        self.update_ahk_list_colors()

    def start_ahk_macro(self, path):
        if self.is_ahk_running(path):
            return True
        info = SHELLEXECUTEINFO()
        info.cbSize = ctypes.sizeof(info)
        info.fMask = SEE_MASK_NOCLOSEPROCESS
        info.lpVerb = "open"
        info.lpFile = path
        info.lpDirectory = os.path.dirname(path)
        info.nShow = SW_SHOWNORMAL
        if not shell32.ShellExecuteExW(ctypes.byref(info)) or not info.hProcess:
            self.set_ahk_status("Could not start macro")
            return False
        self.ahk_processes[path] = info.hProcess
        self.update_ahk_loaded_status()
        self.update_ahk_list_colors()
        return True

    def stop_ahk_macro(self, path, silent=False, repaint=True):
        handle = self.ahk_processes.pop(path, None)
        if not handle:
            return
        kernel32.TerminateProcess(handle, 0)
        kernel32.CloseHandle(handle)
        if not silent:
            self.update_ahk_loaded_status()
        if repaint:
            self.update_ahk_list_colors()

    def is_ahk_running(self, path):
        handle = self.ahk_processes.get(path)
        if not handle:
            return False
        exit_code = ctypes.c_ulong()
        if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)) and exit_code.value == STILL_ACTIVE:
            return True
        kernel32.CloseHandle(handle)
        self.ahk_processes.pop(path, None)
        return False

    def update_ahk_list_colors(self):
        for index, path in enumerate(self.ahk_macros):
            if self.is_ahk_running(path):
                self.ahk_list.itemconfigure(
                    index,
                    background=self._list_active_background,
                    foreground="#ffffff" if self.theme.get() == "dark" else "#064e3b",
                    selectbackground=self._list_active_background,
                )
            else:
                foreground = self._list_favorite_foreground if path in self.ahk_favorites else self._list_foreground
                self.ahk_list.itemconfigure(
                    index,
                    background=self._list_background,
                    foreground=foreground,
                    selectbackground=self._list_select_background,
                )

    def clean_ahk_processes(self):
        before = set(self.ahk_processes)
        for path in list(self.ahk_processes):
            self.is_ahk_running(path)
        if before != set(self.ahk_processes):
            self.update_ahk_list_colors()

    def stop_all_ahk_macros(self):
        for path in list(self.ahk_processes):
            self.stop_ahk_macro(path, silent=True)

    def install_mouse_hook(self):
        self._physical_left_down = key_down(VK_LBUTTON)
        self._physical_right_down = key_down(VK_RBUTTON)

        def hook_proc(n_code, w_param, l_param):
            if n_code == HC_ACTION:
                info = ctypes.cast(l_param, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                if not info.flags & LLMHF_INJECTED:
                    if w_param == WM_LBUTTONDOWN:
                        self._physical_left_down = True
                    elif w_param == WM_LBUTTONUP:
                        self._physical_left_down = False
                    elif w_param == WM_RBUTTONDOWN:
                        self._physical_right_down = True
                    elif w_param == WM_RBUTTONUP:
                        self._physical_right_down = False
            return user32.CallNextHookEx(self._mouse_hook, n_code, w_param, l_param)

        self._mouse_hook_proc = HOOKPROC(hook_proc)
        module_handle = kernel32.GetModuleHandleW(None)
        self._mouse_hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self._mouse_hook_proc, module_handle, 0)

    def uninstall_mouse_hook(self):
        if self._mouse_hook:
            user32.UnhookWindowsHookEx(self._mouse_hook)
        self._mouse_hook = None
        self._mouse_hook_proc = None

    def mouse_button_down(self, button):
        if self._mouse_hook:
            if button == "left":
                return self._physical_left_down
            return self._physical_right_down
        if button == "left":
            return key_down(VK_LBUTTON)
        return key_down(VK_RBUTTON)

    def release_synthetic_button(self):
        with self._click_lock:
            if self._synthetic_button_down:
                release_button(self._synthetic_button_down)
                self._synthetic_button_down = None

    def start_click_worker(self):
        self._click_thread = threading.Thread(target=self.click_worker, daemon=True)
        self._click_thread.start()

    def stop_click_worker(self):
        self._click_thread_stop.set()
        thread = self._click_thread
        if thread and thread.is_alive():
            thread.join(timeout=0.25)
        self._click_thread = None

    def click_worker(self):
        next_click = time.perf_counter()
        last_button = None
        while not self._click_thread_stop.is_set():
            with self._click_lock:
                button = self._active_button
                cps = self._cps_value

            if not button:
                next_click = time.perf_counter()
                last_button = None
                self._click_thread_stop.wait(0.002)
                continue

            if button != last_button:
                next_click = time.perf_counter()
                last_button = button

            now = time.perf_counter()
            delay = next_click - now
            if delay > 0:
                self._click_thread_stop.wait(min(delay, 0.004))
                continue

            with self._click_lock:
                button = self._active_button
                if button:
                    if self.mouse_button_down(button):
                        click(button)
                        self._synthetic_button_down = None
                        self._last_click_time = time.monotonic()
                    else:
                        if self._synthetic_button_down:
                            release_button(self._synthetic_button_down)
                        self._active_button = None
                        self._synthetic_button_down = None

            interval = 1.0 / max(1, cps)
            next_click = time.perf_counter() + interval

    def load_settings(self):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as settings_file:
                settings = json.load(settings_file)
        except (OSError, json.JSONDecodeError):
            return

        self.left_enabled.set(bool(settings.get("left_enabled", self.left_enabled.get())))
        self.right_enabled.set(bool(settings.get("right_enabled", self.right_enabled.get())))
        self.require_shiftlock.set(bool(settings.get("require_shiftlock", self.require_shiftlock.get())))
        self.roblox_only.set(bool(settings.get("roblox_only", self.roblox_only.get())))
        self.always_on_top.set(bool(settings.get("always_on_top", self.always_on_top.get())))

        cps = settings.get("cps", self.cps.get())
        if isinstance(cps, int):
            self.cps.set(max(1, min(100, cps)))

        theme = settings.get("theme", self.theme.get())
        if theme in ("light", "dark"):
            self.theme.set(theme)

        keybind_vk = settings.get("keybind_vk", self.keybind_vk)
        if isinstance(keybind_vk, int) and keybind_vk in VK_NAMES:
            self.keybind_vk = keybind_vk
            self.keybind_name = VK_NAMES[keybind_vk]

        mini_keybind_vk = settings.get("mini_keybind_vk", self.mini_keybind_vk)
        if isinstance(mini_keybind_vk, int) and mini_keybind_vk in VK_NAMES:
            self.mini_keybind_vk = mini_keybind_vk
            self.mini_keybind_name = VK_NAMES[mini_keybind_vk]

        mini_x = settings.get("mini_x", self.mini_x)
        mini_y = settings.get("mini_y", self.mini_y)
        if isinstance(mini_x, int) and isinstance(mini_y, int):
            self.mini_x = max(0, mini_x)
            self.mini_y = max(0, mini_y)

        ahk_folder = settings.get("ahk_folder", self.ahk_folder)
        if isinstance(ahk_folder, str):
            self.ahk_folder = ahk_folder

        ahk_favorites = settings.get("ahk_favorites", [])
        if isinstance(ahk_favorites, list):
            self.ahk_favorites = {path for path in ahk_favorites if isinstance(path, str)}

        self.ahk_panel_visible = bool(settings.get("ahk_panel_visible", self.ahk_panel_visible))

    def add_setting_traces(self):
        for variable in (
            self.left_enabled,
            self.right_enabled,
            self.require_shiftlock,
            self.roblox_only,
            self.always_on_top,
            self.cps,
            self.theme,
        ):
            variable.trace_add("write", lambda *_args: self.on_setting_changed())

    def save_settings(self):
        settings = {
            "left_enabled": self.left_enabled.get(),
            "right_enabled": self.right_enabled.get(),
            "require_shiftlock": self.require_shiftlock.get(),
            "roblox_only": self.roblox_only.get(),
            "always_on_top": self.always_on_top.get(),
            "cps": self.cps.get(),
            "theme": self.theme.get(),
            "keybind_vk": self.keybind_vk,
            "mini_keybind_vk": self.mini_keybind_vk,
            "mini_x": self.mini_x,
            "mini_y": self.mini_y,
            "ahk_folder": self.ahk_folder,
            "ahk_favorites": sorted(self.ahk_favorites),
            "ahk_panel_visible": self.ahk_panel_visible,
        }

        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as settings_file:
                json.dump(settings, settings_file, indent=2)
        except OSError:
            pass

    def on_setting_changed(self):
        self._cps_value = max(1, min(100, int(self.cps.get())))
        self.apply_always_on_top()
        self.save_settings()

    def apply_always_on_top(self):
        self.root.attributes("-topmost", bool(self.always_on_top.get()))

    def set_shift_status(self, roblox_focused):
        if not self.require_shiftlock.get():
            text = "Shift lock check: disabled"
            color = "#6b7280"
        elif not roblox_focused:
            text = "Shift lock: no Roblox focused"
            color = "#6b7280"
        elif self.shiftlock_on.get():
            text = "Shift lock: ON"
            color = "#166534"
        else:
            text = "Shift lock: OFF"
            color = "#9a3412"
        self.shift_label.configure(text=text, foreground=color)

    def toggle_running(self):
        self.running.set(not self.running.get())
        if not self.running.get():
            self.set_active_button(None)
        self.update_status()

    def toggle_roblox_only(self):
        self.roblox_only.set(not self.roblox_only.get())
        self.update_roblox_only_status()

    def update_status(self):
        text, background = self.status_look()
        self.state_box.configure(text=text, background=background, foreground="#ffffff")
        if self._mini_tile:
            self._mini_tile.configure(text=text, background=background, foreground="#ffffff")

    def update_roblox_only_status(self):
        if self.roblox_only.get():
            text = "Roblox only: ON"
        else:
            text = "Roblox only: OFF"

        self.roblox_only_box.configure(
            text=text,
            background=self._box_background,
            foreground=self._foreground,
        )

    def status_look(self):
        if self.running.get():
            return "ON", "#16a34a"
        return "OFF", "#dc2626"

    def update_cps_from_slider(self, value):
        rounded = max(1, min(100, int(round(float(value)))))
        self.cps.set(rounded)
        self._cps_value = rounded
        self.cps_label.configure(text=f"{rounded} CPS")

    def enter_mini_mode(self):
        if self._mini_window and self._mini_window.winfo_exists():
            return

        text, background = self.status_look()
        self.root.withdraw()
        self._mini_window = tk.Toplevel(self.root)
        self._mini_window.overrideredirect(True)
        self._mini_window.attributes("-topmost", True)
        self._mini_window.geometry(f"96x44+{self.mini_x}+{self.mini_y}")
        self._mini_window.configure(background=background)

        self._mini_tile = tk.Label(
            self._mini_window,
            text=text,
            font=("Segoe UI", 12, "bold"),
            background=background,
            foreground="#ffffff",
            cursor="fleur",
            anchor="center",
        )
        self._mini_tile.pack(fill="both", expand=True)
        self._mini_tile.bind("<ButtonPress-1>", self.start_mini_drag)
        self._mini_tile.bind("<B1-Motion>", self.drag_mini_tile)
        self._mini_tile.bind("<ButtonRelease-1>", self.end_mini_drag)
        self._mini_tile.bind("<Button-3>", lambda _event: self.exit_mini_mode())
        self.update_status()

    def exit_mini_mode(self):
        if self._mini_window and self._mini_window.winfo_exists():
            geometry = self._mini_window.geometry()
            try:
                position = geometry.split("+", 1)[1]
                x_text, y_text = position.split("+", 1)
                self.mini_x = int(x_text)
                self.mini_y = int(y_text)
                self.save_settings()
            except (IndexError, ValueError):
                pass
            self._mini_window.destroy()

        self._mini_window = None
        self._mini_tile = None
        self.root.deiconify()
        self.apply_always_on_top()

    def toggle_mini_mode(self):
        if self._mini_window and self._mini_window.winfo_exists():
            self.exit_mini_mode()
        else:
            self.enter_mini_mode()

    def start_mini_drag(self, event):
        self._mini_drag = (event.x_root, event.y_root, self._mini_window.winfo_x(), self._mini_window.winfo_y())
        self._mini_moved = False

    def drag_mini_tile(self, event):
        if not self._mini_drag:
            return

        start_x, start_y, window_x, window_y = self._mini_drag
        new_x = window_x + event.x_root - start_x
        new_y = window_y + event.y_root - start_y
        self._mini_window.geometry(f"+{new_x}+{new_y}")
        self._mini_moved = True

    def end_mini_drag(self, _event):
        if self._mini_window and self._mini_window.winfo_exists():
            self.mini_x = self._mini_window.winfo_x()
            self.mini_y = self._mini_window.winfo_y()
            self.save_settings()
        self._mini_drag = None

    def start_keybind_capture(self, target):
        self._capture_target = target
        self._capture_armed = False
        if target == "mini":
            self.mini_keybind_box.configure(text="Press key/button...")
        else:
            self.keybind_box.configure(text="Press key/button...")

    def any_keybind_key_down(self):
        return any(key_down(vk) for vk in KEYBIND_VKS)

    def capture_keybind_if_ready(self):
        if self._capture_target is None:
            return False

        if not self._capture_armed:
            self._capture_armed = not self.any_keybind_key_down()
            return True

        for vk in KEYBIND_VKS:
            if key_down(vk):
                if self._capture_target == "mini":
                    self.mini_keybind_vk = vk
                    self.mini_keybind_name = VK_NAMES[vk]
                    self._last_mini_key = True
                    self.mini_keybind_box.configure(text=f"Mini keybind: {self.mini_keybind_name}")
                else:
                    self.keybind_vk = vk
                    self.keybind_name = VK_NAMES[vk]
                    self._last_toggle_key = True
                    self.keybind_box.configure(text=f"Keybind: {self.keybind_name}")

                self._capture_target = None
                self._capture_armed = False
                self.save_settings()
                return True

        return True

    def apply_theme(self):
        if self.theme.get() == "dark":
            background = "#1f2937"
            foreground = "#f9fafb"
            muted = "#9ca3af"
            tab_background = "#111827"
            box_background = "#111827"
            list_select_background = "#374151"
            list_active_background = "#065f46"
            list_favorite_foreground = "#facc15"
        else:
            background = "#f3f4f6"
            foreground = "#111827"
            muted = "#6b7280"
            tab_background = "#ffffff"
            box_background = "#ffffff"
            list_select_background = "#d1d5db"
            list_active_background = "#bbf7d0"
            list_favorite_foreground = "#ca8a04"

        self._foreground = foreground
        self._box_background = box_background
        self._list_background = tab_background
        self._list_foreground = foreground
        self._list_select_background = list_select_background
        self._list_active_background = list_active_background
        self._list_favorite_foreground = list_favorite_foreground
        self.root.configure(background=background)
        self.style.theme_use("default")
        self.style.configure(".", background=background, foreground=foreground, fieldbackground=tab_background)
        self.style.configure("TFrame", background=background)
        self.style.configure("TNotebook", background=background, borderwidth=0)
        self.style.configure("TNotebook.Tab", padding=(12, 5), background=tab_background, foreground=foreground)
        self.style.map("TNotebook.Tab", background=[("selected", background)])
        self.style.configure("TLabel", background=background, foreground=foreground)
        self.style.configure("TCheckbutton", background=background, foreground=foreground)
        self.ahk_toggle_box.configure(background=box_background, foreground=foreground)
        self.keybind_box.configure(background=box_background, foreground=foreground)
        self.mini_box.configure(background=box_background, foreground=foreground)
        self.mini_keybind_box.configure(background=box_background, foreground=foreground)
        self.ahk_browse_box.configure(background=box_background, foreground=foreground)
        self.ahk_list_frame.configure(background=tab_background)
        self.ahk_list.configure(
            background=tab_background,
            foreground=foreground,
            selectbackground=list_select_background,
            selectforeground=foreground,
        )
        self.ahk_menu.configure(background=tab_background, foreground=foreground, activebackground=list_select_background)
        for item in self.checkbuttons:
            item["row"].configure(background=background)
            item["indicator"].configure(background=background)
            item["label"].configure(background=background, foreground=foreground)
            if item["note"]:
                item["note"].configure(background=background, foreground=muted)
            self.update_custom_checkbutton(item)

        for item in self.theme_options:
            item["row"].configure(background=background)
            item["indicator"].configure(background=background)
            item["label"].configure(background=background, foreground=foreground)
            self.update_theme_option(item)

        self.update_status()
        self.update_roblox_only_status()
        self.update_ahk_list_colors()

    def update_shiftlock_state(self):
        hwnd = foreground_hwnd()
        focus_changed = hwnd != self._active_hwnd
        self._active_hwnd = hwnd
        roblox_focused = bool(hwnd and is_roblox_window(hwnd))
        now = time.monotonic()

        if not self.require_shiftlock.get():
            self._right_block_until_release = False
            self.shiftlock_on.set(False)
            self.set_shift_status(roblox_focused)
            return roblox_focused

        if not roblox_focused:
            self.shiftlock_on.set(False)
            self.set_shift_status(False)
            return False

        if focus_changed:
            self._centered_since_by_hwnd.pop(hwnd, None)
            self._off_center_since_by_hwnd.pop(hwnd, None)

        shift_pressed, self._last_shift_key = key_pressed(VK_SHIFT, self._last_shift_key)
        if shift_pressed:
            self._centered_since_by_hwnd.pop(hwnd, None)
            self._off_center_since_by_hwnd.pop(hwnd, None)
            if self._shiftlock_by_hwnd.get(hwnd, False):
                self._shift_unlock_until_by_hwnd[hwnd] = now + 0.45
                self._shift_verify_until_by_hwnd.pop(hwnd, None)
                if self.mouse_button_down("right"):
                    self._right_block_until_release = True
                    self._shiftlock_by_hwnd[hwnd] = False
                    self._shift_unlock_until_by_hwnd.pop(hwnd, None)
                    if self._active_button == "right":
                        self.set_active_button(None)
                    release_button("right")
                    self._synthetic_button_down = None
            else:
                self._shift_verify_until_by_hwnd[hwnd] = now + 0.25
                if self.mouse_button_down("right"):
                    self._right_block_until_release = True

        center_state = cursor_center_distance(hwnd)
        unlock_pending = now <= self._shift_unlock_until_by_hwnd.get(hwnd, 0)
        verifying_shift = now <= self._shift_verify_until_by_hwnd.get(hwnd, 0)
        can_check_center = center_state and (not self.mouse_button_down("right") or unlock_pending or verifying_shift)
        if can_check_center:
            distance, tolerance = center_state
            current = self._shiftlock_by_hwnd.get(hwnd, False)
            tightly_centered = distance <= max(8, tolerance * 0.5)
            far_from_center = distance > tolerance * 2

            if tightly_centered:
                self._off_center_since_by_hwnd.pop(hwnd, None)
                if unlock_pending:
                    self._centered_since_by_hwnd.pop(hwnd, None)
                if verifying_shift:
                    centered_since = self._centered_since_by_hwnd.setdefault(hwnd, now)
                    if not current and now - centered_since >= 0.06:
                        self._shiftlock_by_hwnd[hwnd] = True
                else:
                    self._centered_since_by_hwnd.pop(hwnd, None)
            elif far_from_center:
                self._centered_since_by_hwnd.pop(hwnd, None)
                off_center_since = self._off_center_since_by_hwnd.setdefault(hwnd, now)
                if current and unlock_pending and now - off_center_since >= 0.03:
                    self._shiftlock_by_hwnd[hwnd] = False
                    self._shift_unlock_until_by_hwnd.pop(hwnd, None)
                    if self.mouse_button_down("right"):
                        self._right_block_until_release = True
                        if self._active_button == "right":
                            self.set_active_button(None)
                elif current and now - off_center_since >= 0.12:
                    self._shiftlock_by_hwnd[hwnd] = False
                elif verifying_shift and not current and now - off_center_since >= 0.08:
                    self._shiftlock_by_hwnd[hwnd] = False
            else:
                self._centered_since_by_hwnd.pop(hwnd, None)
                self._off_center_since_by_hwnd.pop(hwnd, None)

            self._last_center_distance_by_hwnd[hwnd] = distance

        if now > self._shift_verify_until_by_hwnd.get(hwnd, 0):
            self._shift_verify_until_by_hwnd.pop(hwnd, None)
            if not self._shiftlock_by_hwnd.get(hwnd, False):
                self._centered_since_by_hwnd.pop(hwnd, None)

        if now > self._shift_unlock_until_by_hwnd.get(hwnd, 0):
            self._shift_unlock_until_by_hwnd.pop(hwnd, None)

        self.shiftlock_on.set(self._shiftlock_by_hwnd.get(hwnd, False))

        self.set_shift_status(roblox_focused)
        return roblox_focused

    def should_right_click(self, roblox_focused, right_down):
        if not self.right_enabled.get():
            return False
        if not right_down:
            return False
        if self.require_shiftlock.get() and self._right_block_until_release:
            return False
        if self.require_shiftlock.get() and roblox_focused and not self.shiftlock_on.get():
            return False
        return True

    def choose_active_button(self, left_ready, right_ready, prefer_right=False):
        if left_ready and right_ready:
            if prefer_right or self._right_press_sequence >= self._left_press_sequence:
                return "right"
            return "left"
        if right_ready:
            return "right"
        if left_ready:
            return "left"
        return None

    def set_active_button(self, button):
        with self._click_lock:
            if button != self._active_button:
                self.release_synthetic_button()
                self._active_button = button
                self._last_click_time = 0.0

    def _loop(self):
        now = time.monotonic()
        if now - self._last_macro_check >= 0.5:
            self._last_macro_check = now
            self.clean_ahk_processes()

        if not self.capture_keybind_if_ready():
            toggle_pressed, self._last_toggle_key = key_pressed(self.keybind_vk, self._last_toggle_key)
            if toggle_pressed:
                self.toggle_running()

            mini_pressed, self._last_mini_key = key_pressed(self.mini_keybind_vk, self._last_mini_key)
            if mini_pressed:
                self.toggle_mini_mode()

        self.update_status()
        focused = self.update_shiftlock_state()
        clicks_allowed = focused or not self.roblox_only.get()
        left_down = self.mouse_button_down("left")
        right_down = self.mouse_button_down("right")
        if not right_down:
            self._right_block_until_release = False
        left_pressed = left_down and not self._left_was_down
        right_pressed = right_down and not self._right_was_down
        self._left_was_down = left_down
        self._right_was_down = right_down

        if left_pressed:
            self._press_sequence += 1
            self._left_press_sequence = self._press_sequence
        if right_pressed:
            self._press_sequence += 1
            self._right_press_sequence = self._press_sequence

        if self.running.get() and clicks_allowed:
            left_ready = self.left_enabled.get() and left_down
            right_ready = self.should_right_click(focused, right_down)
            shiftlocked_priority = self.require_shiftlock.get() and focused and self.shiftlock_on.get()

            latest_right_blocked = (
                right_down
                and self._right_press_sequence > self._left_press_sequence
                and not right_ready
            )
            latest_left_blocked = (
                left_down
                and self._left_press_sequence > self._right_press_sequence
                and not left_ready
            )

            if latest_right_blocked or latest_left_blocked:
                self.set_active_button(None)
            else:
                if right_pressed and (not left_pressed or self._right_press_sequence >= self._left_press_sequence):
                    self.set_active_button("right" if right_ready else None)
                elif left_pressed:
                    if shiftlocked_priority and right_ready:
                        self.set_active_button("right")
                    else:
                        self.set_active_button("left" if left_ready else None)

                if self._active_button == "left" and not left_ready:
                    self.set_active_button(self.choose_active_button(left_ready, right_ready, shiftlocked_priority))
                elif self._active_button == "right" and not right_ready:
                    self.set_active_button(self.choose_active_button(left_ready, right_ready, shiftlocked_priority))
                elif self._active_button is None:
                    self.set_active_button(self.choose_active_button(left_ready, right_ready, shiftlocked_priority))
        else:
            self.set_active_button(None)

        self.root.after(5, self._loop)

    def close(self):
        self.stop_click_worker()
        self.set_active_button(None)
        self.release_synthetic_button()
        self.uninstall_mouse_hook()
        self.stop_all_ahk_macros()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = AutoClickerApp(root)
    root.mainloop()
