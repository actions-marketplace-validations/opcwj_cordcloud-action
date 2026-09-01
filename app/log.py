import sys
from datetime import timedelta, timezone, datetime

from actions_toolkit import core

# 检测是否在 debug 模式下
DEBUG_MODE = 'debugpy' in sys.modules or 'pydevd' in sys.modules

# 本地 Windows 控制台默认 GBK 编码，无法输出 emoji 等字符，强制使用 UTF-8 输出
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def now():
    tz = timezone(timedelta(hours=+8))
    return datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')


def info(s: str = ''):
    if DEBUG_MODE:
        print(f'[{now()}] {s}')
    else:
        core.info(f'[{now()}] {s}')


def warning(s: str = ''):
    if DEBUG_MODE:
        print(f'[{now()}] {s}')
    else:
        core.warning(f'[{now()}] {s}')


def error(s: str = ''):
    if DEBUG_MODE:
        print(f'[{now()}] {s}')
    else:
        core.info(f'[{now()}] {s}')


def set_failed(s: str = ''):
    if DEBUG_MODE:
        print(f'[{now()}] {s}')
    else:
        core.set_failed(f'[{now()}] {s}')