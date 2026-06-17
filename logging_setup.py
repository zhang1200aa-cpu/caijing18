"""
caijing18 日志配置模块
- 解决 Windows GBK 终端下 emoji 无法输出的问题
"""
import sys
import logging


class EncodingStreamHandler(logging.StreamHandler):
    """自定义 StreamHandler，强制使用 UTF-8 编码输出"""

    def __init__(self, stream=None):
        if stream is None:
            stream = sys.stdout
        super().__init__(stream)
        # 尝试将底层流包装为 UTF-8
        if hasattr(stream, 'buffer'):
            import io
            self.stream = io.TextIOWrapper(
                stream.buffer,
                encoding='utf-8',
                errors='replace',
                line_buffering=True
            )

    def emit(self, record):
        try:
            msg = self.format(record)
            self.stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


def setup_logging(level=logging.INFO):
    """配置日志（兼容 Windows GBK 终端）"""
    handler = EncodingStreamHandler(sys.stdout)
    handler.setLevel(level)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    # 清除已有 handler
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    return root_logger