import sys
import os
import ctypes
import threading
import time
import configparser
import tkinter as tk
from tkinter import simpledialog, messagebox
from pynput.mouse import Button, Listener, Controller as MouseController
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
    print(instructions)

def resource_path(relative_path):
    """ 获取资源的绝对路径。用于访问包内资源。 """
    try:
        # 如果程序被打包，获取临时文件的路径
        base_path = sys._MEIPASS
    except Exception:
        # 如果程序没有被打包，使用普通的路径
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

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
        if hWnd:
            user32.ShowWindow(hWnd, 0)  # 0 表示 SW_HIDE
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
        self.listener = None
        self.thread_active = False
        self.input_request = None
               
    def perform_actions(self):
        """
        根据设置的模式执行自动化键盘和鼠标操作

        此方法在一个独立线程中运行，根据当前的模式（mode）进行不同的操作：
        - 在模式1中，如果鼠标移动则停止操作。
        - 在模式2中，鼠标将定期移动到指定的坐标。

        方法使用一个按键列表并循环发送按键事件。每个按键按下后释放，之间有设定的延迟。
        迭代器用于循环访问按键列表，一旦到达列表末尾，迭代器会重置。

        Attributes:
            mode (int): 当前的操作模式。
            running (bool): 控制操作执行的运行状态。

        Side Effects:
            会修改实例变量 `thread_active`，在操作结束时将其设置为 False。
        """
        if self.mode == 1:
            self.initial_position = self.mouse.position

        # 初始化按键迭代器
        keys = ['w', 's', 'a', 'd']
        key_iterator = iter(keys)

        while self.running:
            if self.mode == 1 and self.mouse.position != self.initial_position:
                self.running = False
                print("停止")
                break

            # self.mouse.click(Button.left, 1)  # 每次循环点击一次鼠标左键
            self.keyboard.press(" ")
            time.sleep(self.config_manager.settings['press_time'] / 1000)
            self.keyboard.release(" ")

            # 从迭代器获取按键，如果已经到达列表末尾，重置迭代器
            try:
                key = next(key_iterator)
            except StopIteration:
                key_iterator = iter(keys)
                key = next(key_iterator)

            self.keyboard.press(key)
            time.sleep(self.config_manager.settings['press_time'] / 1000)
            self.keyboard.release(key)
            time.sleep(self.config_manager.settings['interval_time'] / 1000)

            if self.mode == 2:
                self.mouse.position = (self.config_manager.settings['x'], self.config_manager.settings['y'])
        
        self.thread_active = False  # 线程完成后，将标志设置为 False     

    def toggle(self):
        """
        切换自动操作的执行状态

        此方法控制一个线程的启动和停止，用于执行预定义的鼠标动作。如果当前没有线程活动且实例未在运行，
        它会启动一个新线程来执行这些动作，并将运行状态设置为 True。如果实例已在运行，则停止当前操作。
        
        1. 当没有线程活动，且 `running` 为 False 时，保存当前鼠标位置，将鼠标移动到配置的位置，启动线程，
        并返回 1 表示启动成功。
        2. 如果已有线程在执行，则打印提示信息，并返回 -1 表示操作无法执行。
        3. 如果 `running` 为 True，表示已在执行中，则将其停止，并返回 0 表示成功停止。

        Returns:
            int: 根据操作结果返回不同的整数：
                - 1 表示操作成功启动。
                - -1 表示操作因为已有线程在运行而未能启动。
                - 0 表示操作已成功停止。
        """
        if not self.running:
            if not self.thread_active:  # 检查是否有线程活动
                self.running = True
                self.locked_position = self.mouse.position
                self.mouse.position = (self.config_manager.settings['x'], self.config_manager.settings['y'])
                threading.Thread(target=self.perform_actions).start()
                self.thread_active = True  # 启动线程时，将标志设置为 True
                self.input_request = None
                return 1
            else:
                self.input_request = None
                return -1
        else:
            self.running = False
            self.input_request = None
            return 0
        
    def switch_mode(self):
        """
        切换当前运行模式

        如果实例没有正在运行的操作，则根据当前模式切换到另一模式（从1切换到2或从2切换到1），
        并更新配置文件以反映这一变化。如果实例正在运行，不执行任何操作。

        Returns:
            bool: 如果成功切换模式，则返回 True；如果因为实例正在运行而不能切换模式，则返回 False。
        """
        if not self.running:
            self.mode = 2 if self.mode == 1 else 1
            self.config_manager.update_config('mode', self.mode)  # 更新配置文件中的模式
            self.input_request = None
            return True
        else:
            self.input_request = None
            return False
    
    def handle_positioning(self):
        """
        处理鼠标定位操作，启用或禁用定位模式，并在禁用时更新配置的坐标位置。

        如果定位模式未激活，则启动定位模式并记录当前鼠标位置。
        如果定位模式已激活，则将当前鼠标位置保存到配置中，并禁用定位模式。

        Returns:
            int or tuple: 如果启动定位模式，返回 1；如果停用定位模式并更新坐标，返回新坐标的元组。
        """
        if not self.positioning:
            self.positioning = True
            self.locked_position = self.mouse.position  # 记录当前鼠标位置
            self.input_request = None
            
            return 1
        else:
            self.locked_position = self.mouse.position
            self.config_manager.update_config('x', self.locked_position[0])
            self.config_manager.update_config('y', self.locked_position[1])
            self.positioning = False
            self.input_request = None
            
            return self.locked_position
        
        
    def handle_input(self, setting, value):
        """
        根据用户的输入更新配置设置。

        参数:
            setting (str): 要更新的配置名称（例如 'press_time' 或 'interval_time'）。
            value (int): 新的配置值。

        根据提供的设置名称，更新对应的配置值。如果设置名称有效且更新成功，则返回 True；如果设置名称无效，返回 False。

        Returns:
            bool: 更新成功则返回 True，否则返回 False。
        """
        if setting == 'press_time':
            self.config_manager.update_config('press_time', value)
            self.input_request = None
            return True
        elif setting == 'interval_time':
            self.config_manager.update_config('interval_time', value)
            self.input_request = None
            return True
        else:
            self.input_request = None
            return False

    def on_press(self, key):
        """
        键盘按键事件的处理函数。

        参数:
            key: 按下的键的对象。

        根据按下的特定键（如 F6, F7, F8 或 'b', 'q' 键），设置输入请求的类型，用于在主程序中处理特定操作。
        Esc 键用于退出程序，F6, F7, F8 分别用于设置 press_time, interval_time 和 set_position。
        'b' 键用于切换自动点击的运行状态，'q' 键用于切换操作模式。

        Effects:
            修改实例变量 `input_request` 来反映用户的意图，便于主程序进行相应操作。
        """
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

