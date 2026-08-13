"""
Автоматизация УСТАНОВКИ TRBOnet
Принимает версию из аргументов командной строки
"""

import os
import sys
import time
import ctypes
from typing import List, Tuple, Optional
from datetime import datetime
import psutil

# Импортируем фикс кодировки
import fix_encoding  # noqa

# Импортируем общую конфигурацию
from config import BUILD_PATH, APPS_TO_CHECK, INSTALL_OPTION, SILENT_INSTALL


# ============================================================================
# КОНСТАНТЫ
# ============================================================================

LOG_FILE = os.path.join("logs", "install_trbonet.log")


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
# ВСЕ ФУНКЦИИ (БЕЗ ИЗМЕНЕНИЙ)
# ============================================================================

def find_installer(build_path: str, version: str) -> Optional[str]:
    log_message(f"Поиск установочного файла...", "INFO")
    log_message(f"  Папка: {build_path}", "INFO")
    log_message(f"  Версия: {version}", "INFO")

    try:
        if not os.path.exists(build_path):
            log_message(f"❌ Папка не существует: {build_path}", "ERROR")
            return None

        installer_name = f"TRBOnet.Enterprise_{version}.exe"
        full_path = os.path.join(build_path, installer_name)

        if os.path.isfile(full_path):
            log_message(f"✅ Найден установочный файл: {full_path}", "SUCCESS")
            return full_path

        log_message(f"  Точное совпадение не найдено, ищем по шаблону...", "INFO")

        import glob
        pattern = os.path.join(build_path, f"TRBOnet.Enterprise_{version}*.exe")
        matches = glob.glob(pattern)

        if matches:
            found_file = matches[0]
            log_message(f"✅ Найден установочный файл: {found_file}", "SUCCESS")
            return found_file

        log_message(f"❌ Установочный файл не найден", "ERROR")
        return None

    except Exception as e:
        log_message(f"❌ Ошибка при поиске установочного файла: {e}", "ERROR")
        return None


def run_installer(installer_path: str, install_option: str = "local",
                  silent: bool = True) -> Tuple[bool, str]:
    log_message(f"Запуск установки TRBOnet...", "INFO")
    log_message(f"  Файл: {installer_path}", "INFO")
    log_message(f"  Опция: {install_option}", "INFO")
    log_message(f"  Тихий режим: {silent}", "INFO")

    log_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "logs",
        f"install_log_{datetime.now().strftime('%H%M%S')}.txt"
    )

    args = f'/exebasicui /exelog "{log_path}" /norestart'

    if silent:
        args += ' /quiet /qn'

    if install_option in ["local", "server", "redundant"]:
        args += ' InstallMode="Custom" INSTALLLEVEL="100"'

    log_message(f"  Аргументы: {args}", "INFO")

    try:
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", installer_path, args,
            os.path.dirname(installer_path), 0
        )

        if result <= 32:
            error_msg = f"Ошибка запуска установщика: код {result}"
            log_message(f"❌ {error_msg}", "ERROR")
            if result == 5:
                error_msg += " (Отказ в доступе)"
            elif result == 2:
                error_msg += " (Файл не найден)"
            elif result == 740:
                error_msg += " (Требуются права администратора)"
            return False, error_msg

        log_message(f"✅ Процесс установки запущен (Handle: {result})", "SUCCESS")

        log_message("⏳ Ожидание завершения установки...", "INFO")

        installer_pid = None
        installer_name = os.path.basename(installer_path)

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] == installer_name:
                    installer_pid = proc.info['pid']
                    log_message(f"  Найден процесс установщика (PID: {installer_pid})", "INFO")
                    break
            except:
                pass

        if not installer_pid:
            log_message("⚠️ Не удалось найти процесс установщика", "WARNING")

        msiexec_pid = None
        max_attempts = 20

        for attempt in range(max_attempts):
            for proc in psutil.process_iter(['pid', 'name', 'ppid']):
                try:
                    if proc.info['name'].lower() == 'msiexec.exe':
                        if installer_pid and proc.info['ppid'] == installer_pid:
                            msiexec_pid = proc.info['pid']
                            log_message(f"  Обнаружен дочерний процесс msiexec (PID: {msiexec_pid})", "INFO")
                            break
                        elif not installer_pid:
                            msiexec_pid = proc.info['pid']
                            log_message(f"  Обнаружен процесс msiexec (PID: {msiexec_pid})", "INFO")
                            break
                except:
                    pass

            if msiexec_pid:
                break
            time.sleep(0.5)

        if not msiexec_pid:
            log_message("⚠️ Процесс msiexec не обнаружен. Возможно, установка не запустилась.", "WARNING")
            return False, "Процесс msiexec не обнаружен"

        max_wait = 600
        elapsed = 0

        while elapsed < max_wait:
            time.sleep(3)
            elapsed += 3

            msiexec_running = False
            try:
                proc = psutil.Process(msiexec_pid)
                if proc.is_running():
                    msiexec_running = True
            except psutil.NoSuchProcess:
                msiexec_running = False
            except:
                pass

            if not msiexec_running:
                log_message(f"✅ Процесс msiexec (PID: {msiexec_pid}) завершился через {elapsed} секунд", "SUCCESS")
                break

            if elapsed % 15 == 0:
                log_message(f"  Установка выполняется... ({elapsed} сек)", "INFO")
        else:
            log_message(f"⚠️ Таймаут: msiexec не завершился за {max_wait} секунд", "WARNING")
            return False, f"Таймаут: msiexec не завершился за {max_wait} сек"

        log_message("✅ Установка успешно завершена", "SUCCESS")
        return True, "Установка выполнена успешно"

    except Exception as e:
        error_msg = f"Исключение при запуске установщика: {e}"
        log_message(f"❌ {error_msg}", "ERROR")
        return False, error_msg


