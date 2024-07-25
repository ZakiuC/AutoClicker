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
    print("5. （在非运行状态时）按 Q 切换操作模式（默认为模式1）：")
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
        self.config_manager = ConfigManager({
            'x': 1250,
            'y': 1030,
            'press_time': 30,
            'interval_time': 50,
            'mode': 1  # 默认模式 1
        })
        self.mode = self.config_manager.settings.get('mode', 1)  # 从配置加载模式
        self.listener = None
        self.thread_active = False
        self.input_request = None

    def handle_time_settings(self, key):
        if self.running:
            print("请先停止当前操作再设置时间参数。")
            return

        if key == Key.f6:
            # 设置按键按下时间
            try:
                new_press_time = int(input("输入新的按键按下时间（毫秒,默认30ms): "))
                self.config_manager.update_config('press_time', new_press_time)
                print(f"按键按下时间设置为：{new_press_time}毫秒")
            except ValueError:
                print("无效输入，请输入一个整数值")
        elif key == Key.f7:
            # 设置按键间隔时间
            try:
                new_interval_time = int(input("输入新的按键间隔时间（毫秒,默认50ms): "))
                self.config_manager.update_config('interval_time', new_interval_time)
                print(f"按键间隔时间设置为：{new_interval_time}毫秒")
            except ValueError:
                print("无效输入，请输入一个整数值")

                
    def perform_actions(self):
        if self.mode == 1:
            self.initial_position = self.mouse.position
        while self.running:
            if self.mode == 1 and self.mouse.position != self.initial_position:
                self.running = False
                print("停止")
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
        self.thread_active = False  # 线程完成后，将标志设置为 False
        
    def toggle(self):
        if not self.running:
            if not self.thread_active:  # 检查是否有线程活动
                self.running = True
                self.locked_position = self.mouse.position
                self.mouse.position = (self.config_manager.settings['x'], self.config_manager.settings['y'])
                threading.Thread(target=self.perform_actions).start()
                self.thread_active = True  # 启动线程时，将标志设置为 True
                print("启动")
            else:
                print("已有一个操作正在执行，请稍后再试。")
        else:
            self.running = False
            print("停止")
        self.input_request = None

    def switch_mode(self):
        if not self.running:
            self.mode = 2 if self.mode == 1 else 1
            self.config_manager.update_config('mode', self.mode)  # 更新配置文件中的模式
            mode_name = "模式 1: 不锁定鼠标" if self.mode == 1 else "模式 2: 锁定鼠标"
            print(f"切换模式：{mode_name}")
        else:
            print("操作进行中，不能切换模式。请先停止当前操作。")
        self.input_request = None
    
    def handle_positioning(self):
        if not self.positioning:
            self.positioning = True
            self.locked_position = self.mouse.position  # 记录当前鼠标位置
            print("开始定位...")
        else:
            self.locked_position = self.mouse.position
            self.config_manager.update_config('x', self.locked_position[0])
            self.config_manager.update_config('y', self.locked_position[1])
            self.positioning = False
            print(f"定位保存: {self.locked_position}")
        self.input_request = None
    
    def handle_input(self, setting):
        if setting == 'press_time':
            new_press_time = int(input("输入新的按键按下时间（毫秒,默认30ms): "))
            self.config_manager.update_config('press_time', new_press_time)
            print(f"按键按下时间设置为：{new_press_time}毫秒")
        elif setting == 'interval_time':
            new_interval_time = int(input("输入新的按键间隔时间（毫秒,默认50ms): "))
            self.config_manager.update_config('interval_time', new_interval_time)
            print(f"按键间隔时间设置为：{new_interval_time}毫秒")
        self.input_request = None
               
    def on_press(self, key):
        if key == Key.esc:
            self.input_request = 'exit'
        elif key == Key.f6:
            self.input_request = 'press_time'
        elif key == Key.f7:
            self.input_request = 'interval_time'
        elif key == Key.f8:
            self.input_request = 'set_position'
        elif key == KeyCode(char='b'):
            self.input_request = 'toggle'
        elif key == KeyCode(char='q'):
            self.input_request = 'switch_mode'
        
    def run(self):
        print_instructions()
        self.listener = KeyboardListener(on_press=self.on_press)
        self.listener.start()
        while True:
            if self.input_request == 'press_time':
                self.handle_input('press_time')
            elif self.input_request == 'interval_time':
                self.handle_input('interval_time')
            elif self.input_request == 'set_position':
                self.handle_positioning()
            elif self.input_request == 'toggle':
                self.toggle()
            elif self.input_request == 'switch_mode':
                self.switch_mode()
            elif self.input_request == 'exit':
                break
            if(self.positioning):
                print("鼠标位置: ", self.mouse.position)
                time.sleep(0.3)
            else:
                time.sleep(0.1)

if __name__ == '__main__':
    run_as_admin()