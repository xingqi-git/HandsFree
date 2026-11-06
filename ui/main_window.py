from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QSplitter, 
                             QLabel, QMessageBox, QMenuBar, QDialog, 
                             QTextEdit, QPushButton, QVBoxLayout, QShortcut,
                             QKeySequenceEdit, QFormLayout, QDialogButtonBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QKeySequence
from .script_panel import ScriptPanel
from .edit_area import ScriptEditArea
from .operation_panel import OperationPanel
from .run_bar import RunBar
from core.script_engine import ScriptEngine
import os, json, sys, time, platform

# 平台判断
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"

# Windows API 常量（仅 Windows 使用）
if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes
    WM_HOTKEY = 0x0312

# 应用目录：打包后取可执行文件所在目录，源码运行为项目根目录，避免依赖当前工作目录
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCRIPTS_FILE = os.path.join(APP_DIR, "handsfree_scripts.json")
CONFIG_FILE = os.path.join(APP_DIR, "handsfree_config.json")


def _qt_key_to_vk(key):
    """Qt.Key 转换为 Windows 虚拟键码，无法识别返回 None"""
    if Qt.Key_F1 <= key <= Qt.Key_F24:
        return 0x70 + (key - Qt.Key_F1)
    special = {
        Qt.Key_Escape: 0x1B, Qt.Key_Tab: 0x09, Qt.Key_Backtab: 0x0A,
        Qt.Key_Backspace: 0x08, Qt.Key_Return: 0x0D, Qt.Key_Enter: 0x0D,
        Qt.Key_Space: 0x20, Qt.Key_Insert: 0x2D, Qt.Key_Delete: 0x2E,
        Qt.Key_Home: 0x24, Qt.Key_End: 0x23, Qt.Key_PageUp: 0x21,
        Qt.Key_PageDown: 0x22, Qt.Key_Left: 0x25, Qt.Key_Up: 0x26,
        Qt.Key_Right: 0x27, Qt.Key_Down: 0x28, Qt.Key_Print: 0x2A,
        Qt.Key_Pause: 0x13, Qt.Key_ScrollLock: 0x91,
    }
    if key in special:
        return special[key]
    # 字母 A-Z（0x41-0x5A）和数字 0-9（0x30-0x39）与 VK 码一致
    if Qt.Key_A <= key <= Qt.Key_Z or Qt.Key_0 <= key <= Qt.Key_9:
        return key
    return None


def _parse_hotkey(key_str):
    """把 Qt 风格按键字符串（如 'Ctrl+Q'）解析为 (虚拟键码, Windows修饰键)，无法识别时返回 (None, 0)"""
    seq = QKeySequence(key_str)
    if seq.count() == 0:
        return None, 0
    combo = seq[0]
    mod_mask = int(Qt.SHIFT | Qt.CTRL | Qt.ALT | Qt.META)
    key = combo & ~mod_mask
    mods = combo & mod_mask
    vk = _qt_key_to_vk(key)
    if vk is None:
        return None, 0
    win_mods = 0
    if mods & int(Qt.SHIFT):
        win_mods |= 0x0004  # MOD_SHIFT
    if mods & int(Qt.CTRL):
        win_mods |= 0x0002  # MOD_CONTROL
    if mods & int(Qt.ALT):
        win_mods |= 0x0001  # MOD_ALT
    if mods & int(Qt.META):
        win_mods |= 0x0008  # MOD_WIN
    return vk, win_mods


