# main.py
import os
import sys

# 强制pyqtgraph使用PySide6后端 (必须在导入pyqtgraph前设置)
os.environ['PYQTGRAPH_QT_LIB'] = 'PySide6'

from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt
from styles import EYE_FRIENDLY_DARK_STYLE
from main_window import UnifiedTool

def resource_path(relative_path):
    """获取资源文件的绝对路径，兼容 PyInstaller 打包后的临时目录"""
    base_path = getattr(sys, '_MEIPASS', os.path.abspath('.'))
    return os.path.join(base_path, relative_path)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet(EYE_FRIENDLY_DARK_STYLE)
    
    icon_path = resource_path('PCAssistant.ico')
    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)

    # 显示启动闪屏
    splash_pixmap = QPixmap(icon_path).scaled(256, 256, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    splash = QSplashScreen(splash_pixmap, Qt.WindowStaysOnTopHint)
    splash.show()
    splash.showMessage("正在加载核心组件...", Qt.AlignBottom | Qt.AlignCenter, Qt.white)
    app.processEvents()

    # 加载主窗体（这里是最耗时的构造）
    window = UnifiedTool()
    window.setWindowIcon(app_icon)
    
    # 界面准备好后，关闭闪屏并显示主窗口
    window.showMaximized()
    splash.finish(window)

    sys.exit(app.exec())
