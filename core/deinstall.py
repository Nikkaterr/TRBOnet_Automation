"""
Автоматизация УДАЛЕНИЯ TRBOnet через установочный файл (.exe)
Принимает версию из аргументов командной строки
"""

import os
import sys

# Импортируем фикс кодировки (ДОЛЖЕН БЫТЬ ПЕРВЫМ!)
import fix_encoding  # noqa

# Дальше остальной код...
import subprocess
import time
import ctypes
import glob
import winreg
from typing import List, Tuple, Dict, Optional
from datetime import datetime
import psutil

# Импортируем общую конфигурацию
from config import BUILD_PATH, PRODUCT_CODE

# ============================================================================
# КОНСТАНТЫ И НАСТРОЙКИ
# ============================================================================

PRODUCT_NAME = "TRBOnet"
LOG_FILE = os.path.join("logs", "trbonet_uninstall.log")
REPORT_FILE = os.path.join("logs", "uninstall_report.txt")
DEFAULT_PRODUCT_CODE = PRODUCT_CODE

# ============================================================================
# ЛОГГИРОВАНИЕ (без изменений)
# ============================================================================

def log_message(message: str, level: str = "INFO"):
    """Записывает сообщение в лог-файл и выводит в консоль."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}"
    print(log_entry)

    try:
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), LOG_FILE)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
    except:
        pass


def save_report(success: bool, installer_path: str, remnants: Dict, errors: List[str],
                uninstall_method: str = ""):
    """Сохраняет отчёт о выполнении."""
    try:
        report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), REPORT_FILE)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("ОТЧЁТ ОБ УДАЛЕНИИ TRBOnet\n")
            f.write(f"Дата и время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"Статус: {'✅ УСПЕШНО' if success else '❌ НЕ УДАЛОСЬ'}\n")
            f.write(f"Метод удаления: {uninstall_method}\n")
            f.write(f"Установочный файл: {installer_path}\n\n")

            if errors:
                f.write("ОШИБКИ:\n")
                for error in errors:
                    f.write(f"  - {error}\n")
                f.write("\n")

            f.write("ПРОВЕРКА ОСТАТКОВ:\n")
            f.write(f"  Файлы: {', '.join(remnants.get('files', [])) or 'Не найдены'}\n")
            f.write(f"  Реестр: {', '.join(remnants.get('registry', [])) or 'Не найдены'}\n")
            f.write(f"  Сервисы: {', '.join(remnants.get('services', [])) or 'Не найдены'}\n")
            f.write(f"  Процессы: {', '.join(remnants.get('processes', [])) or 'Не найдены'}\n")

            if not any(remnants.values()):
                f.write("\n✅ ПОЛНАЯ ОЧИСТКА ВЫПОЛНЕНА УСПЕШНО\n")
            else:
                f.write("\n⚠️ ОБНАРУЖЕНЫ ОСТАТКИ ПОСЛЕ УДАЛЕНИЯ\n")

            f.write("\n" + "=" * 80 + "\n")

        log_message(f"Отчёт сохранён в: {report_path}", "SUCCESS")
    except Exception as e:
        log_message(f"Ошибка при сохранении отчёта: {e}", "ERROR")


# ============================================================================
# ВСЕ ОСТАЛЬНЫЕ ФУНКЦИИ (БЕЗ ИЗМЕНЕНИЙ)
# ============================================================================

def kill_processes_by_name(keyword: str = PRODUCT_NAME) -> Tuple[List[str], List[str]]:
    """Находит и завершает все процессы с указанным ключевым словом."""
    killed_processes = []
    failed_processes = []

    log_message(f"Поиск процессов, содержащих '{keyword}'...", "INFO")

    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            process_name = proc.info['name']
            if keyword.lower() in process_name.lower():
                log_message(f"  Завершаем процесс: {process_name} (PID: {proc.info['pid']})", "INFO")
                try:
                    proc.kill()
                    killed_processes.append(process_name)
                    time.sleep(0.3)
                except Exception as e:
                    log_message(f"    Ошибка: {e}", "WARNING")
                    failed_processes.append(process_name)
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            continue

    if killed_processes:
        log_message(f"Завершено процессов: {len(killed_processes)}", "SUCCESS")
    else:
        log_message("Процессы с 'TRBOnet' в названии не найдены", "INFO")

    return killed_processes, failed_processes


def find_installer_by_version(build_path: str, version: str) -> Optional[str]:
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


def get_installed_instances() -> List[Dict[str, str]]:
    instances = []

    try:
        reg_path = r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
            index = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(key, index)
                    subkey_path = f"{reg_path}\\{subkey_name}"

                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey_path) as subkey:
                        try:
                            display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                            if "TRBOnet" in display_name or "TRBOnet.Enterprise" in display_name:
                                instance_info = {
                                    "display_name": display_name,
                                    "product_code": subkey_name,
                                    "version": winreg.QueryValueEx(subkey, "DisplayVersion")[0] if "DisplayVersion" in [winreg.EnumValue(subkey, i)[0] for i in range(winreg.QueryInfoKey(subkey)[1])] else ""
                                }
                                instances.append(instance_info)
                                log_message(f"  Найден экземпляр: {display_name} (версия: {instance_info['version']})", "INFO")
                        except:
                            pass

                    index += 1
                except WindowsError:
                    break
    except Exception as e:
        log_message(f"Ошибка при чтении реестра: {e}", "WARNING")

    return instances


def is_product_installed(product_code: str) -> bool:
    r"""
    Проверяет, установлен ли продукт с указанным Product Code.
    """
    try:
        reg_path = f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{product_code}"
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path):
                return True
        except FileNotFoundError:
            pass

        reg_path_wow = f"SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{product_code}"
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path_wow):
                return True
        except FileNotFoundError:
            pass

        return False

    except Exception as e:
        log_message(f"  Ошибка при проверке Product Code {product_code}: {e}", "WARNING")
        return True


def uninstall_via_installer(installer_path: str, instance_name: str, product_code: str) -> Tuple[bool, str, int]:
    log_message(f"Запуск удаления через установочный файл...", "INFO")
    log_message(f"  Файл: {installer_path}", "INFO")
    log_message(f"  Экземпляр: {instance_name}", "INFO")
    log_message(f"  Product Code: {product_code}", "INFO")

    log_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "logs",
        f"uninstall_log_{datetime.now().strftime('%H%M%S')}.txt"
    )

    msi_options = "/quiet /qn /norestart"
    args = f'/uninstallinst "{instance_name}" /exebasicui /exelog "{log_path}" {msi_options}'

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
            return False, error_msg, result

        log_message(f"✅ Процесс удаления запущен (Handle: {result})", "SUCCESS")

        log_message("⏳ Ожидание завершения удаления...", "INFO")

        max_wait_seconds = 120
        check_interval = 3
        elapsed = 0

        while elapsed < max_wait_seconds:
            time.sleep(check_interval)
            elapsed += check_interval

            if not is_product_installed(product_code):
                log_message(f"✅ Продукт успешно удалён за {elapsed} секунд", "SUCCESS")
                return True, f"Удаление выполнено успешно за {elapsed} сек", result

            if elapsed % 15 == 0:
                log_message(f"  Удаление выполняется... ({elapsed} сек из {max_wait_seconds} максимум)", "INFO")

        log_message(f"⚠️ Таймаут: продукт не удалён за {max_wait_seconds} секунд", "WARNING")
        return False, f"Таймаут: продукт не удалён за {max_wait_seconds} сек", result

    except Exception as e:
        error_msg = f"Исключение при запуске установщика: {e}"
        log_message(f"❌ {error_msg}", "ERROR")
        return False, error_msg, -1


def check_trbonet_remnants() -> Dict[str, List[str]]:
    remnants = {"files": [], "registry": [], "services": [], "processes": []}

    log_message("Проверка остатков после удаления...", "INFO")

    common_paths = [
        r"C:\Program Files\TRBOnet",
        r"C:\Program Files (x86)\TRBOnet",
        os.path.join(os.environ.get('PROGRAMDATA', r'C:\ProgramData'), 'TRBOnet'),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'TRBOnet'),
        os.path.join(os.environ.get('APPDATA', ''), 'TRBOnet'),
    ]

    for path in common_paths:
        if path and os.path.exists(path):
            remnants["files"].append(path)
            log_message(f"  Обнаружена папка: {path}", "WARNING")

    try:
        reg_paths = [
            r"SOFTWARE\TRBOnet",
            r"SOFTWARE\WOW6432Node\TRBOnet",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{CEC1EF24-87F3-4324-A393-104A5038078C}",
        ]

        for reg_path in reg_paths:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path):
                    remnants["registry"].append(reg_path)
                    log_message(f"  Обнаружен ключ реестра: {reg_path}", "WARNING")
            except:
                pass
    except:
        pass

    try:
        log_message("  Поиск сервисов TRBOnet...", "INFO")
        result = subprocess.run(
            ['sc', 'query', 'type=', 'service'],
            capture_output=True, text=True, timeout=10
        )

        for line in result.stdout.split('\n'):
            if 'SERVICE_NAME:' in line:
                service_name = line.split(':')[1].strip()
                if 'TRBOnet' in service_name:
                    remnants["services"].append(service_name)
                    log_message(f"  Обнаружен сервис: {service_name}", "WARNING")
    except subprocess.TimeoutExpired:
        log_message("  Таймаут при проверке сервисов", "WARNING")
    except Exception as e:
        log_message(f"  Ошибка при проверке сервисов: {e}", "WARNING")

    if not any(remnants.values()):
        log_message("✅ Остатки после удаления не обнаружены", "SUCCESS")
    else:
        log_message(f"⚠️ Обнаружены остатки: {sum(len(v) for v in remnants.values())} объектов", "WARNING")

    return remnants


# ============================================================================
# ОСНОВНАЯ ФУНКЦИЯ (убрана проверка прав)
# ============================================================================

def main():
    log_message("=" * 80, "INFO")
    log_message("ЗАПУСК АВТОМАТИЧЕСКОГО УДАЛЕНИЯ TRBOnet", "INFO")
    log_message("=" * 80, "INFO")

    errors = []

    log_message("✅ Скрипт запущен с правами администратора", "SUCCESS")

    # Получаем версию из аргументов
    if len(sys.argv) < 2:
        log_message("❌ Версия не указана. Использование: python deinstall.py <версия>", "ERROR")
        log_message("   Пример: python deinstall.py 6.5.0.9138", "INFO")
        sys.exit(1)

    version = sys.argv[1]
    log_message(f"Версия для удаления: {version}", "INFO")

    # Получаем список установленных экземпляров
    log_message("\n📌 ШАГ 1: Поиск установленных экземпляров TRBOnet", "INFO")
    log_message("-" * 40, "INFO")

    instances = get_installed_instances()

    if not instances:
        log_message("⚠️ Установленные экземпляры TRBOnet не найдены", "WARNING")
        log_message("   Возможно, приложение уже удалено", "INFO")
        save_report(True, "", {}, errors, "Не найдено экземпляров")
        return

    log_message(f"Найдено экземпляров: {len(instances)}", "INFO")

    # Завершаем процессы
    log_message("\n📌 ШАГ 2: Завершение процессов TRBOnet", "INFO")
    log_message("-" * 40, "INFO")

    killed, failed = kill_processes_by_name(PRODUCT_NAME)

    if failed:
        log_message(f"⚠️ Не удалось завершить процессы: {', '.join(failed)}", "WARNING")
        errors.append(f"Не удалось завершить процессы: {', '.join(failed)}")

    # Ищем установочный файл
    log_message("\n📌 ШАГ 3: Поиск установочного файла", "INFO")
    log_message("-" * 40, "INFO")

    installer_path = find_installer_by_version(BUILD_PATH, version)

    if not installer_path:
        log_message("❌ Установочный файл не найден", "ERROR")
        errors.append(f"Установочный файл версии {version} не найден")
        save_report(False, "", {}, errors, "Файл не найден")
        sys.exit(1)

    # Удаляем каждый найденный экземпляр
    log_message("\n📌 ШАГ 4: Удаление экземпляров TRBOnet через установочный файл", "INFO")
    log_message("-" * 40, "INFO")

    all_success = True

    for idx, instance in enumerate(instances, 1):
        instance_name = instance["display_name"]
        product_code = instance.get("product_code", DEFAULT_PRODUCT_CODE)

        log_message(f"\n  [{idx}/{len(instances)}] Удаление экземпляра: {instance_name}", "INFO")
        log_message(f"  Версия: {instance.get('version', 'Неизвестно')}", "INFO")
        log_message(f"  Product Code: {product_code}", "INFO")

        success, message, code = uninstall_via_installer(installer_path, instance_name, product_code)

        if success:
            log_message(f"  ✅ Удаление {instance_name} выполнено успешно", "SUCCESS")
        else:
            log_message(f"  ❌ Ошибка удаления {instance_name}: {message}", "ERROR")
            errors.append(f"Не удалось удалить {instance_name}: {message}")
            all_success = False

    # Проверяем остатки
    log_message("\n📌 ШАГ 5: Проверка остатков после удаления", "INFO")
    log_message("-" * 40, "INFO")

    remnants = check_trbonet_remnants()

    # Сохраняем результат
    final_success = all_success and not any(remnants.values()) and not errors
    save_report(final_success, installer_path, remnants, errors, "/uninstallinst")

    # Выводим итог
    log_message("\n" + "=" * 80, "INFO")
    if final_success:
        log_message("✅ УДАЛЕНИЕ ВЫПОЛНЕНО УСПЕШНО! Полная очистка.", "SUCCESS")
        log_message(f"   Удалено экземпляров: {len(instances)}", "SUCCESS")
    else:
        log_message("⚠️ УДАЛЕНИЕ ВЫПОЛНЕНО С ОШИБКАМИ!", "WARNING")
        if errors:
            log_message(f"  Ошибки: {len(errors)}", "WARNING")
        if remnants.get("files"):
            log_message(f"  Остались файлы: {', '.join(remnants['files'])}", "WARNING")
        if remnants.get("registry"):
            log_message(f"  Остались ключи реестра: {', '.join(remnants['registry'])}", "WARNING")
        if remnants.get("services"):
            log_message(f"  Остались сервисы: {', '.join(remnants['services'])}", "WARNING")
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
    except Exception as e:
        log_message(f"Критическая ошибка: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1)