def _pynput_key(key_str):
    """把 Qt 风格按键字符串转换为 pynput 按键对象（仅单键，忽略修饰键），失败返回 None"""
    try:
        from pynput import keyboard
    except ImportError:
        return None
    token = QKeySequence(key_str).toString().split('+')[-1].lower()
    fkeys = {f"f{i}": getattr(keyboard.Key, f"f{i}") for i in range(1, 21)}
    named = {
        "esc": keyboard.Key.esc, "escape": keyboard.Key.esc,
        "enter": keyboard.Key.enter, "return": keyboard.Key.enter,
        "tab": keyboard.Key.tab, "space": keyboard.Key.space,
        "backspace": keyboard.Key.backspace, "delete": keyboard.Key.delete,
        "insert": keyboard.Key.insert, "home": keyboard.Key.home,
        "end": keyboard.Key.end, "pageup": keyboard.Key.page_up,
        "pagedown": keyboard.Key.page_down, "up": keyboard.Key.up,
        "down": keyboard.Key.down, "left": keyboard.Key.left,
        "right": keyboard.Key.right, "printscreen": keyboard.Key.print_screen,
        "pause": keyboard.Key.pause, "capslock": keyboard.Key.caps_lock,
    }
    if token in fkeys:
        return fkeys[token]
    if token in named:
        return named[token]
    if len(token) == 1:
        return keyboard.KeyCode.from_char(token)
    return None


def _load_hotkey_config():
    """从配置文件加载热键设置"""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        start = str(data.get("start_hotkey", "F10"))
        stop = str(data.get("stop_hotkey", "F9"))
        return start, stop
    except Exception:
        return "F10", "F9"


