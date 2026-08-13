"""
Общая конфигурация для всех скриптов
"""
import os
import time



# Путь к папке с установочными файлами
BUILD_PATH = r"C:\builds"

# ============================================================================
# ПУТИ К ПРИЛОЖЕНИЯМ
# ============================================================================

CONSOLE_EXE_PATH = r"C:\Program Files\Neocom Software\TRBOnet Enterprise\Console\TRBOnet.Console.exe"
SERVER_EXE_PATH = r"C:\Program Files\Neocom Software\TRBOnet Enterprise\Server\TRBOnet.Server.exe"
ONE_EXE_PATH = r"C:\Program Files\Neocom Software\TRBOnet Enterprise\Console\TRBOnet.One.exe"


# Название окна конфигуратора сервера
SERVER_WINDOW_TITLE = "TRBOnet Enterprise 6.5 / Server"
WINDOW_CONSOLE_PATTERN = r"TRBOnet Enterprise.*Dispatch Console"
WINDOW_ONE_PATTERN = r"TRBOnet One"
WINDOW_CONNECT_MANAGER_ONE_PATTERN = r"TRBOnet Connection Manager"
WINDOW_CONNECT_MANAGER_ENTERPRISE_PATTERN = r"Connect to TRBOnet Server"


# Product Code для удаления
PRODUCT_CODE = "{CEC1EF24-87F3-4324-A393-104A5038078C}"

# Список приложений для проверки после установки
APPS_TO_CHECK = [
    "TRBOnet.Server",
    "TRBOnet.Console",
    "TRBOnet.One"
]

# Опция установки: local / server / console / redundant
INSTALL_OPTION = "local"

# Тихая установка
SILENT_INSTALL = True

#Глобальный таймаут
TIMEOUT = 30

# Задержка между действиями (сек)
SMALL_DELAY = 1
MEDIUM_DELAY = 2
LARGE_DELAY = 5
PTT_DELAY = 15                 # Длительность голосовой сессии (сек)

# ============================================================================
# ПУТИ ДЛЯ СКРИНШОТОВ
# ============================================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREENSHOTS_DIR = os.path.join(BASE_DIR, "screenshots")

# Имена файлов для скриншотов
EXPECTED_SCREENSHOT = "expected_console.png"
ACTUAL_SCREENSHOT = "actual_console.png"
DIFF_SCREENSHOT = "diff_console.png"

# Полные пути
EXPECTED_SCREENSHOT_PATH = os.path.join(SCREENSHOTS_DIR, EXPECTED_SCREENSHOT)
ACTUAL_SCREENSHOT_PATH = os.path.join(SCREENSHOTS_DIR, ACTUAL_SCREENSHOT)
DIFF_SCREENSHOT_PATH = os.path.join(SCREENSHOTS_DIR, DIFF_SCREENSHOT)

# ============================================================================
# НАСТРОЙКИ СРАВНЕНИЯ ИЗОБРАЖЕНИЙ
# ============================================================================

DIFF_THRESHOLD_PERCENT = 0.5    # Минимальный процент отличий для считания изображений разными
MIN_CLUSTER_PIXELS = 50         # Минимальное количество пикселей в кластере отличий
MASK_ENABLED = True             # Включить маскирование областей по умолчанию

# ============================================================================
# МАСКИРУЕМЫЕ ОБЛАСТИ (дата/время и другие динамические элементы)
# ============================================================================

MASK_AREAS = [
    {
        "name": "Время в правом верхнем углу",
        "left": 1733,
        "top": 127,
        "right": 1914,
        "bottom": 193,
    },
    {
        "name": "Время/информация в нижней части",
        "left": 263,
        "top": 838,
        "right": 1924,
        "bottom": 984,
    },
]

# ============================================================================
# НАСТРОЙКИ ПОДКЛЮЧЕНИЯ ПО УМОЛЧАНИЮ
# ============================================================================

DEFAULT_SERVER_ADDRESS = "127.0.0.1"
DEFAULT_SERVER_PORT = "4021"
DEFAULT_AUTH_METHOD = "TRBOnet Authentication"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"