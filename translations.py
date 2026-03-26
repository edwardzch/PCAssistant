# translations.py — 中英文翻译字典

TRANSLATIONS = {
    # ===== 窗口标题 =====
    "window_title": {"zh": "Unified Serial/TCP Assistant V2.1", "en": "Unified Serial/TCP Assistant V2.1"},

    # ===== 通讯模式 =====
    "mode_group": {"zh": "通讯模式", "en": "Communication Mode"},
    "radio_serial": {"zh": "串口 (Serial)", "en": "Serial"},
    "radio_tcp": {"zh": "以太网 (TCP Client)", "en": "TCP Client"},

    # ===== 串口设置 =====
    "serial_group": {"zh": "串口设置", "en": "Serial Settings"},
    "lbl_port": {"zh": "端口:", "en": "Port:"},
    "lbl_baud": {"zh": "波特:", "en": "Baud:"},
    "lbl_data": {"zh": "数据:", "en": "Data:"},
    "lbl_parity": {"zh": "校验:", "en": "Parity:"},
    "lbl_stop": {"zh": "停止:", "en": "Stop:"},
    "btn_open_serial": {"zh": "打开串口", "en": "Open"},
    "btn_close_serial": {"zh": "关闭串口", "en": "Close"},

    # ===== TCP 设置 =====
    "tcp_group": {"zh": "TCP 设置", "en": "TCP Settings"},
    "lbl_ip": {"zh": "IP地址:", "en": "IP Addr:"},
    "lbl_tcp_port": {"zh": "端口:", "en": "Port:"},
    "btn_connect": {"zh": "连接", "en": "Connect"},
    "btn_disconnect": {"zh": "断开", "en": "Disconnect"},

    # ===== 接收/显示 设置 =====
    "receive_group": {"zh": "接收/显示 设置", "en": "Receive / Display"},
    "btn_text_view": {"zh": "文本视图", "en": "Text View"},
    "btn_wave_view": {"zh": "波形视图", "en": "Waveform"},
    "btn_extension_on": {"zh": "脚本扩展 >>", "en": "Script >>"},
    "btn_extension_off": {"zh": "脚本扩展 <<", "en": "Script <<"},
    "lbl_format": {"zh": "格式:", "en": "Format:"},
    "chk_auto_scroll": {"zh": "自动滚动", "en": "Auto Scroll"},
    "chk_timestamp": {"zh": "时间戳", "en": "Timestamp"},
    "btn_clear": {"zh": "清空", "en": "Clear"},

    # ===== 底部选项卡 =====
    "tab_quick_send": {"zh": "快捷发送", "en": "Quick Send"},
    "tab_waveform": {"zh": "波形解析", "en": "Waveform Config"},

    # ===== 快捷发送 =====
    "quick_placeholder": {"zh": "快捷指令 {n} (↑↓切换历史)", "en": "Quick Cmd {n} (↑↓ history)"},
    "btn_send_n": {"zh": "发送 {n}", "en": "Send {n}"},
    "chk_timed": {"zh": "定时", "en": "Timed"},
    "chk_clear_after": {"zh": "发后清空", "en": "Auto-clear"},

    # ===== 波形解析 =====
    "wave_channel": {"zh": "通道 {n}", "en": "Channel {n}"},
    "chk_enable": {"zh": "启用", "en": "Enable"},
    "lbl_skip_header": {"zh": "跳过头:", "en": "Skip Hdr:"},
    "lbl_offset": {"zh": "偏移:", "en": "Offset:"},
    "lbl_length": {"zh": "长度:", "en": "Length:"},
    "btn_pause": {"zh": "暂停", "en": "Pause"},
    "btn_resume": {"zh": "继续", "en": "Resume"},
    "btn_clear_wave": {"zh": "清空", "en": "Clear"},

    # ===== 脚本循环任务 =====
    "script_group": {"zh": "脚本循环任务 (Script Batch)", "en": "Script Loop Task (Batch)"},
    "lbl_select_all": {"zh": "全选", "en": "All"},
    "comment_placeholder": {"zh": "注释...", "en": "Comment..."},
    "btn_send": {"zh": "发送", "en": "Send"},
    "lbl_interval": {"zh": "循环间隔(ms):", "en": "Interval(ms):"},
    "lbl_loop_count": {"zh": "循环次数(0=∞):", "en": "Loops(0=∞):"},
    "lbl_ready": {"zh": "就绪", "en": "Ready"},
    "btn_import": {"zh": "导入 TXT", "en": "Import TXT"},
    "btn_export": {"zh": "导出 TXT", "en": "Export TXT"},
    "btn_start": {"zh": "开始运行", "en": "Start"},
    "btn_stop": {"zh": "停止运行", "en": "Stop"},
    "lbl_stopped": {"zh": "已停止", "en": "Stopped"},

    # ===== 右键菜单 =====
    "menu_add_crc": {"zh": "添加校验码", "en": "Append Checksum"},
    "menu_add_prefix": {"zh": "添加 {name}", "en": "Append {name}"},
    "menu_insert_row": {"zh": "在此处插入空行", "en": "Insert Empty Row"},
    "menu_delete_row": {"zh": "删除此行", "en": "Delete This Row"},
    "menu_clear_row": {"zh": "清空此行", "en": "Clear This Row"},

    # ===== 对话框/提示 =====
    "warn_connect_first": {"zh": "请先连接设备", "en": "Please connect device first"},
    "warn_title": {"zh": "警告", "en": "Warning"},
    "warn_hex_crc": {"zh": "添加校验码建议在 Hex 模式下进行！", "en": "Checksum is recommended in Hex mode!"},
    "err_title": {"zh": "错误", "en": "Error"},
    "err_crc_calc": {"zh": "计算校验码失败: {e}", "en": "Checksum calculation failed: {e}"},

    # ===== 状态栏 =====
    "status_disconnected": {"zh": "未连接", "en": "Disconnected"},
    "status_serial_open": {"zh": "串口: 开启", "en": "Serial: Open"},
    "status_serial_closed": {"zh": "串口: 关闭", "en": "Serial: Closed"},
    "status_tcp_connected": {"zh": "TCP: 已连接", "en": "TCP: Connected"},
    "status_tcp_disconnected": {"zh": "TCP: 未连接", "en": "TCP: Disconnected"},

    # ===== 语言按钮 =====
    "btn_lang": {"zh": "English", "en": "中文"},

    # ===== 内联重命名 =====
    "rename_title": {"zh": "重命名脚本", "en": "Rename Script"},
    "rename_prompt": {"zh": "请输入新的脚本标题:", "en": "Enter new script title:"},

    # ===== 启动指南 =====
    "startup_guide": {
        "zh": """
        <div style="color: #cad3f5; font-size: 13px; line-height: 1.5;">
            <h2 style="color: #8bd5ca;">欢迎使用 Unified Serial/TCP Assistant V2.0</h2>
            <ul>
                <li><b>快速 Hex 格式：</b> 勾选 Hex 后输入内容会自动每两字符加空格，并在末尾点击回车或勾选右侧复选即可包含换行。</li>
                <li><b>右键菜单扩展：</b> 在快捷发送和脚本列表的任何指令输入框中，右键均可快速计算并追加多种格式的校验算法 (比如 CRC/BCC 等)。</li>
                <li><b>多组脚本独立存取：</b> 右侧 3 个脚本配置页完全独立。点击"导入 TXT"自动识别文件名重命名选项卡，也可以使用"导出 TXT"分享您的独立配置。</li>
                <li><b>原生流畅打字：</b> 输入框已默认支持并放行系统原生的 <i>全选(Ctrl+A)、撤销(Ctrl+Z)、恢复(Ctrl+Y)</i> 等标准打字功能；且原生解决自动添加空格带来的退格问题。</li>
            </ul>
            <p style="color: #eed49f;"><i>提示：各项界面的配置项参数、勾选状态以及列表的数据都在软件退出时自动完成记忆存档，下次打开无需重设。</i></p>
            <hr style="border-color: #494d64;">
        </div>
        """,
        "en": """
        <div style="color: #cad3f5; font-size: 13px; line-height: 1.5;">
            <h2 style="color: #8bd5ca;">Welcome to Unified Serial/TCP Assistant V2.1</h2>
            <ul>
                <li><b>Quick Hex:</b> Check "Hex" and typed content is auto-spaced every two chars. Press Enter or check the newline box to append CRLF.</li>
                <li><b>Context Menu:</b> Right-click any command input in Quick Send or Script to append various checksums (CRC/BCC, etc.).</li>
                <li><b>Multi-script tabs:</b> 3 independent script tabs. "Import TXT" auto-renames the tab; "Export TXT" shares your config.</li>
                <li><b>Native editing:</b> Standard shortcuts <i>Select-All (Ctrl+A), Undo (Ctrl+Z), Redo (Ctrl+Y)</i> work naturally in all input fields.</li>
            </ul>
            <p style="color: #eed49f;"><i>Tip: All settings, checkbox states, and script data are auto-saved on exit and restored on next launch.</i></p>
            <hr style="border-color: #494d64;">
        </div>
        """
    },

    # ===== 日志消息 =====
    "log_serial_closed": {"zh": "串口已关闭", "en": "Serial port closed"},
    "log_serial_open_ok": {"zh": "串口 {name} 打开成功", "en": "Serial port {name} opened"},
    "log_serial_open_fail": {"zh": "串口打开失败: {err}", "en": "Failed to open serial: {err}"},
    "log_config_err": {"zh": "配置错误: {err}", "en": "Config error: {err}"},
    "log_port_err": {"zh": "端口错误", "en": "Port error"},
    "log_connecting": {"zh": "正在连接 {addr}...", "en": "Connecting to {addr}..."},
    "log_tcp_ok": {"zh": "TCP 连接成功", "en": "TCP connected"},
    "log_connect_fail": {"zh": "连接失败: {err}", "en": "Connection failed: {err}"},
    "log_tcp_closed": {"zh": "TCP 已断开", "en": "TCP disconnected"},
    "log_server_disconnected": {"zh": "服务器断开连接", "en": "Server disconnected"},
    "log_send_err": {"zh": "发送数据错误: {err}", "en": "Send error: {err}"},
    "log_script_start": {"zh": "脚本开始运行", "en": "Script started"},
    "log_script_stop": {"zh": "脚本停止", "en": "Script stopped"},
    "log_loop_done": {"zh": "循环完成", "en": "Loop completed"},
    "log_delay": {"zh": "延时 {ms}ms", "en": "Delay {ms}ms"},
    "log_wait_interval": {"zh": "等待循环间隔 {ms}ms", "en": "Waiting interval {ms}ms"},
    "log_import_ok": {"zh": "成功导入 {n} 条指令与注释", "en": "Successfully imported {n} commands"},
    "log_import_fail": {"zh": "导入脚本失败: {err}", "en": "Import failed: {err}"},
    "log_export_ok": {"zh": "成功导出 {n} 条指令到 {name}", "en": "Exported {n} commands to {name}"},
    "log_export_fail": {"zh": "导出脚本失败: {err}", "en": "Export failed: {err}"},
    "log_crc_menu_add": {"zh": "添加 {name}", "en": "Append {name}"},
    "log_crc_menu": {"zh": "添加校验码", "en": "Append Checksum"},
    "log_insert_row": {"zh": "在此处插入空行", "en": "Insert Empty Row"},
    "log_delete_row": {"zh": "删除此行", "en": "Delete This Row"},
    "log_clear_row": {"zh": "清空此行", "en": "Clear This Row"},
}


def tr(key, lang="zh", **kwargs):
    """获取翻译文本，支持 format 占位符"""
    entry = TRANSLATIONS.get(key, {})
    text = entry.get(lang, entry.get("zh", key))
    if kwargs:
        text = text.format(**kwargs)
    return text
