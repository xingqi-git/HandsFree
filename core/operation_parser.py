class OperationParser:
    def __init__(self):
        self.supported_ops = [
            "鼠标移动到", "点击", "输入", "按下", "抬起",
            "等待", "循环开始", "结束循环"
        ]

    def validate_line(self, line):
        return True, ""

    def parse_line(self, line):
        return None, {}