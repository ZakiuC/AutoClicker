import sys
import os
import ctypes
import threading
import time
import configparser
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Controller as KeyboardController, Listener as KeyboardListener, Key, KeyCode

def print_instructions():
    print("【使用说明】")
    print("这是一个自动模拟鼠标和键盘操作的工具，主要用于辅助游戏操作。请在使用前了解以下操作指南：")
    print("\n操作步骤:")
    print("1. 进入游戏，确定目标位置。")
    print("2. 按 F8 开始定位目标位置。首次按下开始定位，定位完成后再次按 F8 保存位置。")
    print("3. 按 F6 设置按键按下时间（默认30ms）。")
    print("4. 按 F7 设置按键间隔时间（默认50ms）。注意：间隔越短，操作成功率越高。")
    print("5. 按 Q 切换操作模式：")
    print("   - 模式1：按 B 开始，移动鼠标或再按 B 停止，鼠标位置不锁定。")
    print("   - 模式2：按 B 开始，再按 B 停止，鼠标锁定在目标位置。")
    print("6. 按 ESC 退出程序。")
    print("\n注意事项:")
    print("- 短时间内输出大量按键信息可能会导致游戏崩溃，使用时请注意控制频率。")
    print("\n启动后，请确保游戏窗口是活跃的，以免影响操作效果。祝您游戏愉快！")

# 管理员提权
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    if is_admin():
        autoclicker = AutoClicker()
        autoclicker.run()
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
        self.mode = 1  # Initial mode 1
        self.config_manager = ConfigManager({
            'x': 1250,
            'y': 1030,
            'press_time': 30,
            'interval_time': 50
        })
        self.listener = None

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

    def toggle(self, key):
        if key == KeyCode(char='b'):
            if not self.running:
                self.running = True
                self.locked_position = self.mouse.position
                self.mouse.position = (self.config_manager.settings['x'], self.config_manager.settings['y'])
                threading.Thread(target=self.perform_actions).start()
                print("启动")
            else:
                self.running = False
                print("停止")

    def switch_mode(self, key):
        if key == KeyCode(char='q'):
            self.mode = 2 if self.mode == 1 else 1
            mode_name = "模式 1: 不锁定鼠标" if self.mode == 1 else "模式 2: 锁定鼠标"
            print(f"切换模式：{mode_name}")

    def on_press(self, key):
        if key == Key.esc:
            self.running = False
            if self.listener:
                self.listener.stop()
            print("退出...")
        elif key == KeyCode(char='b'):
            self.toggle(key)
        elif key == Key.f8:
            self.handle_positioning(key)
        elif key == KeyCode(char='q'):
            self.switch_mode(key)

    def run(self):  
        print_instructions()
        with KeyboardListener(on_press=self.on_press) as self.listener:
            self.listener.join()

if __name__ == '__main__':
    run_as_admin()