def _save_hotkey_config(start_key, stop_key):
    """保存热键设置到配置文件"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"start_hotkey": start_key, "stop_hotkey": stop_key},
                      f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存配置失败: {e}")


class HelpDialog(QDialog):
    """使用说明对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("使用说明")
        self.setMinimumSize(700, 600)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 创建文本编辑器用于显示帮助内容
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml(self.get_help_content())
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        close_btn.setFixedWidth(100)
        
        layout.addWidget(help_text)
        layout.addWidget(close_btn, 0, Qt.AlignCenter)
    
    def get_help_content(self):
        """获取帮助内容"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: "Microsoft YaHei", sans-serif; font-size: 14px; line-height: 1.6; }
                h1 { color: #2c3e50; font-size: 24px; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
                h2 { color: #34495e; font-size: 18px; margin-top: 20px; }
                h3 { color: #7f8c8d; font-size: 16px; margin-top: 15px; }
                .code { background-color: #f8f9fa; padding: 2px 8px; border-radius: 4px; font-family: Consolas, monospace; }
                .hotkey { background-color: #e3f2fd; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
                ul { margin: 8px 0; padding-left: 20px; }
                li { margin: 5px 0; }
                .warning { color: #e74c3c; font-weight: bold; }
                .note { color: #f39c12; font-style: italic; }
            </style>
        </head>
        <body>
            <h1>🛠️ HandsFree 使用说明</h1>
            
            <h2>📋 软件简介</h2>
            <p>HandsFree 是一款自动化脚本执行工具，类似"按键精灵"，可以帮助您自动执行重复的鼠标和键盘操作，提高工作效率。</p>
            
            <h2>📝 界面布局</h2>
            <p>软件界面分为三个主要区域：</p>
            <ul>
                <li><strong>左侧 - 脚本列表</strong>：管理您的所有自动化脚本</li>
                <li><strong>中间 - 脚本编辑区</strong>：编写和编辑脚本内容</li>
                <li><strong>右侧 - 操作面板</strong>：快速插入常用操作命令</li>
                <li><strong>底部 - 运行控制栏</strong>：设置运行次数，控制脚本启停</li>
            </ul>
            
            <h2>📁 脚本管理</h2>
            
            <h3>创建新脚本</h3>
            <ul>
                <li>点击左侧脚本列表下方的 <span class="code">+</span> 按钮</li>
                <li>输入脚本名称（如"自动签到"、"重复点击"等）</li>
                <li>点击确定后，新脚本会出现在列表中</li>
            </ul>
            
            <h3>重命名脚本</h3>
            <ul>
                <li>双击脚本名称进入编辑状态</li>
                <li>输入新名称</li>
                <li>按回车键确认或点击其他位置取消</li>
            </ul>
            
            <h3>删除脚本</h3>
            <ul>
                <li>选中要删除的脚本</li>
                <li>点击 <span class="code">-</span> 按钮</li>
                <li>在确认对话框中点击"是"</li>
            </ul>
            
            <h3>切换脚本</h3>
            <ul>
                <li>点击列表中的脚本名称即可切换</li>
                <li>编辑内容会自动保存</li>
            </ul>
            
            <h2>✏️ 脚本编辑</h2>
            
            <h3>脚本语法</h3>
            <p>每行一条命令，支持以下命令：</p>
            <ul>
                <li><span class="code">等待(1.5秒)</span> - 等待指定时间（支持小数）</li>
                <li><span class="code">鼠标移动到(100,200)</span> - 移动鼠标到指定坐标</li>
                <li><span class="code">左键点击</span> - 单击鼠标左键</li>
                <li><span class="code">鼠标双击</span> - 双击鼠标左键</li>
                <li><span class="code">右键点击</span> - 单击鼠标右键</li>
                <li><span class="code">输入(文本)</span> - 输入指定文本（支持中文，支持 <span class="code">数字{{+N}}</span> 递增）</li>
                <li><span class="code">键盘按下(键名)</span> - 按下键盘按键</li>
                <li><span class="code">键盘抬起(键名)</span> - 松开键盘按键</li>
                <li><span class="code">键盘按键(键名)</span> - 按一下键盘按键（按下并松开）</li>
                <li><span class="code">循环开始1(10次)</span> ... <span class="code">结束循环1</span> - 循环执行（支持嵌套）</li>
            </ul>
            
            <h3>示例脚本</h3>
            <pre style="background-color: #f8f9fa; padding: 10px; border-radius: 4px;">
等待(1.5秒)
鼠标移动到(100,200)
左键点击
等待(0.5秒)
输入(Hello, World!)
键盘按下(ctrl)
键盘按键(s)
键盘抬起(ctrl)
            </pre>
            
            <h3>注释</h3>
            <p>以 <span class="code">#</span> 开头的行将被视为注释，不会执行。</p>
            
            <h2>🎮 操作面板</h2>
            
            <h3>快速插入操作</h3>
            <p>点击右侧操作面板中的按钮，可以快速插入常用操作命令：</p>
            <ul>
                <li><strong>等待</strong> - 插入等待命令</li>
                <li><strong>鼠标移动</strong> - 获取鼠标坐标并插入</li>
                <li><strong>鼠标左键点击</strong> - 插入左键点击命令</li>
                <li><strong>鼠标左键双击</strong> - 插入双击命令</li>
                <li><strong>鼠标右键点击</strong> - 插入右键点击命令</li>
                <li><strong>键盘输入</strong> - 插入文本输入命令</li>
                <li><strong>键盘按下/松开</strong> - 插入键盘按键操作</li>
            </ul>
            
            <h3>获取鼠标坐标</h3>
            <p>点击"鼠标移动"按钮后：</p>
            <ul>
                <li>屏幕会显示十字准线</li>
                <li>移动鼠标到目标位置</li>
                <li>点击鼠标左键确认坐标</li>
                <li>按鼠标右键或 ESC 键取消</li>
            </ul>
            
            <h2>▶️ 运行控制</h2>
            
            <h3>设置运行次数</h3>
            <ul>
                <li>在底部运行栏的"运行次数"输入框中输入数字</li>
                <li>默认运行 1 次</li>
                <li>设置为 0 表示无限循环（需要手动停止）</li>
            </ul>
            
            <h3>开始运行</h3>
            <ul>
                <li>点击 <span class="code">开始运行</span> 按钮</li>
                <li>在确认对话框中点击"是"</li>
                <li>软件会自动最小化并开始执行脚本</li>
            </ul>
            
            <h3>停止运行</h3>
            <ul>
                <li>点击 <span class="code">停止运行</span> 按钮</li>
                <li>脚本会在当前循环执行完毕后停止</li>
            </ul>
            
            <h2>⌨️ 全局热键</h2>
            <p>即使窗口最小化也能使用热键控制（默认为 F10 / F9，可在 <span class="code">设置 → 快捷键设置</span> 中自定义）：</p>
            <ul>
                <li><span class="hotkey">开始热键</span> - 开始运行脚本</li>
                <li><span class="hotkey">停止热键</span> - 停止运行脚本</li>
            </ul>
            
            <p class="note">注意：如果热键被其他程序占用，会弹出提示窗口告知。</p>
            
            <h2>💾 数据保存</h2>
            <ul>
                <li>脚本数据自动保存在软件同级目录的 <span class="code">handsfree_scripts.json</span> 文件中</li>
                <li>关闭软件时自动保存</li>
                <li>重新打开软件时会自动加载之前的脚本</li>
            </ul>
            
            <h2>⚠️ 注意事项</h2>
            <ul>
                <li><span class="warning">运行脚本前请确保已检查停止条件！</span></li>
                <li>建议先用简单脚本测试，熟悉功能后再用于重要操作</li>
                <li>无限循环模式下请牢记 F9 停止热键</li>
                <li>脚本运行时不要手动操作鼠标键盘可能影响执行效果</li>
                <li>不同屏幕分辨率变化时，鼠标坐标可能需要重新获取</li>
            </ul>
            
            <h2>💡 使用技巧</h2>
            <ul>
                <li>录制重复操作时，建议在每个操作之间添加适当的等待时间</li>
                <li>对于需要精确点击的场景，建议移动鼠标后等待 0.5-1 秒再点击</li>
                <li>复杂操作可以拆分成多个脚本，分别测试通过后再合并</li>
                <li>使用注释记录脚本用途和注意事项</li>
            </ul>
            
            <h2>❓ 常见问题</h2>
            
            <h3>Q: 脚本运行时如何停止？</h3>
            <p>A: 点击停止按钮或按 F9 热键。脚本会在完成当前循环后停止。</p>
            
            <h3>Q: 鼠标坐标怎么获取？</h3>
            <p>A: 点击右侧操作面板的"鼠标移动"按钮，然后用鼠标点击目标位置即可。</p>
            
            <h3>Q: 支持哪些键盘按键？</h3>
            <p>A: 支持常用按键名称：ctrl, shift, alt, enter, space, tab, escape, 以及字母 a-z, 数字 0-9 等。</p>
            
            <h3>Q: 脚本保存在哪里？</h3>
            <p>A: 保存在软件同级目录的 handsfree_scripts.json 文件中，可以备份此文件。</p>
            
            <h3>Q: Linux 系统可以用吗？</h3>
            <p>A: 可以！HandsFree 支持 Windows 和 Linux 系统。</p>
            
            <hr>
            <p style="text-align: center; color: #7f8c8d; margin-top: 20px;">
                HandsFree v1.0<br>
                让双手解放出来，让效率提升起来！ 🚀
            </p>
        </body>
        </html>
        """


