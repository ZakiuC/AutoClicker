import sys
import os
import ctypes
import threading
import time
import configparser
import tkinter as tk
from tkinter import simpledialog, messagebox
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Controller as KeyboardController, Listener as KeyboardListener, Key, KeyCode
import ctypes

instructions = (
            "【使用说明】\n"
            "这是一个自动模拟鼠标和键盘操作的工具，主要用于辅助游戏操作。请在使用前了解以下操作指南：\n\n"
            "操作步骤:\n"
            "1. 进入游戏，确定目标位置。\n"
            "2. 按 F8 开始定位目标位置。首次按下开始定位，定位完成后再次按 F8 保存位置。\n"
            "3. 按 F6 设置按键按下时间（默认30ms）。\n"
            "4. 按 F7 设置按键间隔时间（默认50ms）。注意：间隔越短，操作成功率越高。\n"
            "5. （在非运行状态时）按 Q 切换操作模式（默认为模式1）：\n"
            "   - 模式1：按 B 开始，移动鼠标或再按 B 停止，鼠标位置不锁定。\n"
            "   - 模式2：按 B 开始，再按 B 停止，鼠标锁定在目标位置。\n"
            "6. 按 ESC 退出程序。\n\n"
            "注意事项:\n"
            "- 短时间内输出大量按键信息可能会导致游戏崩溃，使用时请注意控制频率。\n"
            "启动后，请确保游戏窗口是活跃的，以免影响操作效果。祝您游戏愉快！"
        )

def print_instructions():
    print(instructions )


# 管理员提权
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    if is_admin():
        print_instructions()
        # 获取控制台窗口句柄
        kernel32 = ctypes.WinDLL('kernel32')
        user32 = ctypes.WinDLL('user32')
        hWnd = kernel32.GetConsoleWindow()
        # 如果窗口句柄存在，尝试隐藏窗口
        # if hWnd:
        #     user32.ShowWindow(hWnd, 0)  # 0 表示 SW_HIDE
        root = tk.Tk()
        app = AutoClickerApp(root)
        root.mainloop()
    else:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)

class ConfigManager:
    """
    配置管理
    """
    def __init__(self, default_settings):
        self.config_path = self.get_config_path()
        self.config = configparser.ConfigParser()
        self.default_settings = default_settings
        self.load_config()

    def get_config_path(self):
        """获取配置文件的路径，如果程序被打包为执行文件则放在执行文件同目录，否则放在脚本文件目录。"""
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(application_path, 'config.ini')

    def load_config(self):
        """加载配置文件，如果配置文件不存在则使用默认配置，并创建配置文件。"""
        if os.path.exists(self.config_path):
            self.config.read(self.config_path)
            self.settings = {k: int(v) for k, v in self.config['DEFAULT'].items()}
        else:
            self.settings = self.default_settings
            self.config['DEFAULT'] = {k: str(v) for k, v in self.settings.items()}
            with open(self.config_path, 'w') as configfile:
                self.config.write(configfile)

    def update_config(self, key, value):
        """更新配置文件中的设置项。"""
        self.settings[key] = value
        self.config['DEFAULT'][key] = str(value)
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)

