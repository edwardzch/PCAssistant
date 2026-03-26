# styles.py

EYE_FRIENDLY_DARK_STYLE = """
QWidget { color: #E0E0E0; background-color: #1e1e2e; font-size: 10pt; font-family: 'Segoe UI', 'Microsoft YaHei'; }
QGroupBox { background-color: #1e1e2e; border: 1px solid #505355; border-radius: 5px; margin-top: 1ex; font-weight: bold; }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 5px; background-color: #1e1e2e; color: #89b4fa; }
QLineEdit, QTextEdit, QComboBox, QTextBrowser, QPlainTextEdit, QSpinBox { background-color: #313244; border: 1px solid #45475a; border-radius: 4px; padding: 4px; color: #E0E0E0; }
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QPlainTextEdit:focus, QSpinBox:focus { border: 1px solid #89b4fa; }
QPushButton { background-color: #45475a; border: 1px solid #505355; padding: 5px 10px; border-radius: 4px; font-weight: bold; }
QPushButton:hover { background-color: #585b70; } 
QPushButton:pressed { background-color: #313244; }
QPushButton:checked { background-color: #313244; border: 1px solid #89b4fa; }

/* 特殊按钮颜色 */
QPushButton#btn_connect_open { background-color: #a6e3a1; color: #1e1e2e; }
QPushButton#btn_disconnect_close { background-color: #f38ba8; color: #1e1e2e; }
QPushButton#btn_send { background-color: #89b4fa; color: #1e1e2e; }

QCheckBox { spacing: 5px; }
QCheckBox:disabled { color: #888888; }
QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #505355; border-radius: 3px; background-color: #313244; }
QCheckBox::indicator:checked { background-color: #89b4fa; border: 1px solid #89b4fa; }
QStatusBar { background-color: #313244; }
QMenu { background-color: #313244; border: 1px solid #505355; }
QMenu::item:selected { background-color: #585b70; }
QScrollArea { border: none; }
"""