class GlobalHotkeyThread(QThread):
    """全局热键监听线程（跨平台），支持自定义按键"""
    start_pressed = pyqtSignal()
    stop_pressed = pyqtSignal()
    register_result = pyqtSignal(bool, bool)  # start_success, stop_success

    def __init__(self, start_key="F10", stop_key="F9", parent=None):
        super().__init__(parent)
        self.start_key = start_key
        self.stop_key = stop_key
        self._thread_id = None
        self._quit_requested = False

    def run(self):
        if IS_WINDOWS:
            self._run_windows()
        else:
            self._run_linux()

    def request_stop(self):
        """请求退出热键监听：置退出标志并投递 WM_QUIT"""
        if IS_WINDOWS:
            self._quit_requested = True
            if self._thread_id:
                WM_QUIT = 0x0012
                ctypes.windll.user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        else:
            listener = getattr(self, '_listener', None)
            if listener:
                listener.stop()

    def _run_windows(self):
        """Windows 平台：使用 ctypes + RegisterHotKey"""
        # 记录本线程 ID，供 request_stop() 投递 WM_QUIT
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()

        start_vk, start_mods = _parse_hotkey(self.start_key)
        stop_vk, stop_mods = _parse_hotkey(self.stop_key)

        start_success = bool(start_vk) and bool(
            ctypes.windll.user32.RegisterHotKey(None, 1, start_mods, start_vk))
        stop_success = bool(stop_vk) and bool(
            ctypes.windll.user32.RegisterHotKey(None, 2, stop_mods, stop_vk))

        self.register_result.emit(start_success, stop_success)

        try:
            msg = wintypes.MSG()
            PM_REMOVE = 0x0001
            # 用 PeekMessage + 短轮询代替阻塞式 GetMessageW：
            # 阻塞式 GetMessageW 被 WM_QUIT 唤醒的延迟不稳定（实测可达 0.5s+），
            # 轮询可保证退出延迟确定在 ~50ms 内
            while not self._quit_requested:
                while ctypes.windll.user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
                    if msg.message == WM_HOTKEY:
                        if msg.wParam == 1:
                            self.start_pressed.emit()
                        elif msg.wParam == 2:
                            self.stop_pressed.emit()
                    elif msg.message == WM_QUIT:
                        self._quit_requested = True
                        break
                    ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
                    ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))
                if self._quit_requested:
                    break
                time.sleep(0.05)
        finally:
            if start_success:
                ctypes.windll.user32.UnregisterHotKey(None, 1)
            if stop_success:
                ctypes.windll.user32.UnregisterHotKey(None, 2)
            self._thread_id = None

    def _run_linux(self):
        """Linux 平台：使用 pynput 监听全局快捷键"""
        try:
            from pynput import keyboard
        except ImportError:
            self.register_result.emit(False, False)
            return

        start_key = _pynput_key(self.start_key)
        stop_key = _pynput_key(self.stop_key)
        self.register_result.emit(start_key is not None, stop_key is not None)

        def on_press(key):
            try:
                if start_key is not None and key == start_key:
                    self.start_pressed.emit()
                elif stop_key is not None and key == stop_key:
                    self.stop_pressed.emit()
            except Exception:
                pass

        self._listener = keyboard.Listener(on_press=on_press)
        self._listener.start()
        self._listener.join()


