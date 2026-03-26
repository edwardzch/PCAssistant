import os
import sys
import subprocess

# 打包所需的全部依赖（包括运行时依赖和打包工具本身）
REQUIRED_PACKAGES = [
    'pyinstaller',
    'PySide6',
    'pyqtgraph',
    'pyserial',
    'crc',
    'numpy',
]

def ensure_dependencies():
    """检查并自动安装缺失的依赖包"""
    missing = []
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg.lower().replace('-', '_'))
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print(f"检测到缺失依赖: {', '.join(missing)}")
        print("正在自动安装，请稍候...\n")
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install'] + missing,
            check=True
        )
        print("\n依赖安装完成！\n")
    else:
        print("所有依赖已就绪。\n")

if __name__ == '__main__':
    print("=" * 50)
    print("  PCAssistant 一键打包脚本")
    print("=" * 50)
    
    # 第一步：确保所有依赖已安装
    ensure_dependencies()
    
    # 第二步：执行 PyInstaller 打包
    print("开始打包 PCAssistant 为单文件 EXE，请稍候...\n")
    subprocess.run([
        sys.executable, '-m', 'PyInstaller',
        'main.py',
        '--name=PCAssistant',       # 生成的 exe 名称
        '--windowed',               # 运行时不显示黑色控制台 (-w)
        '--onefile',                # 只生成一个独立的 exe 文件 (-F)
        '--icon=PCAssistant.ico',   # 指定应用图标
        '--add-data=PCAssistant.ico;.',  # 将 ico 打包进 EXE 内部，运行时可访问
        
        # 强制包含可能无法被静态分析到的动态加载库
        '--hidden-import=pyqtgraph',
        '--collect-all=pyqtgraph',  # 收集 pyqtgraph 内部所有依赖和资源
        '--hidden-import=PySide6',
        '--hidden-import=PySide6.QtSerialPort',
        '--hidden-import=crc',
        '--hidden-import=numpy',
        
        '--clean',                  # 构建前清理 PyInstaller 缓存
        '--noconfirm',              # 自动覆盖之前的文件，免提示
    ], check=True)
    
    print("\n" + "=" * 50)
    print("  打包完成！")
    print(f"  输出路径: {os.path.abspath('dist/PCAssistant.exe')}")
    print("=" * 50)

