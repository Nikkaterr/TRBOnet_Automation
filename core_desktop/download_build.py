"""
Автоматизация СКАЧИВАНИЯ И РАСПАКОВКИ TRBOnet
Скачивает архив по HTTPS: https://cdn.trbonet.com/blob/enterprise/builds/<версия>/TRBOnet.Enterprise_<версия>.zip
Принимает версию из аргументов командной строки
"""

import os
import sys
import shutil
import zipfile
import requests
from typing import Optional, Tuple
from datetime import datetime

# Импортируем фикс кодировки
import fix_encoding  # noqa

# Импортируем общую конфигурацию
from config import BUILD_PATH


# ============================================================================
# КОНСТАНТЫ И НАСТРОЙКИ
# ============================================================================

# Базовый URL для скачивания
BASE_URL = "https://cdn.trbonet.com/blob/enterprise/builds"

# Локальная папка для сохранения
LOCAL_BUILD_PATH = BUILD_PATH

# Лог-файл
LOG_FILE = os.path.join("logs", "download_trbonet.log")

# Таймаут для скачивания (сек)
DOWNLOAD_TIMEOUT = 600

# Размер чанка для скачивания (байт)
CHUNK_SIZE = 8192


# ============================================================================
# ЛОГГИРОВАНИЕ
# ============================================================================

def log_message(message: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}"
    print(log_entry)

    try:
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), LOG_FILE)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
    except:
        pass


# ============================================================================
# ОСНОВНЫЕ ФУНКЦИИ
# ============================================================================

def build_download_url(version: str) -> str:
    """
    Формирует URL для скачивания архива.

    Args:
        version: Версия TRBOnet (например, 6.5.0.9140)

    Returns:
        Полный URL для скачивания
    """
    return f"{BASE_URL}/{version}/TRBOnet.Enterprise_{version}.zip"


