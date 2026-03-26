# workers.py
from PySide6.QtCore import QThread, Signal
import socket

class TcpReceiver(QThread):
    signal_data_received = Signal(bytes)
    signal_error = Signal(str)
    signal_disconnected = Signal()

    def __init__(self, socket_obj):
        super().__init__()
        self.sock = socket_obj
        self.is_running = True

    def run(self):
        buffer_size = 4096
        while self.is_running:
            try:
                data = self.sock.recv(buffer_size)
                if not data:
                    if self.is_running: self.signal_disconnected.emit()
                    break
                if self.is_running: self.signal_data_received.emit(data)
            except (OSError, ConnectionAbortedError, ConnectionResetError) as e:
                # 如果是主动停止，不抛出错误
                if not self.is_running: break
                else:
                    self.signal_error.emit(f"TCP异常: {str(e)}")
                    break
            except Exception as e:
                if self.is_running: self.signal_error.emit(f"TCP错误: {str(e)}")
                break

    def stop(self):
        self.is_running = False
