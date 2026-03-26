# main_window.py
import socket
import datetime
import pyqtgraph as pg

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QGroupBox, QLabel, QComboBox, QPushButton,
    QTextBrowser, QLineEdit, QCheckBox, QMessageBox,
    QStatusBar, QStackedWidget, QRadioButton,
    QScrollArea, QFrame, QPlainTextEdit, QSpinBox
)
from PySide6.QtCore import QIODevice, QTimer, QDateTime, Qt, Signal, QEvent, QMimeData, QPoint
from PySide6.QtGui import QIntValidator, QTextCursor, QDrag

# 导入拆分后的模块
from styles import EYE_FRIENDLY_DARK_STYLE
from utils import Checksums
from workers import TcpReceiver
from translations import tr

try:
    from PySide6.QtSerialPort import QSerialPort, QSerialPortInfo
except ImportError:
    # 极少数情况下的兼容处理
    from PySide6.QtSerialPortBus import QSerialPort, QSerialPortInfo


# 自定义ComboBox用于刷新串口
class PortInfoComboBox(QComboBox):
    popup_about_to_show = Signal()

    def showPopup(self): self.popup_about_to_show.emit(); super().showPopup()


class UnifiedTool(QMainWindow):
    # 定义自定义信号用于线程安全日志
    sig_log_msg = Signal(str, str)  # text, tag

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Unified Serial/TCP Assistant V2.1")
        self.resize(1100, 850)

        # --- 核心变量 ---
        self.current_mode = "SERIAL"  # "SERIAL" or "TCP"
        self.current_lang = "zh"  # "zh" or "en"

        # 串口对象
        self.serial = QSerialPort(self)
        self.serial.readyRead.connect(self.on_serial_ready_read)

        # TCP 对象
        self.tcp_socket = None
        self.tcp_thread = None
        self.tcp_connected = False

        # 命令历史
        self.cmd_history = []
        self.history_pos = 0
        
        # 拖拽相关
        self.drag_start_pos = None
        self.drag_source_row = -1

        # 波形绘图数据
        self.is_waveform_paused = False
        self.plot_lines = []
        self.plot_data_y = [[] for _ in range(3)]
        self.plot_colors = ['#e57373', '#81c784', '#64b5f6']
        self.field_enable_checks, self.filter_header_checks, self.header_len_edits = [], [], []
        self.offset_edits, self.field_len_edits, self.endian_radios = [], [], []

        # 接收缓冲区(用于处理断包/粘包显示)
        self.rx_buffer = bytearray()
        self.rx_flush_timer = QTimer(self)
        self.rx_flush_timer.setSingleShot(True)
        self.rx_flush_timer.timeout.connect(self._flush_rx_buffer)

        # 脚本执行引擎
        self.script_timer = QTimer()
        self.script_timer.setSingleShot(True)
        self.script_timer.timeout.connect(self.execute_next_step)
        self.parsed_tasks = []
        self.current_step_index = 0
        self.current_loop_count = 0
        self.target_loop_count = 0
        self.loop_interval_ms = 1000
        self.running_tab_idx = -1

        # --- 初始化UI ---
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        self._create_left_panel()
        self._create_right_panel()  # 右侧现在是脚本区
        self._create_status_bar()

        # PyqtGraph 配置
        pg.setConfigOption('background', '#1e1e2e')
        pg.setConfigOption('foreground', '#D0D0D0')

        # 布局组合
        self.main_layout.addWidget(self.left_widget, 6)
        self.main_layout.addWidget(self.right_widget, 4)

        # 信号连接
        self._connect_signals()

        # 初始化状态
        self.refresh_ports()
        self.load_settings()
        self.update_ui_state()
        self.sig_log_msg.connect(self.log_msg_impl)
        
        # 初始化所有动态文本和启动说明
        self.apply_language()

    def _show_startup_guide(self):
        self.text_display.append(tr("startup_guide", self.current_lang))

    # ---------------- UI 构建区域 ----------------
    def _create_left_panel(self):
        self.left_widget = QWidget()
        layout = QVBoxLayout(self.left_widget)

        # 1. 顶部模式选择
        self.mode_group = QGroupBox("通讯模式")
        mode_layout = QHBoxLayout(self.mode_group)
        self.radio_serial = QRadioButton("串口 (Serial)")
        self.radio_tcp = QRadioButton("以太网 (TCP Client)")
        self.radio_serial.setChecked(True)
        self.radio_serial.toggled.connect(self.on_mode_changed)
        mode_layout.addWidget(self.radio_serial)
        mode_layout.addWidget(self.radio_tcp)
        mode_layout.addStretch()

        # 2. 动态配置区 (Stack)
        self.config_stack = QStackedWidget()
        self.config_stack.addWidget(self._create_serial_config_widget())  # Index 0
        self.config_stack.addWidget(self._create_tcp_config_widget())  # Index 1

        # 3. 接收设置区 (保留原串口工具的强大功能)
        self._create_receive_settings_group()

        # 4. 显示区域 (Stack: 文本/波形)
        self._create_display_stack()

        # 5. 底部快捷发送/波形解析配置
        self._create_bottom_control_panel()

        layout.addWidget(self.mode_group)
        layout.addWidget(self.config_stack)
        layout.addWidget(self.receive_settings_group)
        layout.addWidget(self.display_stack, 1)  # 伸缩因子1
        layout.addWidget(self.bottom_control_panel)
        layout.setContentsMargins(0, 0, 0, 0)

    def _create_serial_config_widget(self):
        self.serial_group = QGroupBox("串口设置")
        layout = QHBoxLayout(self.serial_group)

        self.port_combo = PortInfoComboBox()
        self.port_combo.popup_about_to_show.connect(self.refresh_ports)

        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200", "230400", "921600"])
        self.baud_combo.setCurrentText("115200")
        self.baud_combo.setEditable(True)
        self.baud_combo.setFixedWidth(100)

        # 简化其他参数，默认 8N1
        self.data_bits_combo = QComboBox();
        self.data_bits_combo.addItems(["8", "7"]);
        self.data_bits_combo.setFixedWidth(50)
        self.parity_combo = QComboBox();
        self.parity_combo.addItems(["None", "Even", "Odd"]);
        self.parity_combo.setFixedWidth(70)
        self.stop_bits_combo = QComboBox();
        self.stop_bits_combo.addItems(["1", "1.5", "2"]);
        self.stop_bits_combo.setFixedWidth(50)

        self.btn_open_serial = QPushButton("打开串口")
        self.btn_open_serial.setObjectName("btn_connect_open")

        self.lbl_port = QLabel("端口:")
        self.lbl_baud = QLabel("波特:")
        self.lbl_data = QLabel("数据:")
        self.lbl_parity = QLabel("校验:")
        self.lbl_stop = QLabel("停止:")

        layout.addWidget(self.lbl_port)
        layout.addWidget(self.port_combo)
        layout.addWidget(self.lbl_baud)
        layout.addWidget(self.baud_combo)
        layout.addWidget(self.lbl_data)
        layout.addWidget(self.data_bits_combo)
        layout.addWidget(self.lbl_parity)
        layout.addWidget(self.parity_combo)
        layout.addWidget(self.lbl_stop)
        layout.addWidget(self.stop_bits_combo)
        layout.addWidget(self.btn_open_serial)
        layout.addStretch()
        return self.serial_group

    def _create_tcp_config_widget(self):
        self.tcp_group = QGroupBox("TCP 设置")
        layout = QHBoxLayout(self.tcp_group)

        self.ip_input = QLineEdit("192.168.1.10")
        self.port_input = QLineEdit("502")
        self.port_input.setFixedWidth(80)

        self.btn_connect_tcp = QPushButton("连接")
        self.btn_connect_tcp.setObjectName("btn_connect_open")

        self.lbl_ip = QLabel("IP地址:")
        self.lbl_tcp_port = QLabel("端口:")

        layout.addWidget(self.lbl_ip)
        layout.addWidget(self.ip_input)
        layout.addWidget(self.lbl_tcp_port)
        layout.addWidget(self.port_input)
        layout.addWidget(self.btn_connect_tcp)
        layout.addStretch()
        return self.tcp_group

    def _create_receive_settings_group(self):
        self.receive_settings_group = QGroupBox("接收/显示 设置")
        layout = QHBoxLayout(self.receive_settings_group)
        self.btn_show_text = QPushButton("文本视图")
        self.btn_show_waveform = QPushButton("波形视图")
        self.btn_toggle_extension = QPushButton("脚本扩展 >>")
        self.btn_toggle_extension.setCheckable(True)
        self.btn_toggle_extension.setChecked(True)  # 默认展开

        self.receive_format_combo = QComboBox()
        self.receive_format_combo.addItems(["ASCII", "HEX", "UTF-8", "GB2312"])
        self.receive_format_combo.setCurrentText("ASCII")

        self.check_auto_scroll = QCheckBox("自动滚动");
        self.check_auto_scroll.setChecked(True)
        self.check_show_timestamp = QCheckBox("时间戳");
        self.check_show_timestamp.setChecked(True)
        self.btn_clear_receive = QPushButton("清空")

        self.btn_lang = QPushButton("English")
        self.btn_lang.setFixedWidth(70)
        self.btn_lang.clicked.connect(self.toggle_language)

        self.lbl_format = QLabel("格式:")

        layout.addWidget(self.btn_show_text)
        layout.addWidget(self.btn_show_waveform)
        layout.addWidget(self.btn_toggle_extension)
        layout.addStretch()
        layout.addWidget(self.lbl_format)
        layout.addWidget(self.receive_format_combo)
        layout.addWidget(self.check_auto_scroll)
        layout.addWidget(self.check_show_timestamp)
        layout.addWidget(self.btn_clear_receive)
        layout.addWidget(self.btn_lang)

    def _create_display_stack(self):
        self.display_stack = QStackedWidget()

        # 1. 文本显示
        self.text_display = QTextBrowser()
        self.text_display.setOpenExternalLinks(False)

        # 2. 波形显示
        self.waveform_plot_widget = pg.PlotWidget()
        self.waveform_plot_widget.addLegend()
        self.waveform_plot_widget.setBackground('#1e1e2e')
        self.waveform_plot_widget.showGrid(x=True, y=True, alpha=0.3)
        for i in range(3):
            line = self.waveform_plot_widget.plot(pen=pg.mkPen(self.plot_colors[i], width=2), name=f'Data {i + 1}')
            self.plot_lines.append(line)

        self.display_stack.addWidget(self.text_display)
        self.display_stack.addWidget(self.waveform_plot_widget)

    def _create_bottom_control_panel(self):
        self.bottom_control_panel = QWidget()
        layout = QVBoxLayout(self.bottom_control_panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # 移除单条发送区
        single_send_layout = QHBoxLayout()

        # 选项卡切换 (快捷发送 / 波形解析)
        tab_layout = QHBoxLayout()
        self.btn_tab_quick = QPushButton("快捷发送")
        self.btn_tab_wave = QPushButton("波形解析")
        for btn in [self.btn_tab_quick, self.btn_tab_wave]:
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton { border-radius: 0px; border-bottom: 2px solid #505355; background: transparent; } 
                QPushButton:checked { border-bottom: 2px solid #89b4fa; color: #89b4fa; }
            """)
        self.btn_tab_quick.setChecked(True)
        self.btn_tab_quick.clicked.connect(lambda: self.bottom_stack.setCurrentIndex(0) or self.update_tab_style(0))
        self.btn_tab_wave.clicked.connect(lambda: self.bottom_stack.setCurrentIndex(1) or self.update_tab_style(1))

        tab_layout.addWidget(self.btn_tab_quick)
        tab_layout.addWidget(self.btn_tab_wave)
        tab_layout.addStretch()

        self.bottom_stack = QStackedWidget()
        self.bottom_stack.addWidget(self._create_quick_send_group())
        self.bottom_stack.addWidget(self._create_waveform_config_group())

        layout.addLayout(single_send_layout)
        layout.addLayout(tab_layout)
        layout.addWidget(self.bottom_stack)

    def update_tab_style(self, idx):
        self.btn_tab_quick.setChecked(idx == 0)
        self.btn_tab_wave.setChecked(idx == 1)

    def _create_quick_send_group(self):
        # 快捷发送区
        group = QWidget()
        layout = QGridLayout(group)
        self.quick_inputs = []
        self.quick_hex_checks = []
        self.quick_nl_checks = []
        self.quick_timer_checks = []   # 定时发送复选框
        self.quick_timer_spins = []    # 定时间隔 (ms)
        self.quick_timers = []         # QTimer 实例
        self.quick_clear_checks = []   # 发后清空复选框
        self.quick_send_btns = []      # 发送按钮
        for i in range(3):
            line = QLineEdit()
            line.setPlaceholderText(f"快捷指令 {i + 1} (↑↓切换历史)")
            line.installEventFilter(self)
            line.setContextMenuPolicy(Qt.CustomContextMenu)
            line.customContextMenuRequested.connect(lambda pos, l=line: self.show_crc_menu(l, pos))
            line.returnPressed.connect(lambda _, x=i: self.send_quick(x))
            
            chk_hex = QCheckBox("Hex")
            chk_hex.toggled.connect(lambda checked, l=line: self.on_hex_toggled(l, checked))
            line.textEdited.connect(lambda text, l=line, h=chk_hex: self.on_line_text_edited(l, h))
            
            chk_nl = QCheckBox(r"\r\n")
            chk_nl.setChecked(True)
            
            btn = QPushButton(f"发送 {i + 1}")
            btn.clicked.connect(lambda _, x=i: self.send_quick(x))
            self.quick_send_btns.append(btn)

            # 定时发送: 复选框 + 间隔输入框
            chk_timer = QCheckBox("定时")
            spin_timer = QSpinBox()
            spin_timer.setRange(10, 999999)
            spin_timer.setValue(1000)
            spin_timer.setSuffix(" ms")
            spin_timer.setFixedWidth(100)
            timer = QTimer(self)
            timer.timeout.connect(lambda x=i: self.send_quick(x))
            chk_timer.toggled.connect(lambda checked, x=i: self._toggle_quick_timer(x, checked))

            # 发后清空
            chk_clear = QCheckBox("发后清空")
            
            self.quick_inputs.append(line)
            self.quick_hex_checks.append(chk_hex)
            self.quick_nl_checks.append(chk_nl)
            self.quick_timer_checks.append(chk_timer)
            self.quick_timer_spins.append(spin_timer)
            self.quick_timers.append(timer)
            self.quick_clear_checks.append(chk_clear)
            
            layout.addWidget(line, i, 0)
            layout.addWidget(chk_hex, i, 1)
            layout.addWidget(chk_nl, i, 2)
            layout.addWidget(btn, i, 3)
            layout.addWidget(chk_timer, i, 4)
            layout.addWidget(spin_timer, i, 5)
            layout.addWidget(chk_clear, i, 6)
        return group

    def _toggle_quick_timer(self, idx, checked):
        """切换定时发送开关"""
        if checked:
            interval = self.quick_timer_spins[idx].value()
            self.quick_timers[idx].start(interval)
        else:
            self.quick_timers[idx].stop()

    def _create_waveform_config_group(self):
        # 波形解析配置（保留原逻辑）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        layout = QHBoxLayout(content)

        self.wave_channel_groups = []
        self.wave_lbl_skip = []
        self.wave_lbl_offset = []
        self.wave_lbl_length = []

        for i in range(3):
            g = QGroupBox(f"通道 {i + 1}")
            self.wave_channel_groups.append(g)
            gl = QGridLayout(g)

            en = QCheckBox("启用");
            self.field_enable_checks.append(en)

            lbl_s = QLabel("跳过头:")
            self.wave_lbl_skip.append(lbl_s)
            hl_edit = QLineEdit("0");
            hl_edit.setValidator(QIntValidator(0, 255));
            self.header_len_edits.append(hl_edit)
            gl.addWidget(lbl_s, 0, 0);
            gl.addWidget(hl_edit, 0, 1)

            lbl_o = QLabel("偏移:")
            self.wave_lbl_offset.append(lbl_o)
            off_edit = QLineEdit("0");
            off_edit.setValidator(QIntValidator(0, 255));
            self.offset_edits.append(off_edit)
            gl.addWidget(lbl_o, 1, 0);
            gl.addWidget(off_edit, 1, 1)

            lbl_l = QLabel("长度:")
            self.wave_lbl_length.append(lbl_l)
            len_edit = QLineEdit("2");
            len_edit.setValidator(QIntValidator(1, 8));
            self.field_len_edits.append(len_edit)
            gl.addWidget(lbl_l, 2, 0);
            gl.addWidget(len_edit, 2, 1)

            big = QRadioButton("Big");
            small = QRadioButton("Little");
            small.setChecked(True)
            self.endian_radios.append((big, small))
            el = QHBoxLayout();
            el.addWidget(big);
            el.addWidget(small)

            gl.addWidget(en, 3, 0, 1, 2)
            gl.addLayout(el, 4, 0, 1, 2)

            self.filter_header_checks.append(QCheckBox())  # 占位，简化逻辑默认按长度截取
            layout.addWidget(g)

        btn_layout = QVBoxLayout()
        self.btn_pause_wave = QPushButton("暂停")
        self.btn_pause_wave.clicked.connect(self.toggle_waveform_pause)
        self.btn_clear_wave = QPushButton("清空")
        self.btn_clear_wave.clicked.connect(self.clear_waveform)
        btn_layout.addWidget(self.btn_pause_wave)
        btn_layout.addWidget(self.btn_clear_wave)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)
        scroll.setWidget(content)
        return scroll

    def _create_right_panel(self):
        # --- 右侧：脚本发送区 ---
        self.right_widget = QWidget()
        layout = QVBoxLayout(self.right_widget)

        self.script_group = QGroupBox("脚本循环任务 (Script Batch)")
        g_layout = QVBoxLayout(self.script_group)

        # Tab buttons
        tab_layout = QHBoxLayout()
        self.script_tab_btns = []
        for i in range(3):
            btn = QPushButton(f"Script {i+1}")
            btn.setCheckable(True)
            if i == 0: btn.setChecked(True)
            btn.clicked.connect(lambda checked, idx=i: self._switch_script_tab(idx))
            btn.installEventFilter(self)
            self.script_tab_btns.append(btn)
            tab_layout.addWidget(btn)
        g_layout.addLayout(tab_layout)

        self.script_stack = QStackedWidget()
        
        self.script_inputs = [[], [], []]
        self.script_hex_checks = [[], [], []]
        self.script_nl_checks = [[], [], []]
        self.script_comments = [[], [], []]
        
        self.spin_script_intervals = []
        self.spin_script_counts = []
        self.lbl_script_statuses = []
        self.btn_import_txts = []
        self.btn_start_scripts = []
        self.btn_stop_scripts = []
        self.btn_export_scripts = []
        self.script_scrolls = []
        self.lbl_select_alls = []
        self.lbl_intervals = []
        self.lbl_loop_counts = []
        self.script_send_btns = [[], [], []]

        default_script = [
 
        ]

        for tab_idx in range(3):
            page_widget = QWidget()
            page_layout = QVBoxLayout(page_widget)
            page_layout.setContentsMargins(0, 0, 0, 0)
            
            script_scroll = QScrollArea()
            script_scroll.setWidgetResizable(True)
            script_scroll.setFrameShape(QFrame.NoFrame)
            script_content = QWidget()
            script_layout = QVBoxLayout(script_content)
            script_layout.setContentsMargins(0, 0, 0, 0)
            script_layout.setSpacing(2)
            
            chk_all_layout = QHBoxLayout()
            chk_all_layout.setContentsMargins(0, 0, 0, 0)
            dummy_lbl = QLabel()
            dummy_lbl.setFixedWidth(20)
            chk_all_layout.addWidget(dummy_lbl)
            
            dummy_edit = QLineEdit()
            dummy_edit.setStyleSheet("background: transparent; border: none;")
            dummy_edit.setReadOnly(True)
            dummy_edit.setFocusPolicy(Qt.NoFocus)
            chk_all_layout.addWidget(dummy_edit)
            
            lbl_select_all = QLabel("全选")
            lbl_select_all.setAlignment(Qt.AlignCenter)
            lbl_select_all.setFixedWidth(64)
            self.lbl_select_alls.append(lbl_select_all)
            chk_all_layout.addWidget(lbl_select_all)
            
            chk_all_hex = QCheckBox("Hex")
            chk_all_hex.setChecked(False)
            chk_all_hex.setFixedWidth(64)
            chk_all_nl = QCheckBox(r"\r\n")
            chk_all_nl.setChecked(False)
            chk_all_nl.setFixedWidth(60)
            chk_all_hex.stateChanged.connect(lambda state, t_idx=tab_idx: self.toggle_all_hex(t_idx, state))
            chk_all_nl.stateChanged.connect(lambda state, t_idx=tab_idx: self.toggle_all_nl(t_idx, state))
            
            chk_all_layout.addWidget(chk_all_hex)
            chk_all_layout.addWidget(chk_all_nl)
            
            dummy_comment = QLabel()
            dummy_comment.setFixedWidth(104)
            chk_all_layout.addWidget(dummy_comment)
            script_layout.addLayout(chk_all_layout)
            
            for i in range(30):
                row_layout = QHBoxLayout()
                row_layout.setContentsMargins(0,0,0,0)
                
                lbl = QLabel(f"{i+1:02d}.")
                lbl.setFixedWidth(20)
                lbl.setCursor(Qt.OpenHandCursor)
                lbl.setProperty("row_idx", i)
                lbl.setProperty("tab_idx", tab_idx)
                lbl.installEventFilter(self)
                
                line_edit = QLineEdit()
                line_edit.setContextMenuPolicy(Qt.CustomContextMenu)
                line_edit.customContextMenuRequested.connect(lambda pos, l=line_edit, idx=i, t_idx=tab_idx: self.show_script_menu(l, idx, t_idx, pos))
                line_edit.installEventFilter(self)
                if tab_idx == 0 and i < len(default_script):
                    line_edit.setText(default_script[i])
                    
                chk_hex = QCheckBox("Hex")
                chk_hex.setChecked(True)
                chk_hex.setFixedWidth(60)
                chk_hex.toggled.connect(lambda checked, l=line_edit: self.on_hex_toggled(l, checked))
                line_edit.textEdited.connect(lambda text, l=line_edit, h=chk_hex: self.on_line_text_edited(l, h))
                
                chk_nl = QCheckBox(r"\r\n")
                chk_nl.setChecked(False)
                chk_nl.setFixedWidth(60)
                
                comment_edit = QLineEdit()
                comment_edit.setPlaceholderText("注释...")
                comment_edit.setFixedWidth(100)
                
                btn_send = QPushButton("发送")
                btn_send.setFixedWidth(60)
                btn_send.clicked.connect(lambda checked=False, r=i, t=tab_idx: self.send_script_row(t, r))
                self.script_send_btns[tab_idx].append(btn_send)
                
                row_layout.addWidget(lbl)
                row_layout.addWidget(line_edit)
                row_layout.addWidget(btn_send)
                row_layout.addWidget(chk_hex)
                row_layout.addWidget(chk_nl)
                row_layout.addWidget(comment_edit)
                
                row_widget = QWidget()
                row_widget.setLayout(row_layout)
                row_widget.setProperty("row_idx", i)
                row_widget.setProperty("tab_idx", tab_idx)
                row_widget.setAcceptDrops(True)
                row_widget.installEventFilter(self)
                
                self.script_inputs[tab_idx].append(line_edit)
                self.script_hex_checks[tab_idx].append(chk_hex)
                self.script_nl_checks[tab_idx].append(chk_nl)
                self.script_comments[tab_idx].append(comment_edit)
                script_layout.addWidget(row_widget)
                
            script_layout.addStretch()
            script_scroll.setWidget(script_content)
            self.script_scrolls.append(script_scroll)
            
            ctrl_layout = QGridLayout()
            spin_interval = QSpinBox()
            spin_interval.setRange(0, 3600000)
            spin_interval.setValue(1000)
            spin_count = QSpinBox()
            spin_count.setRange(0, 9999)
            spin_count.setValue(1)
            
            self.spin_script_intervals.append(spin_interval)
            self.spin_script_counts.append(spin_count)

            lbl_interval = QLabel("循环间隔(ms):")
            lbl_loop_count = QLabel("循环次数(0=∞):")
            self.lbl_intervals.append(lbl_interval)
            self.lbl_loop_counts.append(lbl_loop_count)

            ctrl_layout.addWidget(lbl_interval, 0, 0)
            ctrl_layout.addWidget(spin_interval, 0, 1)
            ctrl_layout.addWidget(lbl_loop_count, 1, 0)
            ctrl_layout.addWidget(spin_count, 1, 1)

            lbl_status = QLabel("就绪")
            lbl_status.setStyleSheet("color: #fab387")
            self.lbl_script_statuses.append(lbl_status)

            btn_box = QHBoxLayout()
            btn_import = QPushButton("导入 TXT")
            btn_import.clicked.connect(lambda checked=False, t_idx=tab_idx: self.import_script_from_txt(t_idx))
            self.btn_import_txts.append(btn_import)
            
            btn_export = QPushButton("导出 TXT")
            btn_export.clicked.connect(lambda checked=False, t_idx=tab_idx: self.export_script_to_txt(t_idx))
            self.btn_export_scripts.append(btn_export)
            
            btn_start = QPushButton("开始运行")
            btn_start.setObjectName("btn_connect_open")
            btn_start.clicked.connect(lambda checked=False, t_idx=tab_idx: self.start_script(t_idx))
            self.btn_start_scripts.append(btn_start)

            btn_stop = QPushButton("停止运行")
            btn_stop.setObjectName("btn_disconnect_close")
            btn_stop.setEnabled(False)
            btn_stop.clicked.connect(lambda checked=False, t_idx=tab_idx: self.stop_script(t_idx))
            self.btn_stop_scripts.append(btn_stop)

            btn_box.addWidget(btn_import)
            btn_box.addWidget(btn_export)
            btn_box.addWidget(btn_start)
            btn_box.addWidget(btn_stop)

            page_layout.addWidget(script_scroll)
            page_layout.addLayout(ctrl_layout)
            page_layout.addWidget(lbl_status)
            page_layout.addLayout(btn_box)
            
            self.script_stack.addWidget(page_widget)

        g_layout.addWidget(self.script_stack)
        layout.addWidget(self.script_group)

    def _switch_script_tab(self, idx):
        for i, btn in enumerate(self.script_tab_btns):
            btn.setChecked(i == idx)
        self.script_stack.setCurrentIndex(idx)

    def _start_inline_tab_rename(self, btn):
        """在按钮位置叠加一个 QLineEdit 进行内联编辑"""
        # 如果已有编辑框则先完成
        if hasattr(self, "_renaming_edit") and self._renaming_edit is not None:
            self._finish_inline_tab_rename()

        edit = QLineEdit(btn.parentWidget())
        edit.setText(btn.text())
        edit.setGeometry(btn.geometry())
        edit.setStyleSheet(
            "QLineEdit { background: #313244; color: #cdd6f4; border: 2px solid #89b4fa; "
            "border-radius: 4px; padding: 2px 4px; font-size: 13px; }"
        )
        edit.selectAll()
        edit.setFocus()
        edit.installEventFilter(self)
        edit.returnPressed.connect(self._finish_inline_tab_rename)
        edit.show()

        self._renaming_edit = edit
        self._renaming_btn = btn

    def _finish_inline_tab_rename(self):
        """完成内联编辑，将文本写回按钮"""
        if not hasattr(self, "_renaming_edit") or self._renaming_edit is None:
            return
        new_text = self._renaming_edit.text().strip()
        if new_text:
            self._renaming_btn.setText(new_text)
        self._renaming_edit.removeEventFilter(self)
        self._renaming_edit.deleteLater()
        self._renaming_edit = None
        self._renaming_btn = None

    def import_script_from_txt(self, tab_idx):
        from PySide6.QtWidgets import QFileDialog
        import os
        path, _ = QFileDialog.getOpenFileName(self, "选择TXT脚本", "", "Text Files (*.txt);;All Files (*)")
        if not path: return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except:
            try:
                with open(path, 'r', encoding='gbk') as f:
                    lines = f.readlines()
            except Exception as e:
                self.log_msg(f"导入脚本失败: {e}", "error")
                return
        
        lines = [l.strip() for l in lines]
        
        # 自动重命名 Tab
        base_name = os.path.basename(path)
        name_without_ext = os.path.splitext(base_name)[0]
        self.script_tab_btns[tab_idx].setText(name_without_ext)
        
        import re
        hex_pattern = re.compile(r'^([0-9A-Fa-f]{2}\s)*[0-9A-Fa-f]{2}$')

        for i in range(len(self.script_inputs[tab_idx])):
            if i < len(lines):
                line = lines[i]
                if ';' in line:
                    parts = line.split(';', 1)
                    cmd = parts[0].strip()
                    comment = parts[1].strip()
                else:
                    cmd = line.strip()
                    comment = ""
                self.script_inputs[tab_idx][i].setText(cmd)
                self.script_comments[tab_idx][i].setText(comment)

                # 自动检测 Hex：内容是否为空格分隔的十六进制字节对
                is_hex = bool(cmd) and bool(hex_pattern.match(cmd))
                self.script_hex_checks[tab_idx][i].setChecked(is_hex)

                # 自动检测换行符：非 Hex 的文本指令通常需要 \r\n
                self.script_nl_checks[tab_idx][i].setChecked(not is_hex and bool(cmd))
            else:
                self.script_inputs[tab_idx][i].clear()
                self.script_comments[tab_idx][i].clear()
                self.script_hex_checks[tab_idx][i].setChecked(False)
                self.script_nl_checks[tab_idx][i].setChecked(False)
        self.log_msg(tr("log_import_ok", self.current_lang, n=min(len(lines), len(self.script_inputs[tab_idx]))), "system")

    def export_script_to_txt(self, tab_idx):
        from PySide6.QtWidgets import QFileDialog
        import os
        default_name = f"{self.script_tab_btns[tab_idx].text()}.txt"
        path, _ = QFileDialog.getSaveFileName(self, tr("dialog_export_script_txt", self.current_lang), default_name, "Text Files (*.txt);;All Files (*)")
        if not path: return
        try:
            lines = []
            for i in range(len(self.script_inputs[tab_idx])):
                text = self.script_inputs[tab_idx][i].text().strip()
                comment = self.script_comments[tab_idx][i].text().strip()
                
                if text and comment:
                    lines.append(f"{text} ; {comment}")
                elif text:
                    lines.append(text)
                elif comment:
                    lines.append(f"; {comment}")
            with open(path, 'w', encoding='utf-8') as f:
                f.write("\n".join(lines) + "\n")
            self.log_msg(tr("log_export_ok", self.current_lang, n=len(lines), name=os.path.basename(path)), "success")
        except Exception as e:
            self.log_msg(tr("log_export_fail", self.current_lang, err=e), "error")

    def toggle_all_hex(self, tab_idx, state):
        for chk in self.script_hex_checks[tab_idx]:
            chk.setChecked(state != 0)

    def toggle_all_nl(self, tab_idx, state):
        for chk in self.script_nl_checks[tab_idx]:
            chk.setChecked(state != 0)

    def _create_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.lbl_status = QLabel("未连接")
        self.lbl_rx = QLabel("RX: 0")
        self.lbl_tx = QLabel("TX: 0")
        self.rx_cnt = 0
        self.tx_cnt = 0
        self.status_bar.addPermanentWidget(self.lbl_status)
        self.status_bar.addPermanentWidget(self.lbl_rx)
        self.status_bar.addPermanentWidget(self.lbl_tx)

    def _connect_signals(self):
        self.btn_open_serial.clicked.connect(self.toggle_serial)
        self.btn_connect_tcp.clicked.connect(self.toggle_tcp)

        self.btn_show_text.clicked.connect(lambda: self.display_stack.setCurrentIndex(0))
        self.btn_show_waveform.clicked.connect(lambda: self.display_stack.setCurrentIndex(1))
        self.btn_toggle_extension.clicked.connect(self.toggle_right_panel)
        self.btn_clear_receive.clicked.connect(self.clear_all)

    # ---------------- 逻辑控制区域 ----------------

    def on_mode_changed(self):
        # 切换模式时，如果处于连接状态，先断开
        if self.serial.isOpen(): self.toggle_serial()
        if self.tcp_connected: self.toggle_tcp()

        if self.radio_serial.isChecked():
            self.current_mode = "SERIAL"
            self.config_stack.setCurrentIndex(0)
        else:
            self.current_mode = "TCP"
            self.config_stack.setCurrentIndex(1)
        self.update_ui_state()

    def toggle_right_panel(self):
        L = self.current_lang
        if self.btn_toggle_extension.isChecked():
            self.right_widget.show()
            self.btn_toggle_extension.setText(tr("btn_extension_on", L))
        else:
            self.right_widget.hide()
            self.btn_toggle_extension.setText(tr("btn_extension_off", L))

    # --- 串口逻辑 (这里是核心修改点) ---
    def refresh_ports(self):
        self.port_combo.blockSignals(True)
        current = self.port_combo.currentData()
        self.port_combo.clear()
        for p in QSerialPortInfo.availablePorts():
            name = p.portName()
            desc = p.description()
            display = f"{name} - {desc}" if desc else name
            self.port_combo.addItem(display, name)
        
        # Try to restore selection
        idx = self.port_combo.findData(current)
        if idx >= 0:
            self.port_combo.setCurrentIndex(idx)
        self.port_combo.blockSignals(False)

    def toggle_serial(self):
        if self.serial.isOpen():
            self.stop_script()
            self.serial.close()
            self.rx_flush_timer.stop()
            self._flush_rx_buffer()
            self.log_msg(tr("log_serial_closed", self.current_lang), "system")
        else:
            name = self.port_combo.currentData()
            if not name:
                name = self.port_combo.currentText().split(" - ")[0]
            if not name: return

            try:
                self.serial.setPortName(name)
                self.serial.setBaudRate(int(self.baud_combo.currentText()))

                # === 修复点：PySide6 严格类型检查 ===
                # 数据位映射
                db_map = {
                    "8": QSerialPort.DataBits.Data8,
                    "7": QSerialPort.DataBits.Data7
                }
                self.serial.setDataBits(db_map[self.data_bits_combo.currentText()])

                # 校验位映射
                p_map = {
                    "None": QSerialPort.Parity.NoParity,
                    "Even": QSerialPort.Parity.EvenParity,
                    "Odd": QSerialPort.Parity.OddParity
                }
                self.serial.setParity(p_map[self.parity_combo.currentText()])

                # 停止位映射
                s_map = {
                    "1": QSerialPort.StopBits.OneStop,
                    "1.5": QSerialPort.StopBits.OneAndHalfStop,
                    "2": QSerialPort.StopBits.TwoStop
                }
                self.serial.setStopBits(s_map[self.stop_bits_combo.currentText()])

                if self.serial.open(QIODevice.ReadWrite):
                    self.log_msg(tr("log_serial_open_ok", self.current_lang, name=name), "success")
                else:
                    self.log_msg(tr("log_serial_open_fail", self.current_lang, err=self.serial.errorString()), "error")
            except Exception as e:
                self.log_msg(tr("log_config_err", self.current_lang, err=str(e)), "error")

        self.update_ui_state()

    def on_serial_ready_read(self):
        data = self.serial.readAll().data()
        self.process_received_data(data)

    # --- TCP 逻辑 ---
    def toggle_tcp(self):
        if self.tcp_connected:
            self.stop_script()
            self.disconnect_tcp()
        else:
            self.connect_tcp()

    def connect_tcp(self):
        ip = self.ip_input.text()
        try:
            port = int(self.port_input.text())
        except:
            self.log_msg(tr("log_port_err", self.current_lang), "error")
            return

        try:
            self.log_msg(tr("log_connecting", self.current_lang, addr=f"{ip}:{port}"), "system")
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.settimeout(2.0)
            self.tcp_socket.connect((ip, port))
            self.tcp_socket.settimeout(None)

            self.tcp_thread = TcpReceiver(self.tcp_socket)
            self.tcp_thread.signal_data_received.connect(self.process_received_data_threadsafe)
            self.tcp_thread.signal_error.connect(lambda e: self.log_msg(e, "error"))
            self.tcp_thread.signal_disconnected.connect(self.on_tcp_disconnected)
            self.tcp_thread.start()

            self.tcp_connected = True
            self.log_msg(tr("log_tcp_ok", self.current_lang), "success")
            self.update_ui_state()

        except Exception as e:
            self.log_msg(tr("log_connect_fail", self.current_lang, err=e), "error")
            if self.tcp_socket: self.tcp_socket.close()

    def disconnect_tcp(self):
        if self.tcp_thread: self.tcp_thread.stop()
        if self.tcp_socket:
            try:
                self.tcp_socket.shutdown(socket.SHUT_RDWR)
            except:
                pass
            self.tcp_socket.close()

        self.tcp_connected = False
        self.log_msg(tr("log_tcp_closed", self.current_lang), "system")
        self.update_ui_state()

    def on_tcp_disconnected(self):
        self.log_msg(tr("log_server_disconnected", self.current_lang), "error")
        self.disconnect_tcp()

    def process_received_data_threadsafe(self, data):
        # 供子线程调用
        self.process_received_data(data)

    # --- 通用接收处理 (核心) ---
    def process_received_data(self, data: bytes):
        if not data: return
        self.rx_cnt += len(data)
        self.lbl_rx.setText(f"RX: {self.rx_cnt}")

        # 1. 放入缓冲区
        self.rx_buffer.extend(data)

        # 2. 波形实时处理 (不等待换行)
        if self.display_stack.currentIndex() == 1 and not self.is_waveform_paused:
            self.parse_waveform(data)

        # 3. 文本显示 (处理换行粘包)
        while True:
            idx = self.rx_buffer.find(b'\n')
            if idx == -1: break
            line = self.rx_buffer[:idx + 1]
            del self.rx_buffer[:idx + 1]
            self._display_text(bytes(line), 'rx')

        # 4. 剩余数据延迟刷新
        if self.rx_buffer:
            self.rx_flush_timer.start(50)

    def _flush_rx_buffer(self):
        if self.rx_buffer:
            self._display_text(bytes(self.rx_buffer), 'rx')
            self.rx_buffer.clear()

    def _display_text(self, data: bytes, tag):
        # 解码
        fmt = self.receive_format_combo.currentText()
        text = ""
        if fmt == "HEX":
            # 如果结尾是换行，去掉再HEX显示，防止变成多余的 0A 0D
            d_view = data
            if d_view.endswith(b'\n'): d_view = d_view[:-1]
            if d_view.endswith(b'\r'): d_view = d_view[:-1]
            if not d_view: return  # 处理纯换行的空包
            text = " ".join([f"{b:02X}" for b in d_view])
        else:
            try:
                text = data.decode(fmt.lower(), errors='replace').strip()
            except:
                text = str(data)

        if not text: return
        self.log_msg(text, tag)

    def log_msg_impl(self, text, tag):
        # 实际操作UI的日志函数
        import html as html_lib
        safe_text = html_lib.escape(text)
        
        timestamp = QDateTime.currentDateTime().toString(
            "[HH:mm:ss.zzz]") if self.check_show_timestamp.isChecked() else ""
        c_map = {"tx": "#a6e3a1", "rx": "#89b4fa", "error": "#f38ba8", "success": "#a6e3a1", "system": "#fab387"}
        color = c_map.get(tag, "#E0E0E0")
        prefix = {"tx": "[TX] ", "rx": "[RX] ", "error": "!! ", "success": "OK ", "system": "## "}.get(tag, "")

        html = f'<span style="color:#6c7086;">{timestamp}</span> <span style="color:{color};">{html_lib.escape(prefix)}{safe_text}</span>'
        self.text_display.append(html)
        if self.check_auto_scroll.isChecked():
            self.text_display.moveCursor(QTextCursor.End)

    def log_msg(self, text, tag):
        # 线程安全的日志入口
        self.sig_log_msg.emit(text, tag)

    # --- 发送逻辑 ---
    def send_raw(self, data: bytes):
        if self.current_mode == "SERIAL" and self.serial.isOpen():
            self.serial.write(data)
            self.tx_cnt += len(data)
            self.lbl_tx.setText(f"TX: {self.tx_cnt}")
            return True
        elif self.current_mode == "TCP" and self.tcp_connected:
            try:
                self.tcp_socket.sendall(data)
                self.tx_cnt += len(data)
                self.lbl_tx.setText(f"TX: {self.tx_cnt}")
                return True
            except:
                self.disconnect_tcp()
                return False
        return False

    def send_string(self, text, is_hex=False, add_nl=True):
        if not text: return
        data = b''
        try:
            if is_hex:
                data = bytes.fromhex(text)
            else:
                data = text.encode('utf-8')

            if add_nl and not is_hex:
                data += b'\r\n'
            elif add_nl and is_hex:
                data += b'\r\n'  # Hex模式下是否加回车看需求，这里暂加

            if self.send_raw(data):
                self.log_msg(text, "tx")
        except Exception as e:
            self.log_msg(tr("log_send_err", self.current_lang, err=e), "error")

    def get_line_edit_hex_status(self, line_edit):
        if hasattr(self, 'quick_inputs') and line_edit in self.quick_inputs:
            idx = self.quick_inputs.index(line_edit)
            return self.quick_hex_checks[idx].isChecked()
        if hasattr(self, 'script_inputs'):
            for t in range(3):
                if line_edit in self.script_inputs[t]:
                    idx = self.script_inputs[t].index(line_edit)
                    return self.script_hex_checks[t][idx].isChecked()
        return False

    def show_crc_menu(self, line_edit, pos):
        from PySide6.QtGui import QAction
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        
        crc_options = [
            ("CRC16 (Modbus)", Checksums.crc16_modbus),
            ("CRC8", Checksums.crc8),
            ("CRC32", Checksums.crc32),
            ("CheckSum (SUM8)", Checksums.sum),
            ("BCC (XOR)", Checksums.bcc),
            ("LRC", Checksums.lrc),
            ("CRC16 (XModem)", Checksums.crc16_xmodem)
        ]
        
        for name, func in crc_options:
            action = QAction(tr("log_crc_menu_add", self.current_lang, name=name), self)
            action.triggered.connect(lambda checked=False, l=line_edit, f=func: self.append_crc(l, f))
            menu.addAction(action)
            
        menu.exec_(line_edit.mapToGlobal(pos))

    def show_script_menu(self, line_edit, row_idx, t_idx, pos):
        from PySide6.QtGui import QAction
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        
        # CRC Options Submenu
        crc_menu = menu.addMenu(tr("log_crc_menu", self.current_lang))
        crc_options = [
            ("CRC16 (Modbus)", Checksums.crc16_modbus),
            ("CRC8", Checksums.crc8),
            ("CRC32", Checksums.crc32),
            ("CheckSum (SUM8)", Checksums.sum),
            ("BCC (XOR)", Checksums.bcc),
            ("LRC", Checksums.lrc),
            ("CRC16 (XModem)", Checksums.crc16_xmodem)
        ]
        for name, func in crc_options:
            action = QAction(name, self)
            action.triggered.connect(lambda checked=False, l=line_edit, f=func: self.append_crc(l, f))
            crc_menu.addAction(action)
            
        menu.addSeparator()
        
        # Row Management
        action_insert = QAction(tr("log_insert_row", self.current_lang), self)
        action_insert.triggered.connect(lambda: self.insert_script_row(t_idx, row_idx))
        menu.addAction(action_insert)
        
        action_delete = QAction(tr("log_delete_row", self.current_lang), self)
        action_delete.triggered.connect(lambda: self.delete_script_row(t_idx, row_idx))
        menu.addAction(action_delete)
        
        action_clear = QAction(tr("log_clear_row", self.current_lang), self)
        action_clear.triggered.connect(line_edit.clear)
        menu.addAction(action_clear)

        menu.exec_(line_edit.mapToGlobal(pos))

    def insert_script_row(self, t_idx, idx):
        # Shift down
        for i in range(len(self.script_inputs[t_idx]) - 1, idx, -1):
            self.script_inputs[t_idx][i].setText(self.script_inputs[t_idx][i-1].text())
            self.script_hex_checks[t_idx][i].setChecked(self.script_hex_checks[t_idx][i-1].isChecked())
            self.script_nl_checks[t_idx][i].setChecked(self.script_nl_checks[t_idx][i-1].isChecked())
            self.script_comments[t_idx][i].setText(self.script_comments[t_idx][i-1].text())
        # Clear current
        self.script_inputs[t_idx][idx].clear()
        self.script_hex_checks[t_idx][idx].setChecked(False)
        self.script_nl_checks[t_idx][idx].setChecked(True)
        self.script_comments[t_idx][idx].clear()

    def delete_script_row(self, t_idx, idx):
        # Shift up
        for i in range(idx, len(self.script_inputs[t_idx]) - 1):
            self.script_inputs[t_idx][i].setText(self.script_inputs[t_idx][i+1].text())
            self.script_hex_checks[t_idx][i].setChecked(self.script_hex_checks[t_idx][i+1].isChecked())
            self.script_nl_checks[t_idx][i].setChecked(self.script_nl_checks[t_idx][i+1].isChecked())
            self.script_comments[t_idx][i].setText(self.script_comments[t_idx][i+1].text())
        # Clear last
        last_idx = len(self.script_inputs[t_idx]) - 1
        self.script_inputs[t_idx][last_idx].clear()
        self.script_hex_checks[t_idx][last_idx].setChecked(False)
        self.script_nl_checks[t_idx][last_idx].setChecked(True)
        self.script_comments[t_idx][last_idx].clear()

    def append_crc(self, line_edit, crc_func):
        text = line_edit.text().strip()
        if not text: return
        is_hex = self.get_line_edit_hex_status(line_edit)
        
        try:
            if is_hex:
                data = bytes.fromhex(text)
                crc_bytes = crc_func(data)
                crc_str = " ".join([f"{b:02X}" for b in crc_bytes])
                line_edit.setText(text + (" " if not text.endswith(" ") else "") + crc_str + " ")
            else:
                QMessageBox.warning(self, tr("warn_title", self.current_lang), tr("warn_hex_crc", self.current_lang))
        except Exception as e:
            QMessageBox.warning(self, tr("err_title", self.current_lang), tr("err_crc_calc", self.current_lang, e=e))

    def on_hex_toggled(self, line_edit, checked):
        text = line_edit.text().replace(" ", "")
        if checked:
            import re
            text = re.sub(r'[^0-9A-Fa-f]', '', text)
            formatted = " ".join([text[i:i+2] for i in range(0, len(text), 2)])
            if len(formatted) > 0 and len(text) % 2 == 0:
                formatted += " "
            line_edit.setText(formatted)

    def on_line_text_edited(self, line_edit, chk_hex):
        if not chk_hex.isChecked(): return
        text = line_edit.text().replace(" ", "").upper()
        import re
        text = re.sub(r'[^0-9A-F]', '', text)
        formatted = " ".join([text[i:i+2] for i in range(0, len(text), 2)])
        if len(text) > 0 and len(text) % 2 == 0:
            formatted += " "
        line_edit.setText(formatted)

    def send_quick(self, idx):
        text = self.quick_inputs[idx].text().strip()
        if not text: return
        
        # 历史记录
        if not self.cmd_history or self.cmd_history[-1] != text:
            self.cmd_history.append(text)
        self.history_pos = len(self.cmd_history)
        
        is_hex = self.quick_hex_checks[idx].isChecked()
        is_nl = self.quick_nl_checks[idx].isChecked()
        self.send_string(text, is_hex, is_nl)
        
        # 发后清空
        if self.quick_clear_checks[idx].isChecked():
            self.quick_inputs[idx].clear()

    # --- 波形解析 ---
    def parse_waveform(self, data: bytes):
        # 简单实现：按配置截取字节转int
        for i in range(3):
            if not self.field_enable_checks[i].isChecked(): continue
            try:
                # 获取配置
                hl = int(self.header_len_edits[i].text())
                off = int(self.offset_edits[i].text())
                fl = int(self.field_len_edits[i].text())
                is_big = self.endian_radios[i][0].isChecked()

                # 简单截取
                if len(data) < hl + off + fl: continue

                raw = data[hl + off: hl + off + fl]
                val = int.from_bytes(raw, 'big' if is_big else 'little', signed=True)

                self.plot_data_y[i].append(val)
                if len(self.plot_data_y[i]) > 1000:  # 限制长度
                    self.plot_data_y[i].pop(0)

                self.plot_lines[i].setData(self.plot_data_y[i])

            except:
                pass

    def toggle_waveform_pause(self):
        self.is_waveform_paused = not self.is_waveform_paused
        self.btn_pause_wave.setText(tr("btn_resume", self.current_lang) if self.is_waveform_paused else tr("btn_pause", self.current_lang))

    def clear_waveform(self):
        for i in range(3):
            self.plot_data_y[i] = []
            self.plot_lines[i].setData([])

    # --- 脚本引擎 (复用之前的逻辑) ---
    def start_script(self, tab_idx):
        is_connected = (self.current_mode == "SERIAL" and self.serial.isOpen()) or (
                    self.current_mode == "TCP" and self.tcp_connected)
        if not is_connected:
            QMessageBox.warning(self, tr("warn_title", self.current_lang), tr("warn_connect_first", self.current_lang))
            return

        self.parsed_tasks = []
        for i, line_edit in enumerate(self.script_inputs[tab_idx]):
            l = line_edit.text().strip()
            if not l: continue
            
            is_hex = self.script_hex_checks[tab_idx][i].isChecked()
            is_nl = self.script_nl_checks[tab_idx][i].isChecked()
            
            if l.lower().startswith("#delay"):
                try:
                    self.parsed_tasks.append({'type': 'DELAY', 'val': int(l.split()[1])})
                except:
                    pass
            else:
                self.parsed_tasks.append({'type': 'CMD', 'val': l, 'is_hex': is_hex, 'is_nl': is_nl})

        if not self.parsed_tasks: return

        self.current_step_index = 0
        self.current_loop_count = 0
        self.target_loop_count = self.spin_script_counts[tab_idx].value()
        self.loop_interval_ms = self.spin_script_intervals[tab_idx].value()
        self.running_tab_idx = tab_idx

        self.btn_start_scripts[tab_idx].setEnabled(False)
        self.btn_stop_scripts[tab_idx].setEnabled(True)
        self.script_scrolls[tab_idx].setEnabled(False)

        self.log_msg(tr("log_script_start", self.current_lang), "system")
        self.execute_next_step()

    def stop_script(self, tab_idx=None):
        if tab_idx is None: tab_idx = self.running_tab_idx
        if tab_idx == -1: return
        
        self.script_timer.stop()
        self.btn_start_scripts[tab_idx].setEnabled(True)
        self.btn_stop_scripts[tab_idx].setEnabled(False)
        self.script_scrolls[tab_idx].setEnabled(True)
        self.lbl_script_statuses[tab_idx].setText(tr("lbl_stopped", self.current_lang))
        self.log_msg(tr("log_script_stop", self.current_lang), "system")
        self.running_tab_idx = -1

    def execute_next_step(self):
        if self.running_tab_idx == -1: return
        tab_idx = self.running_tab_idx
        
        # 检查连接
        is_connected = (self.current_mode == "SERIAL" and self.serial.isOpen()) or (
                    self.current_mode == "TCP" and self.tcp_connected)
        if not is_connected: self.stop_script(); return

        if self.current_step_index >= len(self.parsed_tasks):
            self.current_loop_count += 1
            if self.target_loop_count > 0 and self.current_loop_count >= self.target_loop_count:
                self.stop_script(tab_idx)
                self.log_msg(tr("log_loop_done", self.current_lang), "success")
                return
            else:
                self.current_step_index = 0
                self.script_timer.start(self.loop_interval_ms)
                self.lbl_script_statuses[tab_idx].setText(tr("log_wait_interval", self.current_lang, ms=self.loop_interval_ms))
                return

        task = self.parsed_tasks[self.current_step_index]
        if task['type'] == 'CMD':
            self.send_string(task['val'], task.get('is_hex', False), task.get('is_nl', True))
            self.current_step_index += 1
            self.script_timer.start(50)  # 指令间最小间隔
        elif task['type'] == 'DELAY':
            self.log_msg(tr("log_delay", self.current_lang, ms=task['val']), "system")
            self.current_step_index += 1
            self.script_timer.start(task['val'])

        self.lbl_script_statuses[tab_idx].setText(f"Loop: {self.current_loop_count} | Step: {self.current_step_index}")

    def send_script_row(self, tab_idx, row_idx):
        if tab_idx >= len(self.script_inputs) or row_idx >= len(self.script_inputs[tab_idx]):
            return
        
        text = self.script_inputs[tab_idx][row_idx].text().strip()
        if not text:
            return
        
        is_connected = (self.current_mode == "SERIAL" and self.serial.isOpen()) or (
                    self.current_mode == "TCP" and self.tcp_connected)
        if not is_connected:
            QMessageBox.warning(self, tr("warn_title", self.current_lang), tr("warn_connect_first", self.current_lang))
            return
            
        is_hex = self.script_hex_checks[tab_idx][row_idx].isChecked()
        is_nl = self.script_nl_checks[tab_idx][row_idx].isChecked()
        
        self.send_string(text, is_hex, is_nl)

    # --- 辅助功能 ---
    def toggle_language(self):
        """切换中英文"""
        self.current_lang = "en" if self.current_lang == "zh" else "zh"
        self.apply_language()

    def apply_language(self):
        """应用当前语言到所有静态 UI 元素"""
        L = self.current_lang

        # 窗口标题
        self.setWindowTitle(tr("window_title", L))

        # 语言按钮自身
        self.btn_lang.setText(tr("btn_lang", L))

        # 启动指南
        self.text_display.clear()
        self._show_startup_guide()

        # 通讯模式
        self.mode_group.setTitle(tr("mode_group", L))
        self.radio_serial.setText(tr("radio_serial", L))
        self.radio_tcp.setText(tr("radio_tcp", L))

        # 串口设置
        self.serial_group.setTitle(tr("serial_group", L))
        self.lbl_port.setText(tr("lbl_port", L))
        self.lbl_baud.setText(tr("lbl_baud", L))
        self.lbl_data.setText(tr("lbl_data", L))
        self.lbl_parity.setText(tr("lbl_parity", L))
        self.lbl_stop.setText(tr("lbl_stop", L))

        # TCP 设置
        self.tcp_group.setTitle(tr("tcp_group", L))
        self.lbl_ip.setText(tr("lbl_ip", L))
        self.lbl_tcp_port.setText(tr("lbl_tcp_port", L))

        # 接收/显示 设置
        self.receive_settings_group.setTitle(tr("receive_group", L))
        self.btn_show_text.setText(tr("btn_text_view", L))
        self.btn_show_waveform.setText(tr("btn_wave_view", L))
        self.lbl_format.setText(tr("lbl_format", L))
        self.check_auto_scroll.setText(tr("chk_auto_scroll", L))
        self.check_show_timestamp.setText(tr("chk_timestamp", L))
        self.btn_clear_receive.setText(tr("btn_clear", L))

        # 脚本扩展按钮
        if self.btn_toggle_extension.isChecked():
            self.btn_toggle_extension.setText(tr("btn_extension_on", L))
        else:
            self.btn_toggle_extension.setText(tr("btn_extension_off", L))

        # 底部选项卡
        self.btn_tab_quick.setText(tr("tab_quick_send", L))
        self.btn_tab_wave.setText(tr("tab_waveform", L))

        # 快捷发送
        for i in range(3):
            self.quick_inputs[i].setPlaceholderText(tr("quick_placeholder", L, n=i + 1))
            self.quick_send_btns[i].setText(tr("btn_send_n", L, n=i + 1))
            self.quick_timer_checks[i].setText(tr("chk_timed", L))
            self.quick_clear_checks[i].setText(tr("chk_clear_after", L))

        # 波形解析
        for i in range(3):
            self.wave_channel_groups[i].setTitle(tr("wave_channel", L, n=i + 1))
            self.field_enable_checks[i].setText(tr("chk_enable", L))
            self.wave_lbl_skip[i].setText(tr("lbl_skip_header", L))
            self.wave_lbl_offset[i].setText(tr("lbl_offset", L))
            self.wave_lbl_length[i].setText(tr("lbl_length", L))
        self.btn_clear_wave.setText(tr("btn_clear_wave", L))
        if self.is_waveform_paused:
            self.btn_pause_wave.setText(tr("btn_resume", L))
        else:
            self.btn_pause_wave.setText(tr("btn_pause", L))

        # 脚本循环任务
        self.script_group.setTitle(tr("script_group", L))
        for t in range(3):
            self.lbl_select_alls[t].setText(tr("lbl_select_all", L))
            self.lbl_intervals[t].setText(tr("lbl_interval", L))
            self.lbl_loop_counts[t].setText(tr("lbl_loop_count", L))
            self.btn_import_txts[t].setText(tr("btn_import", L))
            self.btn_export_scripts[t].setText(tr("btn_export", L))
            self.btn_start_scripts[t].setText(tr("btn_start", L))
            self.btn_stop_scripts[t].setText(tr("btn_stop", L))
            for btn in self.script_send_btns[t]:
                btn.setText(tr("btn_send", L))
            for ce in self.script_comments[t]:
                ce.setPlaceholderText(tr("comment_placeholder", L))
            # 脚本状态标签（就绪）
            if self.running_tab_idx != t:
                self.lbl_script_statuses[t].setText(tr("lbl_ready", L))

        # 更新动态状态
        self.update_ui_state()

    def update_ui_state(self):
        s_open = self.serial.isOpen()
        t_open = self.tcp_connected
        L = self.current_lang

        if self.current_mode == "SERIAL":
            self.btn_open_serial.setText(tr("btn_close_serial", L) if s_open else tr("btn_open_serial", L))
            self.btn_open_serial.setObjectName("btn_disconnect_close" if s_open else "btn_connect_open")
            self.lbl_status.setText(tr("status_serial_open", L) if s_open else tr("status_serial_closed", L))

            # 禁用TCP相关
            self.ip_input.setEnabled(False);
            self.port_input.setEnabled(False);
            self.btn_connect_tcp.setEnabled(False)
            # 启用串口相关
            self.port_combo.setEnabled(not s_open);
            self.baud_combo.setEnabled(not s_open);
            self.btn_open_serial.setEnabled(True)

        else:  # TCP
            self.btn_connect_tcp.setText(tr("btn_disconnect", L) if t_open else tr("btn_connect", L))
            self.btn_connect_tcp.setObjectName("btn_disconnect_close" if t_open else "btn_connect_open")
            self.lbl_status.setText(tr("status_tcp_connected", L) if t_open else tr("status_tcp_disconnected", L))

            # 禁用串口相关
            self.port_combo.setEnabled(False);
            self.baud_combo.setEnabled(False);
            self.btn_open_serial.setEnabled(False)
            # 启用TCP相关
            self.ip_input.setEnabled(not t_open);
            self.port_input.setEnabled(not t_open);
            self.btn_connect_tcp.setEnabled(True)

        # 刷新样式
        self.btn_open_serial.setStyle(self.btn_open_serial.style())
        self.btn_connect_tcp.setStyle(self.btn_connect_tcp.style())

    def clear_all(self):
        self.text_display.clear()
        self.clear_waveform()
        self.rx_cnt = 0;
        self.tx_cnt = 0
        self.rx_buffer.clear()

    # 键盘/拖拽过滤
    def eventFilter(self, obj, event):
        # 处理脚本 Tab 标题双击重命名（内联编辑）
        if hasattr(self, "script_tab_btns") and isinstance(obj, QPushButton) and obj in self.script_tab_btns:
            if event.type() == QEvent.MouseButtonDblClick and event.button() == Qt.LeftButton:
                self._start_inline_tab_rename(obj)
                return True
        # 处理内联编辑框的焦点丢失 → 确认修改
        if hasattr(self, "_renaming_edit") and obj is self._renaming_edit:
            if event.type() == QEvent.FocusOut:
                self._finish_inline_tab_rename()
                return True

        # 处理拖拽
        if hasattr(self, "script_stack"):
            if isinstance(obj, QLabel) and obj.property("row_idx") is not None:
                if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                    self.drag_start_pos = event.pos()
                    self.drag_source_row = obj.property("row_idx")
                elif event.type() == QEvent.MouseMove and self.drag_start_pos is not None:
                    if (event.pos() - self.drag_start_pos).manhattanLength() > 5:
                        drag = QDrag(self)
                        mime = QMimeData()
                        mime.setText(f"{obj.property('tab_idx')},{self.drag_source_row}")
                        drag.setMimeData(mime)
                        drag.exec_(Qt.MoveAction)
                        self.drag_start_pos = None
                        
            elif isinstance(obj, QWidget) and obj.property("row_idx") is not None and obj.layout():
                if event.type() == QEvent.DragEnter:
                    if event.mimeData().hasText(): event.acceptProposedAction()
                    return True
                elif event.type() == QEvent.Drop:
                    data_str = event.mimeData().text().split(',')
                    if len(data_str) == 2:
                        source_tab = int(data_str[0])
                        source_idx = int(data_str[1])
                        target_idx = obj.property("row_idx")
                        target_tab = obj.property("tab_idx")
                        if source_tab == target_tab and source_idx != target_idx and source_idx >= 0 and target_idx >= 0:
                            self.swap_script_rows(target_tab, source_idx, target_idx)
                    event.acceptProposedAction()
                    return True

        if event.type() == QEvent.KeyPress and isinstance(obj, QLineEdit):
            # Hex 模式下回删体验优化：只有在没有选中文字时，才执行自定义的跳空格回删
            if event.key() == Qt.Key_Backspace and self.get_line_edit_hex_status(obj):
                if not obj.hasSelectedText():
                    cursor = obj.cursorPosition()
                    text = obj.text()
                    if cursor > 0 and text[cursor - 1] == ' ':
                        obj.setText(text[:cursor-2] + text[cursor:])
                        obj.setCursorPosition(cursor-2)
                        return True
                # 若有选中文字，直接走默认回删逻辑
            if hasattr(self, "cmd_history"):
                is_target = False
                if hasattr(self, "quick_inputs") and obj in self.quick_inputs:
                    is_target = True
                if hasattr(self, "script_inputs"):
                    for t in range(3):
                        if obj in self.script_inputs[t]:
                            is_target = True
                            break
                    
                if is_target:
                    if event.key() == Qt.Key_Up:
                        self.history_pos = max(0, self.history_pos - 1)
                        if self.cmd_history: obj.setText(
                            self.cmd_history[min(self.history_pos, len(self.cmd_history) - 1)])
                        return True
                    elif event.key() == Qt.Key_Down:
                        self.history_pos = min(len(self.cmd_history), self.history_pos + 1)
                        if self.history_pos < len(self.cmd_history):
                            obj.setText(self.cmd_history[self.history_pos])
                        else:
                            obj.clear()
                        return True
        return super().eventFilter(obj, event)

    def load_settings(self):
        from PySide6.QtCore import QSettings
        settings = QSettings("PCAssistant", "Configs")
        
        # 基础配置
        if settings.contains("baud"): self.baud_combo.setCurrentText(settings.value("baud"))
        if settings.contains("ip"): self.ip_input.setText(settings.value("ip"))
        if settings.contains("port"): self.port_input.setText(settings.value("port"))
        if settings.contains("recv_fmt"): self.receive_format_combo.setCurrentText(settings.value("recv_fmt"))
        
        if settings.contains("parity"): self.parity_combo.setCurrentText(settings.value("parity"))
        if settings.contains("stop_bits"): self.stop_bits_combo.setCurrentText(settings.value("stop_bits"))

        # 语言
        if settings.contains("lang"):
            self.current_lang = settings.value("lang")

        # 快捷发送
        for i in range(3):
            if settings.contains(f"quick_text_{i}"):
                self.quick_inputs[i].setText(settings.value(f"quick_text_{i}"))
            if settings.contains(f"quick_hex_{i}"):
                self.quick_hex_checks[i].setChecked(settings.value(f"quick_hex_{i}") == "true")
            if settings.contains(f"quick_nl_{i}"):
                self.quick_nl_checks[i].setChecked(settings.value(f"quick_nl_{i}") == "true")
            if settings.contains(f"quick_timer_checked_{i}"):
                self.quick_timer_checks[i].setChecked(settings.value(f"quick_timer_checked_{i}") == "true")
            if settings.contains(f"quick_timer_interval_{i}"):
                self.quick_timer_spins[i].setValue(int(settings.value(f"quick_timer_interval_{i}")))
            if settings.contains(f"quick_clear_{i}"):
                self.quick_clear_checks[i].setChecked(settings.value(f"quick_clear_{i}") == "true")
                
        # 脚本扩展 (3 个 Tabs)
        for t in range(3):
            if settings.contains(f"script_btn_name_{t}"):
                self.script_tab_btns[t].setText(settings.value(f"script_btn_name_{t}"))
            if settings.contains(f"script_interval_{t}"): 
                self.spin_script_intervals[t].setValue(int(settings.value(f"script_interval_{t}")))
            if settings.contains(f"script_count_{t}"): 
                self.spin_script_counts[t].setValue(int(settings.value(f"script_count_{t}")))
            
            for i in range(len(self.script_inputs[t])):
                if settings.contains(f"script_text_{t}_{i}"):
                    self.script_inputs[t][i].setText(settings.value(f"script_text_{t}_{i}"))
                if settings.contains(f"script_hex_{t}_{i}"):
                    self.script_hex_checks[t][i].setChecked(settings.value(f"script_hex_{t}_{i}") == "true")
                if settings.contains(f"script_nl_{t}_{i}"):
                    self.script_nl_checks[t][i].setChecked(settings.value(f"script_nl_{t}_{i}") == "true")
                if settings.contains(f"script_comment_{t}_{i}"):
                    self.script_comments[t][i].setText(settings.value(f"script_comment_{t}_{i}"))

    def save_settings(self):
        from PySide6.QtCore import QSettings
        settings = QSettings("PCAssistant", "Configs")
        
        settings.setValue("baud", self.baud_combo.currentText())
        settings.setValue("ip", self.ip_input.text())
        settings.setValue("port", self.port_input.text())
        settings.setValue("recv_fmt", self.receive_format_combo.currentText())
        
        settings.setValue("parity", self.parity_combo.currentText())
        settings.setValue("stop_bits", self.stop_bits_combo.currentText())
        settings.setValue("lang", self.current_lang)
        
        for i in range(3):
            settings.setValue(f"quick_text_{i}", self.quick_inputs[i].text())
            settings.setValue(f"quick_hex_{i}", "true" if self.quick_hex_checks[i].isChecked() else "false")
            settings.setValue(f"quick_nl_{i}", "true" if self.quick_nl_checks[i].isChecked() else "false")
            settings.setValue(f"quick_timer_checked_{i}", "true" if self.quick_timer_checks[i].isChecked() else "false")
            settings.setValue(f"quick_timer_interval_{i}", self.quick_timer_spins[i].value())
            settings.setValue(f"quick_clear_{i}", "true" if self.quick_clear_checks[i].isChecked() else "false")
            
        for t in range(3):
            settings.setValue(f"script_btn_name_{t}", self.script_tab_btns[t].text())
            settings.setValue(f"script_interval_{t}", self.spin_script_intervals[t].value())
            settings.setValue(f"script_count_{t}", self.spin_script_counts[t].value())
            
            for i in range(len(self.script_inputs[t])):
                settings.setValue(f"script_text_{t}_{i}", self.script_inputs[t][i].text())
                settings.setValue(f"script_hex_{t}_{i}", "true" if self.script_hex_checks[t][i].isChecked() else "false")
                settings.setValue(f"script_nl_{t}_{i}", "true" if self.script_nl_checks[t][i].isChecked() else "false")
                settings.setValue(f"script_comment_{t}_{i}", self.script_comments[t][i].text())

    def swap_script_rows(self, t_idx, idx1, idx2):
        temp_text = self.script_inputs[t_idx][idx1].text()
        temp_hex = self.script_hex_checks[t_idx][idx1].isChecked()
        temp_nl = self.script_nl_checks[t_idx][idx1].isChecked()
        temp_comment = self.script_comments[t_idx][idx1].text()
        
        self.script_inputs[t_idx][idx1].setText(self.script_inputs[t_idx][idx2].text())
        self.script_hex_checks[t_idx][idx1].setChecked(self.script_hex_checks[t_idx][idx2].isChecked())
        self.script_nl_checks[t_idx][idx1].setChecked(self.script_nl_checks[t_idx][idx2].isChecked())
        self.script_comments[t_idx][idx1].setText(self.script_comments[t_idx][idx2].text())
        
        self.script_inputs[t_idx][idx2].setText(temp_text)
        self.script_hex_checks[t_idx][idx2].setChecked(temp_hex)
        self.script_nl_checks[t_idx][idx2].setChecked(temp_nl)
        self.script_comments[t_idx][idx2].setText(temp_comment)

    def closeEvent(self, event):
        self.save_settings()
        if self.serial.isOpen(): self.serial.close()
        self.disconnect_tcp()
        event.accept()