def download_file(url: str, destination_path: str) -> Tuple[bool, str]:
    """
    Скачивает файл по URL с отображением прогресса.

    Args:
        url: URL для скачивания
        destination_path: Путь для сохранения файла

    Returns:
        Кортеж (успех, сообщение)
    """
    log_message(f"Скачивание файла...", "INFO")
    log_message(f"  URL: {url}", "INFO")
    log_message(f"  Назначение: {destination_path}", "INFO")

    try:
        # Проверяем, существует ли уже файл
        if os.path.exists(destination_path):
            log_message(f"  Файл уже существует: {destination_path}", "WARNING")
            log_message("  Удаляем существующий файл...", "INFO")
            os.remove(destination_path)

        # Создаём папку назначения, если её нет
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)

        # Скачиваем файл с прогрессом
        log_message("  Начинаем скачивание... (это может занять несколько минут)", "INFO")

        response = requests.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT)
        response.raise_for_status()  # Проверяем статус ответа

        # Получаем размер файла для прогресса
        total_size = int(response.headers.get('content-length', 0))

        downloaded = 0
        with open(destination_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Показываем прогресс каждые 10%
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        if int(percent) % 10 == 0 and int(percent) != 0:
                            log_message(f"    Прогресс: {int(percent)}% ({downloaded // (1024*1024)} МБ из {total_size // (1024*1024)} МБ)", "INFO")

        # Проверяем, что файл скачался
        if os.path.isfile(destination_path):
            file_size = os.path.getsize(destination_path) / (1024 * 1024)
            log_message(f"✅ Файл скачан успешно (размер: {file_size:.2f} МБ)", "SUCCESS")
            return True, f"Файл скачан в {destination_path}"
        else:
            error_msg = "Файл не найден после скачивания"
            log_message(f"❌ {error_msg}", "ERROR")
            return False, error_msg

    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            error_msg = f"Файл не найден на сервере (404). Проверьте версию: {url}"
        else:
            error_msg = f"HTTP ошибка {response.status_code}: {e}"
        log_message(f"❌ {error_msg}", "ERROR")
        return False, error_msg

    except requests.exceptions.ConnectionError:
        error_msg = "Ошибка подключения к серверу. Проверьте интернет-соединение."
        log_message(f"❌ {error_msg}", "ERROR")
        return False, error_msg

    except requests.exceptions.Timeout:
        error_msg = f"Таймаут при скачивании (превышено {DOWNLOAD_TIMEOUT} сек)"
        log_message(f"❌ {error_msg}", "ERROR")
        return False, error_msg

    except Exception as e:
        error_msg = f"Ошибка при скачивании: {e}"
        log_message(f"❌ {error_msg}", "ERROR")
        return False, error_msg


def extract_archive(archive_path: str, extract_dir: str) -> Tuple[bool, str]:
    """
    Распаковывает ZIP-архив в указанную папку.

    Args:
        archive_path: Полный путь к архиву
        extract_dir: Папка для распаковки

    Returns:
        Кортеж (успех, сообщение)
    """
    log_message(f"Распаковка архива...", "INFO")
    log_message(f"  Архив: {archive_path}", "INFO")
    log_message(f"  Папка распаковки: {extract_dir}", "INFO")

    try:
        if not os.path.isfile(archive_path):
            error_msg = f"Архив не существует: {archive_path}"
            log_message(f"❌ {error_msg}", "ERROR")
            return False, error_msg

        if not os.path.exists(extract_dir):
            log_message(f"  Создаём папку для распаковки: {extract_dir}", "INFO")
            os.makedirs(extract_dir, exist_ok=True)

        if not zipfile.is_zipfile(archive_path):
            error_msg = f"Файл не является ZIP-архивом: {archive_path}"
            log_message(f"❌ {error_msg}", "ERROR")
            return False, error_msg

        log_message("  Распаковка... (может занять некоторое время)", "INFO")

        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            total_files = len(file_list)
            log_message(f"  Файлов в архиве: {total_files}", "INFO")
            zip_ref.extractall(extract_dir)

        log_message(f"✅ Архив успешно распакован (файлов: {total_files})", "SUCCESS")
        return True, f"Архив распакован в {extract_dir}"

    except Exception as e:
        error_msg = f"Ошибка при распаковке: {e}"
        log_message(f"❌ {error_msg}", "ERROR")
        return False, error_msg


def delete_file(file_path: str, file_description: str = "Файл") -> Tuple[bool, str]:
    """
    Удаляет указанный файл.

    Args:
        file_path: Полный путь к файлу
        file_description: Описание файла для лога

    Returns:
        Кортеж (успех, сообщение)
    """
    log_message(f"Удаление {file_description}...", "INFO")
    log_message(f"  Файл: {file_path}", "INFO")

    try:
        if not os.path.isfile(file_path):
            log_message(f"  {file_description} уже удалён или не существует", "WARNING")
            return True, f"{file_description} уже удалён"

        os.remove(file_path)

        if not os.path.isfile(file_path):
            log_message(f"✅ {file_description} успешно удалён", "SUCCESS")
            return True, f"{file_description} удалён"
        else:
            error_msg = f"Не удалось удалить {file_description}"
            log_message(f"❌ {error_msg}", "ERROR")
            return False, error_msg

    except Exception as e:
        error_msg = f"Ошибка при удалении {file_description}: {e}"
        log_message(f"❌ {error_msg}", "ERROR")
        return False, error_msg


# ============================================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================================

def main():
    log_message("=" * 80, "INFO")
    log_message("ЗАПУСК АВТОМАТИЧЕСКОГО СКАЧИВАНИЯ И РАСПАКОВКИ TRBOnet", "INFO")
    log_message("=" * 80, "INFO")

    errors = []

    # Получаем версию из аргументов
    if len(sys.argv) < 2:
        log_message("❌ Версия не указана. Использование: python download_build.py <версия>", "ERROR")
        log_message("   Пример: python download_build.py 6.5.0.9140", "INFO")
        sys.exit(1)

    version = sys.argv[1]
    log_message(f"Целевая версия: {version}", "INFO")

    # Формируем URL и пути
    download_url = build_download_url(version)
    archive_name = f"TRBOnet.Enterprise_{version}.zip"
    local_archive_path = os.path.join(LOCAL_BUILD_PATH, archive_name)

    log_message(f"URL для скачивания: {download_url}", "INFO")
    log_message(f"Локальный путь: {local_archive_path}", "INFO")

    # Шаг 1: Скачивание архива
    log_message("\n📌 ШАГ 1: Скачивание архива", "INFO")
    log_message("-" * 40, "INFO")

    success, message = download_file(download_url, local_archive_path)

    if not success:
        errors.append(message)
        log_message(f"❌ Скачивание не удалось: {message}", "ERROR")
        sys.exit(1)

    # Шаг 2: Распаковка архива
    log_message("\n📌 ШАГ 2: Распаковка архива", "INFO")
    log_message("-" * 40, "INFO")

    success, message = extract_archive(local_archive_path, LOCAL_BUILD_PATH)

    if not success:
        errors.append(message)
        log_message(f"❌ Распаковка не удалась: {message}", "ERROR")
        sys.exit(1)

    # Шаг 3: Удаление архива после распаковки
    log_message("\n📌 ШАГ 3: Удаление архива", "INFO")
    log_message("-" * 40, "INFO")

    success, message = delete_file(local_archive_path, "Архив")

    if not success:
        errors.append(message)
        log_message(f"⚠️ Не удалось удалить архив: {message}", "WARNING")

    # Шаг 4: Удаление файла NeocomLTD_EULA.rtf
    log_message("\n📌 ШАГ 4: Удаление NeocomLTD_EULA.rtf", "INFO")
    log_message("-" * 40, "INFO")

    eula_path = os.path.join(LOCAL_BUILD_PATH, "NeocomLTD_EULA.rtf")
    success, message = delete_file(eula_path, "NeocomLTD_EULA.rtf")

    if not success:
        errors.append(message)
        log_message(f"⚠️ Не удалось удалить NeocomLTD_EULA.rtf: {message}", "WARNING")

    # Выводим итог
    log_message("\n" + "=" * 80, "INFO")

    if not errors:
        log_message("✅ ОПЕРАЦИЯ ВЫПОЛНЕНА УСПЕШНО!", "SUCCESS")
        log_message(f"   Версия: {version}", "SUCCESS")
        log_message(f"   URL: {download_url}", "SUCCESS")
        log_message(f"   Папка назначения: {LOCAL_BUILD_PATH}", "SUCCESS")
        log_message(f"   Архив распакован и удалён", "SUCCESS")
        log_message(f"   Файл NeocomLTD_EULA.rtf удалён", "SUCCESS")
    else:
        log_message("⚠️ ОПЕРАЦИЯ ВЫПОЛНЕНА С ОШИБКАМИ!", "WARNING")
        for error in errors:
            log_message(f"  - {error}", "WARNING")
        sys.exit(1)

    log_message("=" * 80, "INFO")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_message("⚠️ Операция прервана пользователем", "WARNING")
        sys.exit(0)
    except Exception as e:
        log_message(f"❌ Критическая ошибка: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1)