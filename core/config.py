"""
Общая конфигурация для всех скриптов
"""

# Путь к папке с установочными файлами
BUILD_PATH = r"C:\builds"

# Путь к исполняемому файлу TRBOnet Server
SERVER_EXE_PATH = r"C:\Program Files\Neocom Software\TRBOnet Enterprise\Server\TRBOnet.Server.exe"

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