class AutoClickerApp:
    def __init__(self, master):
        self.master = master
        master.title("自动点击器")

        # 设置窗口的最小尺寸
        master.minsize(300, 200)

        # 设置窗口图标
        master.iconbitmap(resource_path('app_icon.ico')) 
    
        # 设置窗口始终置顶
        master.attributes('-topmost', True)
    
        # 初始化AutoClicker对象
        self.auto_clicker = AutoClicker()
        
        # 使用grid布局管理器
        self.status_label = tk.Label(master, text="就绪")
        self.status_label.grid(row=0, column=0, columnspan=2, padx=10, pady=10)
        
        self.position_button = tk.Button(master, text="设置位置", command=self.set_position)
        self.position_button.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        self.position_button = tk.Button(master, text="设置时间", command=self.set_timer)
        self.position_button.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        
        self.mode_button = tk.Button(master, text="切换模式", command=self.switch_mode)
        self.mode_button.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.instructions_button = tk.Button(master, text="查看说明", command=self.show_instructions)
        self.instructions_button.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        
        self.start_button = tk.Button(master, text="开始", command=self.toggle_clicker)
        self.start_button.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        
        # 使组件在水平方向上填充可用空间
        master.grid_columnconfigure(0, weight=1)
        master.grid_columnconfigure(1, weight=1)
        
        # 使标签在垂直方向上填充
        master.grid_rowconfigure(2, weight=1)
        
        self.inputing = False
        self.run()
    
    def run(self):
        """
        启动应用程序的主循环，处理键盘事件和自动点击状态。

        此方法监控键盘事件并根据自动点击器的输入请求进行操作。
        它还定期更新 GUI 的状态标签以显示当前的操作状态或鼠标位置。
        使用 Tkinter 的 after 方法来实现循环调用，确保 GUI 响应用户操作。
        """
        if self.auto_clicker.listener == None:
            self.auto_clicker.listener = KeyboardListener(on_press=self.auto_clicker.on_press)
            self.auto_clicker.listener.start()
            print("程序已启动\n\n")
        
        if self.auto_clicker.input_request == 'press_time':
            self.set_timer()
        elif self.auto_clicker.input_request == 'interval_time':
            self.set_timer()
        elif self.auto_clicker.input_request == 'set_position':
            self.set_position()
        elif self.auto_clicker.input_request == 'toggle':
            self.toggle_clicker()
        elif self.auto_clicker.input_request == 'switch_mode':
            self.switch_mode()
        elif self.auto_clicker.input_request == 'exit':
            self.exit_application()
        
        if(self.auto_clicker.running):
            self.start_button.config(text="停止")
        else:
            if(self.status_label['text'] == "点击中..."):
                self.status_label.config(text="已停止")
            self.start_button.config(text="开始")
            
        if(self.auto_clicker.positioning):
            x, y = self.auto_clicker.mouse.position
            self.status_label.config(text=f"当前鼠标位置: {x}, {y} | 按F8保存")
        self.master.after(100, self.run)

    def show_instructions(self):
        """
        显示应用程序的使用说明。

        使用一个消息框来显示预定义的使用说明文本。
        这可以帮助新用户了解如何使用这个自动点击器应用程序。
        """
        messagebox.showinfo("使用说明", instructions)
        print("已展开使用说明")
        
    def toggle_clicker(self):
        """
        切换自动点击器的运行状态。

        根据自动点击器的当前状态，启动或停止自动点击操作。
        更新 GUI 中的状态标签和按钮文本以反映当前操作状态。
        """
        if not self.auto_clicker.positioning:
            if not self.inputing:
                result = self.auto_clicker.toggle()
                if(result == 1):
                    self.status_label.config(text="点击中...")
                    self.start_button.config(text="停止")
                    print("开始点击")
                elif(result == -1):
                    self.status_label.config(text="已有一个操作正在执行，请稍后再试")
                    self.start_button.config(text="开始")
                    print("操作进行中，不能启动新的操作")
                elif(result == 0):
                    self.status_label.config(text="已停止")
                    self.start_button.config(text="开始")
                    print("停止点击")
            else:
                print("设置按键时间中，请勿启动点击")
        else:
            self.status_label.config(text="请先停止目标位置设置")
            print("请先停止目标位置设置")
        
    def switch_mode(self):
        """
        切换自动点击器的操作模式。

        如果自动点击器不在运行中，则可以切换操作模式。
        更新状态标签以显示当前的操作模式。
        如果尝试在点击器运行时切换模式，将显示错误信息。
        """
        if not self.auto_clicker.positioning:
            if not self.inputing:
                result = self.auto_clicker.switch_mode()
                if result:
                    mode_name = "模式 1: 不锁定鼠标" if self.auto_clicker.mode == 1 else "模式 2: 锁定鼠标"
                    self.status_label.config(text=f"当前 {mode_name}")
                    print(f"切换模式：{mode_name}")
                else:
                    self.status_label.config(text=f"操作进行中，不能切换模式 请先停止当前操作")
                    print("操作进行中，不能切换模式。请先停止当前操作。")
            else:
                print("设置按键时间中，请勿切换模式")
        else:
            self.status_label.config(text="请先停止目标位置设置")
            print("请先停止目标位置设置")

    def set_timer(self):
        """
        设置自动点击器的按键按下时间和间隔时间。

        通过对话框接受用户输入的时间设置。
        如果点击器未在运行，更新这些设置；否则，显示错误信息提示用户先停止点击器。
        """
        if not self.auto_clicker.positioning:
            if not self.auto_clicker.running:
                self.inputing = True
                x = simpledialog.askinteger("时间", "输入按键按下时间（默认30ms）")
                y = simpledialog.askinteger("时间", "输入按键间隔时间（默认50ms）")
                if x is not None and y is not None:
                    result = self.auto_clicker.handle_input('press_time', x)
                    if result is False:
                        self.status_label.config(text=f"按键按下时间未保存,未知错误")
                        print("按键按下时间未保存,未知错误")
                    result = self.auto_clicker.handle_input('interval_time', y)
                    if result is False:
                        self.status_label.config(text=f"按键间隔时间未保存,未知错误")
                        print("按键间隔时间未保存,未知错误")
                    
                    self.status_label.config(text=f"时间已设置: 按键按下时间：{x}, 按键间隔时间：{y}")
                    print("时间已设置")
            else:
                self.status_label.config(text=f"请先停止自动点击的运行")
                print("请先停止自动点击的运行")
        else:
            self.status_label.config(text="请先停止目标位置设置")
            print("请先停止目标位置设置")
            
    def set_position(self):
        """
        设置或保存自动点击器的点击位置。

        当点击器未运行时，用户可以设置或保存鼠标的点击位置。
        如果正在设置位置，更新状态标签以提示用户当前在设置位置；如果位置已保存，更新状态标签显示新位置。
        """
        if not self.auto_clicker.running:
            if not self.inputing:
                result = self.auto_clicker.handle_positioning()
                if(result == 1):
                    self.status_label.config(text=f"开始设置目标位置")
                    print("开始设置目标位置")
                else:
                    self.status_label.config(text=f"已保存鼠标位置: {result[0]}, {result[1]}")
                    print(f"已保存鼠标位置: {result[0]}, {result[1]}")
            else:
                print("设置按键时间中，请勿设置目标位置")
        else:
            self.status_label.config(text="请先停止自动点击的运行")
            print("请先停止自动点击的运行")
    
    def exit_application(self):
        """
        安全退出应用程序。

        停止监听键盘事件并关闭应用程序。
        这个方法确保在退出前正确地释放资源，如停止键盘监听器。
        """
        print("退出程序...")
        if self.auto_clicker.listener.is_alive():
            self.auto_clicker.listener.stop()  # 停止监听器
        self.master.quit()  # 停止Tkinter主事件循环

if __name__ == "__main__":
    run_as_admin()