def check_apps_in_registry(app_names: List[str]) -> Tuple[bool, List[str], List[str]]:
    import winreg

    log_message("Проверка установки через реестр...", "INFO")

    found_apps = []
    missing_apps = []

    try:
        reg_path = r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
            index = 0
            installed_products = []

            while True:
                try:
                    subkey_name = winreg.EnumKey(key, index)
                    subkey_path = f"{reg_path}\\{subkey_name}"

                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey_path) as subkey:
                        try:
                            display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                            installed_products.append(display_name)
                        except:
                            pass

                    index += 1
                except WindowsError:
                    break

        for app_name in app_names:
            found = False
            for product in installed_products:
                if app_name.lower() in product.lower() or "TRBOnet" in product:
                    if "TRBOnet" in app_name or "TRBOnet" in product:
                        found = True
                        break

            if found:
                found_apps.append(app_name)
                log_message(f"  ✅ Найден в реестре: {app_name}", "SUCCESS")
            else:
                missing_apps.append(app_name)
                log_message(f"  ❌ Не найден в реестре: {app_name}", "WARNING")

    except Exception as e:
        log_message(f"  Ошибка при проверке реестра: {e}", "WARNING")
        missing_apps = app_names.copy()

    all_installed = len(missing_apps) == 0
    return all_installed, found_apps, missing_apps


# ============================================================================
# ОСНОВНАЯ ФУНКЦИЯ (убрана проверка прав)
# ============================================================================

def main():
    log_message("=" * 80, "INFO")
    log_message("ЗАПУСК АВТОМАТИЧЕСКОЙ УСТАНОВКИ TRBOnet", "INFO")
    log_message("=" * 80, "INFO")

    log_message("НАСТРОЙКИ:", "INFO")
    log_message(f"  Путь к сборкам: {BUILD_PATH}", "INFO")
    log_message(f"  Опция установки: {INSTALL_OPTION}", "INFO")
    log_message(f"  Тихий режим: {SILENT_INSTALL}", "INFO")
    log_message(f"  Приложения для проверки: {', '.join(APPS_TO_CHECK)}", "INFO")

    errors = []

    log_message("✅ Скрипт запущен с правами администратора", "SUCCESS")

    # Получаем версию из аргументов
    if len(sys.argv) < 2:
        log_message("❌ Версия не указана. Использование: python install.py <версия>", "ERROR")
        log_message("   Пример: python install.py 6.5.0.9140", "INFO")
        sys.exit(1)

    version = sys.argv[1]
    log_message(f"Версия для установки: {version}", "INFO")

    # Поиск установочного файла
    log_message("\n📌 ШАГ 1: Поиск установочного файла", "INFO")
    log_message("-" * 40, "INFO")

    installer_path = find_installer(BUILD_PATH, version)

    if not installer_path:
        log_message(f"❌ Установочный файл не найден. Завершение.", "ERROR")
        sys.exit(1)

    # Запуск установки
    log_message("\n📌 ШАГ 2: Установка TRBOnet", "INFO")
    log_message("-" * 40, "INFO")

    success, message = run_installer(installer_path, INSTALL_OPTION, SILENT_INSTALL)

    if not success:
        errors.append(message)
        log_message(f"❌ Установка не удалась: {message}", "ERROR")
        sys.exit(1)

    # Проверка установленных приложений
    log_message("\n📌 ШАГ 3: Проверка установленных приложений", "INFO")
    log_message("-" * 40, "INFO")

    log_message("  Ожидание запуска приложений...", "INFO")
    time.sleep(5)

    all_installed, found, missing = check_apps_in_registry(APPS_TO_CHECK)

    if not all_installed:
        errors.append(f"Не установлены приложения: {', '.join(missing)}")

    # Вывод итога
    log_message("\n" + "=" * 80, "INFO")

    if all_installed and not errors:
        log_message("✅ УСТАНОВКА ВЫПОЛНЕНА УСПЕШНО!", "SUCCESS")
        log_message(f"   Версия: {version}", "SUCCESS")
        log_message(f"   Опция установки: {INSTALL_OPTION}", "SUCCESS")
        log_message(f"   Установлены приложения: {', '.join(found)}", "SUCCESS")
    elif all_installed and errors:
        log_message("⚠️ УСТАНОВКА ВЫПОЛНЕНА, НО ЕСТЬ ПРЕДУПРЕЖДЕНИЯ!", "WARNING")
        for error in errors:
            log_message(f"  - {error}", "WARNING")
    else:
        log_message("❌ УСТАНОВКА НЕ УДАЛАСЬ!", "ERROR")
        for error in errors:
            log_message(f"  - {error}", "ERROR")
        sys.exit(1)

    log_message("=" * 80, "INFO")


if __name__ == "__main__":
    try:
        import psutil
    except ImportError:
        print("❌ Не установлена библиотека 'psutil'.")
        print("   Установите её командой: pip install psutil")
        sys.exit(1)

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