class AutoClicker:
    def __init__(self):
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        self.running = False
        self.positioning = False
        self.locked_position = None
        self.config_manager = ConfigManager({
            'x': 1250,
            'y': 1030,
            'press_time': 30,
            'interval_time': 50,
            'mode': 1  # 默认模式 1
        })
        self.mode = self.config_manager.settings.get('mode', 1)  # 从配置加载模式
                
    def perform_actions(self):
        if self.mode == 1:
            self.initial_position = self.mouse.position
        while self.running:
            if self.mode == 1 and self.mouse.position != self.initial_position:
                self.running = False
                break
            self.mouse.click(Button.left, 1)
            keys = ['w', 'a', 's', 'd']
            for key in keys:
                self.keyboard.press(key)
                time.sleep(self.config_manager.settings['press_time'] / 1000)
                self.keyboard.release(key)
                time.sleep(self.config_manager.settings['interval_time'] / 1000)
            if self.mode == 2:
                self.mouse.position = (self.config_manager.settings['x'], self.config_manager.settings['y'])

    def toggle(self):
        if not self.running:
            self.running = True
            self.locked_position = self.mouse.position
            self.mouse.position = (self.config_manager.settings['x'], self.config_manager.settings['y'])
        else:
            self.running = False

    def switch_mode(self):
        if not self.running:
            self.mode = 2 if self.mode == 1 else 1
            self.config_manager.update_config('mode', self.mode)  # 更新配置文件中的模式
            return True
        else:
            return False

    def handle_positioning(self, x, y):
        self.config_manager.update_config('x', x)
        self.config_manager.update_config('y', y)
        self.locked_position = (x, y)

class AutoClickerApp:
    def __init__(self, master):
        self.master = master
        master.title("自动点击器")

        # 设置窗口的最小尺寸
        master.minsize(300, 200)

        # 初始化AutoClicker对象
        self.auto_clicker = AutoClicker()
        
        # 使用grid布局管理器
        self.status_label = tk.Label(master, text="就绪")
        self.status_label.grid(row=0, column=0, columnspan=2, padx=10, pady=10)
        
        self.start_button = tk.Button(master, text="开始", command=self.start_clicker)
        self.start_button.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        self.stop_button = tk.Button(master, text="停止", command=self.stop_clicker)
        self.stop_button.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        self.position_button = tk.Button(master, text="设置位置", command=self.set_position)
        self.position_button.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        
        self.position_button = tk.Button(master, text="设置时间", command=self.set_timer)
        self.position_button.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        
        self.mode_button = tk.Button(master, text="切换模式", command=self.switch_mode)
        self.mode_button.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.instructions_button = tk.Button(master, text="查看说明", command=self.show_instructions)
        self.instructions_button.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        
        # 使组件在水平方向上填充可用空间
        master.grid_columnconfigure(0, weight=1)
        master.grid_columnconfigure(1, weight=1)
        
        # 使标签在垂直方向上填充
        master.grid_rowconfigure(2, weight=1)

    def show_instructions(self):
        messagebox.showinfo("使用说明", instructions)
        
    def start_clicker(self):
        self.auto_clicker.running = True
        threading.Thread(target=self.auto_clicker.perform_actions).start()
        self.status_label.config(text="点击中...")

    def stop_clicker(self):
        self.auto_clicker.running = False
        self.status_label.config(text="已停止")
        
        
    def switch_mode(self):
        result = self.auto_clicker.switch_mode()
        if result:
            mode_name = "模式 1: 不锁定鼠标" if self.auto_clicker.mode == 1 else "模式 2: 锁定鼠标"
            print(f"切换模式：{mode_name}")
            self.status_label.config(text=f"当前 {mode_name}")
        else:
            print("操作进行中，不能切换模式。请先停止当前操作。") 
            self.status_label.config(text=f"操作进行中，不能切换模式 请先停止当前操作")

    def set_timer(self):
        x = simpledialog.askinteger("时间", "输入按键按下时间（默认30ms）")
        y = simpledialog.askinteger("时间", "输入按键间隔时间（默认50ms）")
        if x is not None and y is not None:
            self.auto_clicker.handle_positioning(x, y)
            self.status_label.config(text=f"时间已设置: 按键按下时间：{x}, 按键间隔时间：{y}")
            
    def set_position(self):
        x = simpledialog.askinteger("位置", "输入X坐标")
        y = simpledialog.askinteger("位置", "输入Y坐标")
        if x is not None and y is not None:
            self.auto_clicker.handle_positioning(x, y)
            self.status_label.config(text=f"位置已设置到: ({x}, {y})")
    

if __name__ == "__main__":
    run_as_admin()
