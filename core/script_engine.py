from PyQt6.QtCore import QThread, pyqtSignal
import pyautogui
import time
import re


class ScriptEngine(QThread):
    run_finished = pyqtSignal()
    run_error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.script_content = ""
        self.run_count = 0
        self._stop_flag = False
        # 存储每行的递增状态 {line_key: current_value}
        self._increment_states = {}
        # 指令正则匹配
        self.move_re = re.compile(r"鼠标移动到\((\d+),(\d+)\)")
        self.wait_re = re.compile(r"等待\((\d+)秒\)")
        self.input_re = re.compile(r"输入\((.*?)\)")
        self.key_re = re.compile(r"键盘按键\((.*?)\)")
        self.loop_start_re = re.compile(r"循环开始(\d+)\((\d+)次\)")
        self.loop_end_re = re.compile(r"结束循环(\d+)")
        # 递增模式正则：匹配数字{{+N}}格式
        self.increment_re = re.compile(r"(\d+)\{\{\+(\d+)\}\}")
        # 按键名称映射
        self.key_map = {
            "回车": "enter", "Tab": "tab", "Shift": "shift", "Alt": "alt",
            "Ctrl": "ctrl", "Backspace": "backspace", "Delete": "delete",
            "PageUp": "pageup", "PageDown": "pagedown", "PrtSc": "printscreen",
            "↑": "up", "↓": "down", "←": "left", "→": "right",
            "F1": "f1", "F2": "f2", "F3": "f3", "F4": "f4", "F5": "f5", "F6": "f6",
            "F7": "f7", "F8": "f8", "F9": "f9", "F10": "f10", "F11": "f11", "F12": "f12",
            "Home": "home", "End": "end", "Insert": "insert", "Esc": "esc",
            "空格": "space"
        }

    def set_script(self, content):
        self.script_content = content

    def set_run_count(self, count):
        self.run_count = count

    def stop(self):
        self._stop_flag = True

    def run(self):
        self._stop_flag = False
        try:
            lines = [line.strip() for line in self.script_content.splitlines() if line.strip()]
            if not lines:
                self.run_finished.emit()
                return

            total_run = self.run_count if self.run_count > 0 else float('inf')
            current_run = 0

            while current_run < total_run and not self._stop_flag:
                # 每次运行开始时，重置所有递增状态
                self._increment_states = {}
                self._execute_block(lines)
                current_run += 1

            if not self._stop_flag:
                self.run_finished.emit()

        except Exception as e:
            self.run_error.emit(str(e))

    def _execute_block(self, lines, start_idx=0):
        idx = start_idx
        line_count = len(lines)

        while idx < line_count and not self._stop_flag:
            line = lines[idx]

            # 鼠标移动
            move_match = self.move_re.match(line)
            if move_match:
                x, y = int(move_match.group(1)), int(move_match.group(2))
                pyautogui.moveTo(x, y, duration=0.2)
                idx += 1
                continue

            # 鼠标点击/按下/抬起
            if line == "左键点击":
                pyautogui.click()
                idx += 1
                continue
            if line == "右键点击":
                pyautogui.rightClick()
                idx += 1
                continue
            if line == "按下":
                pyautogui.mouseDown()
                idx += 1
                continue
            if line == "抬起":
                pyautogui.mouseUp()
                idx += 1
                continue

            # 等待
            wait_match = self.wait_re.match(line)
            if wait_match:
                seconds = int(wait_match.group(1))
                time.sleep(seconds)
                idx += 1
                continue

            # 输入（支持递增）
            input_match = self.input_re.match(line)
            if input_match:
                text = input_match.group(1)
                processed_text = self._process_increment(text, idx)
                pyautogui.typewrite(processed_text)
                idx += 1
                continue

            # 键盘按键
            key_match = self.key_re.match(line)
            if key_match:
                key_name = key_match.group(1)
                actual_key = self.key_map.get(key_name, key_name)
                pyautogui.press(actual_key)
                idx += 1
                continue

            # 循环处理（支持嵌套）
            loop_start_match = self.loop_start_re.match(line)
            if loop_start_match:
                loop_num = loop_start_match.group(1)
                loop_count = int(loop_start_match.group(2))
                end_idx = self._find_loop_end(lines, loop_num, idx + 1)
                if end_idx == -1:
                    raise Exception(f"未找到循环{loop_num}对应的结束循环")
                for _ in range(loop_count):
                    if self._stop_flag:
                        break
                    self._execute_block(lines, idx + 1)
                idx = end_idx + 1
                continue

            # 循环结束（退出当前块）
            if self.loop_end_re.match(line):
                idx += 1
                return idx

            raise Exception(f"未知指令：{line}")

        return idx

    def _process_increment(self, text, line_idx):
        """处理文本中的递增标记"""
        def replace_func(match):
            base_num = int(match.group(1))
            increment = int(match.group(2))
            # 使用行号和基础数字作为key来唯一标识每个递增位置
            key = f"{line_idx}_{base_num}_{increment}"
            
            if key not in self._increment_states:
                # 第一次执行，使用初始值
                self._increment_states[key] = base_num
            else:
                # 后续执行，递增
                self._increment_states[key] += increment
            
            return str(self._increment_states[key])
        
        return self.increment_re.sub(replace_func, text)

    def _find_loop_end(self, lines, loop_num, start_idx):
        stack = 1
        idx = start_idx
        while idx < len(lines):
            line = lines[idx]
            if self.loop_start_re.match(line) and self.loop_start_re.match(line).group(1) == loop_num:
                stack += 1
            elif self.loop_end_re.match(line) and self.loop_end_re.match(line).group(1) == loop_num:
                stack -= 1
                if stack == 0:
                    return idx
            idx += 1
        return -1
