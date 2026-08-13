"""
Фикс кодировки для Windows Console
Добавлять в начало каждого скрипта: import fix_encoding
"""

import sys
import io
import ctypes


def fix_console_encoding():
    """
    Настраивает консоль Windows на работу с UTF-8.
    """
    # Переопределяем stdout/stderr
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except:
            pass
    else:
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
        except:
            pass

    # Устанавливаем кодовую страницу консоли на UTF-8 (65001)
    if sys.platform == 'win32':
        try:
            ctypes.windll.kernel32.SetConsoleCP(65001)
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        except:
            pass


# Вызываем сразу при импорте
fix_console_encoding()