class HotkeySettingsDialog(QDialog):
    """快捷键设置对话框"""
    def __init__(self, start_key, stop_key, parent=None):
        super().__init__(parent)
        self.setWindowTitle("快捷键设置")
        self.setFixedSize(380, 190)
        self.start_key = start_key
        self.stop_key = stop_key
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.start_edit = QKeySequenceEdit(QKeySequence(self.start_key))
        self.stop_edit = QKeySequenceEdit(QKeySequence(self.stop_key))
        form.addRow("开始运行热键:", self.start_edit)
        form.addRow("停止运行热键:", self.stop_edit)
        layout.addLayout(form)

        tip = QLabel("点击输入框后按下新按键即可录入，支持组合键（如 Ctrl+Q）")
        tip.setStyleSheet("color: #888888; font-size: 12px;")
        layout.addWidget(tip)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._on_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _on_accept(self):
        start = self.start_edit.keySequence().toString()
        stop = self.stop_edit.keySequence().toString()
        if not start or not stop:
            QMessageBox.warning(self, "警告", "开始/停止热键不能为空！")
            return
        if start == stop:
            QMessageBox.warning(self, "警告", "开始和停止热键不能相同！")
            return
        if _parse_hotkey(start)[0] is None or _parse_hotkey(stop)[0] is None:
            QMessageBox.warning(self, "警告",
                                "包含无法识别的按键！\n请使用字母、数字、F1~F12 或方向键等按键。")
            return
        self.start_key = start
        self.stop_key = stop
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HandsFree")
        self.setMinimumSize(500, 500)

        # 核心运行引擎
        self.script_engine = ScriptEngine()

        # 创建菜单栏
        self._create_menu_bar()

        # 中心布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # 标题栏
        title = QLabel("HandsFree")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        main_layout.addWidget(title)

        # 三栏分割器
        mid_splitter = QSplitter(Qt.Horizontal)
        mid_splitter.setHandleWidth(2)

        # 初始化三个核心面板
        self.script_panel = ScriptPanel()
        self.edit_area = ScriptEditArea()
        self.operation_panel = OperationPanel()

        mid_splitter.addWidget(self.script_panel)
        mid_splitter.addWidget(self.edit_area)
        mid_splitter.addWidget(self.operation_panel)
        mid_splitter.setStretchFactor(0, 2)
        mid_splitter.setStretchFactor(1, 3)
        mid_splitter.setStretchFactor(2, 1)
        main_layout.addWidget(mid_splitter, stretch=1)  # 设置拉伸因子

        # 底部运行栏
        self.run_bar = RunBar()
        main_layout.addWidget(self.run_bar)

        # 信号槽连接
        self._connect_signals()

        # 自动保存定时器（防抖）
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(1500)
        self._save_timer.timeout.connect(self._save_scripts)

        # 初始化热键
        self._init_shortcuts()

        self._load_scripts()
        # 无任何脚本时自动创建默认脚本，无需手动新建即可编写
        self.script_panel.ensure_default_script()

    def _create_menu_bar(self):
        """创建菜单栏"""
        menu_bar = self.menuBar()

        # 设置菜单
        settings_menu = menu_bar.addMenu("设置(&S)")
        hotkey_action = settings_menu.addAction("快捷键设置(&K)...")
        hotkey_action.triggered.connect(self._on_hotkey_settings)

        # 帮助菜单
        help_menu = menu_bar.addMenu("帮助(&H)")
        
        # 使用说明动作
        help_action = help_menu.addAction("使用说明(&U)")
        help_action.triggered.connect(self._show_help)
        
        # 添加分隔线
        help_menu.addSeparator()
        
        # 关于动作
        about_action = help_menu.addAction("关于(&A)")
        about_action.triggered.connect(self._show_about)

    def _show_help(self):
        """显示使用说明对话框"""
        dialog = HelpDialog(self)
        dialog.exec_()

    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于 HandsFree", 
            """<h3>HandsFree v1.0</h3>
            <p>自动化脚本执行工具</p>
            <p>让双手解放出来，让效率提升起来！</p>
            <p><br>支持平台：Windows / Linux</p>
            <p>开发：PyQt5 + pyautogui</p>""")

    def _connect_signals(self):
        # 脚本管理信号
        # self.script_panel.script_selected.connect(self.edit_area.load_script_content)
        self.script_panel.load_script.connect(self.edit_area.load_script_content)
        # 内容编辑：编辑区告诉面板更新数据
        self.edit_area.content_changed.connect(self.script_panel.update_current_script)
        # 操作插入信号
        self.operation_panel.operation_inserted.connect(self.edit_area.insert_operation_line)
        self.operation_panel.coordinate_picked.connect(self.edit_area.insert_mouse_move_line)
        # 运行控制信号
        self.run_bar.start_run.connect(self._start_script_run)
        self.run_bar.stop_run.connect(self._stop_script_run)
        # 引擎运行反馈
        self.script_engine.run_finished.connect(self._on_run_finished)
        self.script_engine.run_error.connect(self._on_run_error)
        # 自动保存：编辑区内容和脚本列表变化都触发防抖保存
        self.edit_area.content_changed.connect(self._schedule_auto_save)
        self.script_panel.scripts_changed.connect(self._schedule_auto_save)

    def _init_shortcuts(self):
        """初始化快捷键（窗口级 + 全局热键）"""
        # 从配置文件加载热键设置
        self.hotkey_start, self.hotkey_stop = _load_hotkey_config()

        # 窗口级快捷键：当窗口有焦点时生效
        self.start_shortcut = QShortcut(QKeySequence(self.hotkey_start), self)
        self.start_shortcut.activated.connect(lambda: self._start_script_run(self.run_bar.get_run_count()))

        self.stop_shortcut = QShortcut(QKeySequence(self.hotkey_stop), self)
        self.stop_shortcut.activated.connect(self._stop_script_run)

        # 全局热键线程（Windows / Linux）
        self._start_hotkey_thread()

    def _start_hotkey_thread(self):
        """创建并启动全局热键监听线程"""
        self.hotkey_thread = GlobalHotkeyThread(self.hotkey_start, self.hotkey_stop, self)
        self.hotkey_thread.start_pressed.connect(self._on_hotkey_start)
        self.hotkey_thread.stop_pressed.connect(self._stop_script_run)
        self.hotkey_thread.register_result.connect(self._on_hotkey_registered)
        self.hotkey_thread.start()

    def _on_hotkey_settings(self):
        """打开快捷键设置对话框"""
        dialog = HotkeySettingsDialog(self.hotkey_start, self.hotkey_stop, self)
        if dialog.exec_() != QDialog.Accepted:
            return
        self.hotkey_start = dialog.start_key
        self.hotkey_stop = dialog.stop_key
        _save_hotkey_config(self.hotkey_start, self.hotkey_stop)
        self._apply_hotkeys()

    def _apply_hotkeys(self):
        """应用新的快捷键设置：更新窗口级快捷键并重启全局热键线程"""
        self.start_shortcut.setKey(QKeySequence(self.hotkey_start))
        self.stop_shortcut.setKey(QKeySequence(self.hotkey_stop))
        self.run_bar.set_hotkey_hint(start_hotkey=self.hotkey_start, stop_hotkey=self.hotkey_stop)

        # 停止旧的热键监听线程
        if self.hotkey_thread.isRunning():
            self.hotkey_thread.request_stop()
            self.hotkey_thread.wait(2000)
            if self.hotkey_thread.isRunning():
                self.hotkey_thread.terminate()
                self.hotkey_thread.wait(1000)
        self._start_hotkey_thread()

    def _on_hotkey_registered(self, start_success, stop_success):
        """处理热键注册结果"""
        # 窗口级热键始终可用，先设置热键提示
        self.run_bar.set_hotkey_hint(start_hotkey=self.hotkey_start, stop_hotkey=self.hotkey_stop)

        failed_keys = []
        if not start_success:
            failed_keys.append(self.hotkey_start)
        if not stop_success:
            failed_keys.append(self.hotkey_stop)
        
        if failed_keys:
            # 全局热键注册失败，弹出提示（但窗口级热键仍可用）
            msg = QMessageBox(QMessageBox.Warning, "提示", 
                              "全局热键注册失败。\n\n热键仅在窗口有焦点时可用。",
                              QMessageBox.Ok, self)
            msg.setWindowFlags(msg.windowFlags() | Qt.WindowStaysOnTopHint)
            msg.exec_()

    def _on_hotkey_start(self):
        """全局热键触发开始运行"""
        # 直接触发运行栏的开始运行信号
        self.run_bar.start_run.emit(self.run_bar.get_run_count())

    def _start_script_run(self, run_count):
        # 防止重复启动：脚本引擎运行中时忽略再次开始的请求（如运行中误按 F10）
        if self.script_engine.isRunning():
            return
        script_content = self.edit_area.toPlainText().strip()
        if not script_content:
            msg = QMessageBox(QMessageBox.Warning, "警告", "脚本内容为空，无法运行！", QMessageBox.Ok, self)
            msg.setWindowFlags(msg.windowFlags() | Qt.WindowStaysOnTopHint)
            msg.exec_()
            return
        # 运行前静态检查，提前发现所有语法错误，避免执行中途才报错
        errors = self.script_engine.validate_script(script_content)
        if errors:
            detail = '\n'.join(errors[:8])
            if len(errors) > 8:
                detail += f"\n... 共 {len(errors)} 处问题"
            msg = QMessageBox(QMessageBox.Critical, "脚本检查未通过",
                              f"发现 {len(errors)} 处问题，请修正后再运行：\n\n{detail}",
                              QMessageBox.Ok, self)
            msg.setWindowFlags(msg.windowFlags() | Qt.WindowStaysOnTopHint)
            msg.exec_()
            return
        # 弹出确认提示框，询问是否执行脚本（置顶显示）
        msg_box = QMessageBox(QMessageBox.Question, "执行确认", 
                             "我已经检查了停止条件，确认要执行",
                             QMessageBox.Yes | QMessageBox.No, self)
        msg_box.setDefaultButton(QMessageBox.No)
        msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
        reply = msg_box.exec_()

        # 判断选择：只有点击"是"才继续执行
        if reply != QMessageBox.Yes:
            return

        self.run_bar.set_running_state(True)
        self.showMinimized()  # 运行开始时最小化窗口
        self.script_engine.set_script(script_content)
        self.script_engine.set_run_count(run_count)
        self.script_engine.start()

    def _stop_script_run(self):
        # 空闲状态下按停止热键不做任何事，避免多余的弹窗
        if not self.script_engine.isRunning():
            return
        self.script_engine.stop()
        self.run_bar.set_running_state(False)
        self.showNormal()  # 手动停止时恢复窗口
        self.activateWindow()  # 激活窗口到前端
        # 置顶显示手动停止提示
        msg = QMessageBox(QMessageBox.Information, "提示", "已手动停止脚本运行", QMessageBox.Ok, self)
        msg.setWindowFlags(msg.windowFlags() | Qt.WindowStaysOnTopHint)
        msg.exec_()

    def _on_run_finished(self):
        self.run_bar.set_running_state(False)
        self.showNormal()  # 运行完成时恢复窗口
        self.activateWindow()  # 激活窗口到前端
        # 置顶显示提示框
        msg = QMessageBox(QMessageBox.Information, "提示", "脚本运行完成！", QMessageBox.Ok, self)
        msg.setWindowFlags(msg.windowFlags() | Qt.WindowStaysOnTopHint)
        msg.exec_()

    def _on_run_error(self, error_msg):
        self.run_bar.set_running_state(False)
        self.showNormal()  # 运行出错时恢复窗口
        self.activateWindow()  # 激活窗口到前端
        # 置顶显示错误提示
        msg = QMessageBox(QMessageBox.Critical, "错误", f"脚本运行出错：{error_msg}", QMessageBox.Ok, self)
        msg.setWindowFlags(msg.windowFlags() | Qt.WindowStaysOnTopHint)
        msg.exec_()

    def _load_scripts(self):
        """从应用目录加载脚本"""
        if not os.path.exists(SCRIPTS_FILE):
            return
        try:
            with open(SCRIPTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            script_dict = data.get("scripts", {})
            script_counter = data.get("counter", 1)
            self.script_panel.load_scripts(script_dict, script_counter)
        except Exception as e:
            print(f"加载脚本失败: {e}")

    def _save_scripts(self):
        """保存脚本到应用目录"""
        script_dict, script_counter = self.script_panel.get_all_scripts()
        data = {
            "scripts": script_dict,
            "counter": script_counter
        }
        try:
            with open(SCRIPTS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存脚本失败: {e}")

    def _schedule_auto_save(self):
        """内容或脚本列表变化后防抖 1.5 秒自动保存，避免程序异常退出丢失内容"""
        self._save_timer.start()

    def closeEvent(self, event):
        """重写关闭事件，停止脚本引擎和热键线程并保存"""
        # 先停止并等待脚本引擎线程退出，避免 "QThread: Destroyed while thread is still running" 崩溃
        self.script_engine.stop()
        if self.script_engine.isRunning():
            self.script_engine.wait(3000)
        # 停止热键线程
        self.hotkey_thread.request_stop()
        self.hotkey_thread.wait(2000)
        if self.hotkey_thread.isRunning():
            self.hotkey_thread.terminate()
            self.hotkey_thread.wait(1000)
        self._save_scripts()
        event.accept()
