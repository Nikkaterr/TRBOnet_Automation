"""
deinstall.py - Автоматизация УДАЛЕНИЯ TRBOnet

Режимы работы:
1. Без аргументов: удаляет найденную установленную версию через стандартные средства Windows (msiexec)
2. С версией: удаляет указанную версию через установочный файл
3. С флагом --force: принудительное удаление всех экземпляров
"""

import os
import sys
import subprocess
import time
import ctypes
import winreg
import re
import psutil
from typing import List, Tuple, Dict, Optional
from datetime import datetime

# Импортируем фикс кодировки
import fix_encoding  # noqa

# Импортируем общую конфигурацию
from config import PRODUCT_CODE, BUILD_PATH

# ============================================================================
# КОНСТАНТЫ И НАСТРОЙКИ
# ============================================================================

PRODUCT_NAME = "TRBOnet"
LOG_FILE = os.path.join("logs", "trbonet_uninstall.log")
REPORT_FILE = os.path.join("logs", "uninstall_report.txt")
DEFAULT_PRODUCT_CODE = PRODUCT_CODE

# Ключи реестра для поиска
REGISTRY_PATHS = [
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
]

# Папки для проверки остатков
REMNANT_PATHS = [
    r"C:\Program Files\TRBOnet",
    r"C:\Program Files (x86)\TRBOnet",
    r"C:\ProgramData\TRBOnet",
]


# ============================================================================
# ЛОГГИРОВАНИЕ
# ============================================================================

def log_message(message: str, level: str = "INFO"):
    """Записывает сообщение в лог-файл и выводит в консоль."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}"
    print(log_entry)

    try:
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), LOG_FILE)
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
    except Exception:
        pass


def save_report(success: bool, uninstall_method: str, instances: List[dict],
                errors: List[str], remnants: Dict):
    """Сохраняет отчёт о выполнении."""
    try:
        report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), REPORT_FILE)
        os.makedirs(os.path.dirname(report_path), exist_ok=True)

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("ОТЧЁТ ОБ УДАЛЕНИИ TRBOnet\n")
            f.write(f"Дата и время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"Статус: {'✅ УСПЕШНО' if success else '❌ НЕ УДАЛОСЬ'}\n")
            f.write(f"Метод удаления: {uninstall_method}\n\n")

            if instances:
                f.write("УДАЛЁННЫЕ ЭКЗЕМПЛЯРЫ:\n")
                for inst in instances:
                    f.write(f"  - {inst.get('display_name', 'Неизвестно')} ")
                    f.write(f"(версия: {inst.get('version', 'Неизвестно')})\n")
                f.write("\n")

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
# ПОИСК УСТАНОВЛЕННЫХ ЭКЗЕМПЛЯРОВ
# ============================================================================

def find_installed_instances() -> List[Dict[str, str]]:
    """
    Находит все установленные экземпляры TRBOnet в системе.

    Returns:
        List[Dict]: Список словарей с информацией об экземплярах
    """
    instances = []

    log_message("Поиск установленных экземпляров TRBOnet...", "INFO")

    # Регулярное выражение для проверки GUID формата {XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}
    guid_pattern = re.compile(r'^\{[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\}$')

    for reg_path in REGISTRY_PATHS:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                index = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, index)

                        # Пропускаем ключи, которые не являются GUID
                        # В Windows Installer Product Code всегда в формате GUID
                        if not guid_pattern.match(subkey_name):
                            index += 1
                            continue

                        subkey_path = f"{reg_path}\\{subkey_name}"

                        try:
                            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey_path) as subkey:
                                try:
                                    display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]

                                    # Проверяем, что это TRBOnet
                                    if "TRBOnet" in display_name or "TRBOnet.Enterprise" in display_name:
                                        instance_info = {
                                            "display_name": display_name,
                                            "product_code": subkey_name,
                                            "install_source": "",
                                            "install_location": "",
                                            "version": ""
                                        }

                                        # Пытаемся получить дополнительную информацию
                                        try:
                                            instance_info["version"] = winreg.QueryValueEx(subkey, "DisplayVersion")[0]
                                        except Exception:
                                            pass

                                        try:
                                            instance_info["install_source"] = winreg.QueryValueEx(subkey, "InstallSource")[0]
                                        except Exception:
                                            pass

                                        try:
                                            instance_info["install_location"] = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                                        except Exception:
                                            pass

                                        # Проверяем, есть ли уже такой экземпляр
                                        if not any(i["product_code"] == subkey_name for i in instances):
                                            instances.append(instance_info)
                                            log_message(f"  Найден экземпляр: {display_name} "
                                                      f"(версия: {instance_info['version']}, "
                                                      f"Product Code: {subkey_name})", "INFO")
                                except Exception:
                                    pass
                        except Exception:
                            pass

                        index += 1

                    except WindowsError:
                        break

        except Exception as e:
            log_message(f"Ошибка при доступе к реестру {reg_path}: {e}", "WARNING")
            continue

    if not instances:
        log_message("  ❌ Установленные экземпляры TRBOnet не найдены", "WARNING")
    else:
        log_message(f"  ✅ Найдено экземпляров: {len(instances)}", "SUCCESS")

    return instances


def find_instance_by_version(instances: List[Dict], version: str) -> Optional[Dict]:
    """
    Ищет экземпляр по версии.

    Args:
        instances: Список найденных экземпляров
        version: Версия для поиска

    Returns:
        Optional[Dict]: Найденный экземпляр или None
    """
    for instance in instances:
        if instance.get("version", "").startswith(version):
            return instance
    return None


# ============================================================================
# УДАЛЕНИЕ ЧЕРЕЗ СТАНДАРТНЫЕ СРЕДСТВА WINDOWS
# ============================================================================

def uninstall_via_msiexec(instance: Dict) -> Tuple[bool, str]:
    """
    Удаляет экземпляр через msiexec (стандартные средства Windows).

    Args:
        instance: Словарь с информацией об экземпляре

    Returns:
        Tuple[bool, str]: (успех, сообщение)
    """
    product_code = instance.get("product_code")
    display_name = instance.get("display_name", "Неизвестно")
    version = instance.get("version", "Неизвестно")

    log_message(f"Удаление через msiexec: {display_name}", "INFO")
    log_message(f"  Product Code: {product_code}", "INFO")
    log_message(f"  Версия: {version}", "INFO")

    if not product_code:
        return False, "Product Code не найден"

    # Проверяем, что Product Code это GUID
    guid_pattern = re.compile(r'^\{[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\}$')
    if not guid_pattern.match(product_code):
        log_message(f"  ⚠️ Product Code не является GUID: {product_code}", "WARNING")
        log_message(f"  Пропускаем этот экземпляр", "WARNING")
        return False, f"Неверный Product Code: {product_code}"

    # Формируем команду для msiexec
    cmd = [
        "msiexec",
        "/x", product_code,
        "/quiet",
        "/qn",
        "/norestart"
    ]

    log_message(f"  Команда: {' '.join(cmd)}", "DEBUG")

    try:
        # Запускаем msiexec и ждем завершения
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            check=False
        )

        # Проверяем результат
        if result.returncode == 0:
            log_message(f"  ✅ Удаление успешно завершено", "SUCCESS")
            return True, "Удаление через msiexec выполнено успешно"
        else:
            # Специальные коды ошибок msiexec
            error_messages = {
                0: "Успешно",
                1602: "Пользователь отменил установку",
                1603: "Критическая ошибка во время установки",
                1605: "Продукт не установлен",
                1618: "Другая установка уже выполняется",
                1619: "Не удалось открыть пакет установки",
                1635: "Не удалось открыть пакет",
                1638: "Другая версия уже установлена",
                1641: "Требуется перезагрузка",
                3010: "Требуется перезагрузка (успешно)",
            }

            error_msg = error_messages.get(result.returncode, f"Неизвестная ошибка (код {result.returncode})")

            # Если ошибка 1619, возможно продукт уже удален
            if result.returncode == 1619:
                log_message(f"  ⚠️ Пакет не найден. Возможно, продукт уже удален.", "WARNING")
                # Проверяем, существует ли еще этот Product Code в реестре
                if not is_product_installed(product_code):
                    log_message(f"  ✅ Продукт уже удален из системы", "SUCCESS")
                    return True, "Продукт уже удален"

            if result.returncode in [1641, 3010]:
                log_message(f"  ⚠️ Требуется перезагрузка для завершения удаления", "WARNING")
                return True, "Удаление выполнено, требуется перезагрузка"

            log_message(f"  ❌ Ошибка: {error_msg}", "ERROR")
            return False, f"Ошибка msiexec: {error_msg}"

    except subprocess.TimeoutExpired:
        log_message(f"  ❌ Таймаут удаления (5 минут)", "ERROR")
        return False, "Таймаут удаления"
    except Exception as e:
        log_message(f"  ❌ Ошибка: {e}", "ERROR")
        return False, f"Ошибка: {e}"


def is_product_installed(product_code: str) -> bool:
    """
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
    except Exception:
        return True  # В случае ошибки считаем, что продукт установлен


# ============================================================================
# УДАЛЕНИЕ ЧЕРЕЗ УСТАНОВОЧНЫЙ ФАЙЛ
# ============================================================================

def find_installer_by_version(version: str) -> Optional[str]:
    """
    Ищет установочный файл указанной версии.

    Args:
        version: Версия для поиска

    Returns:
        Optional[str]: Путь к установочному файлу или None
    """
    log_message(f"Поиск установочного файла для версии {version}...", "INFO")

    try:
        if not os.path.exists(BUILD_PATH):
            log_message(f"  ❌ Папка не существует: {BUILD_PATH}", "ERROR")
            return None

        # Ищем точное совпадение
        installer_name = f"TRBOnet.Enterprise_{version}.exe"
        full_path = os.path.join(BUILD_PATH, installer_name)

        if os.path.isfile(full_path):
            log_message(f"  ✅ Найден файл: {full_path}", "SUCCESS")
            return full_path

        # Ищем по маске
        import glob
        pattern = os.path.join(BUILD_PATH, f"TRBOnet.Enterprise_{version}*.exe")
        matches = glob.glob(pattern)

        if matches:
            found_file = matches[0]
            log_message(f"  ✅ Найден файл: {found_file}", "SUCCESS")
            return found_file

        log_message(f"  ❌ Установочный файл для версии {version} не найден", "ERROR")
        return None

    except Exception as e:
        log_message(f"  ❌ Ошибка при поиске: {e}", "ERROR")
        return None


def uninstall_via_installer(installer_path: str, instance_name: str) -> Tuple[bool, str]:
    """
    Удаляет через установочный файл.

    Args:
        installer_path: Путь к установочному файлу
        instance_name: Имя экземпляра для удаления

    Returns:
        Tuple[bool, str]: (успех, сообщение)
    """
    log_message(f"Удаление через установочный файл: {installer_path}", "INFO")
    log_message(f"  Экземпляр: {instance_name}", "INFO")

    log_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "logs",
        f"uninstall_log_{datetime.now().strftime('%H%M%S')}.txt"
    )

    # Формируем аргументы
    args = f'/uninstallinst "{instance_name}" /exebasicui /exelog "{log_path}" /quiet /qn /norestart'

    log_message(f"  Аргументы: {args}", "DEBUG")

    try:
        # Запускаем с правами администратора
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", installer_path, args,
            os.path.dirname(installer_path), 0
        )

        if result <= 32:
            error_msg = f"Ошибка запуска установщика: код {result}"
            log_message(f"  ❌ {error_msg}", "ERROR")

            if result == 5:
                error_msg += " (Отказ в доступе)"
            elif result == 2:
                error_msg += " (Файл не найден)"
            elif result == 740:
                error_msg += " (Требуются права администратора)"

            return False, error_msg

        log_message(f"  ✅ Процесс удаления запущен (Handle: {result})", "SUCCESS")

        # Ожидаем завершения
        log_message("  ⏳ Ожидание завершения удаления...", "INFO")

        max_wait = 120
        elapsed = 0

        # Проверяем, завершился ли процесс установщика
        installer_name = os.path.basename(installer_path)

        while elapsed < max_wait:
            time.sleep(3)
            elapsed += 3

            # Проверяем, есть ли процесс установщика
            installer_running = False
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'] == installer_name:
                        installer_running = True
                        break
                except Exception:
                    pass

            if not installer_running:
                log_message(f"  ✅ Процесс установщика завершился через {elapsed} секунд", "SUCCESS")
                return True, f"Удаление выполнено успешно за {elapsed} сек"

            if elapsed % 15 == 0:
                log_message(f"  Удаление выполняется... ({elapsed} сек)", "INFO")

        log_message(f"  ⚠️ Таймаут: процесс не завершился за {max_wait} секунд", "WARNING")
        return False, f"Таймаут: процесс не завершился за {max_wait} сек"

    except Exception as e:
        error_msg = f"Исключение: {e}"
        log_message(f"  ❌ {error_msg}", "ERROR")
        return False, error_msg


# ============================================================================
# ЗАВЕРШЕНИЕ ПРОЦЕССОВ И ОЧИСТКА
# ============================================================================

def kill_processes(keyword: str = PRODUCT_NAME) -> Tuple[List[str], List[str]]:
    """
    Находит и завершает все процессы с указанным ключевым словом.

    Returns:
        Tuple[List[str], List[str]]: (убитые процессы, не удалось убить)
    """
    killed = []
    failed = []

    log_message(f"Поиск и завершение процессов с '{keyword}'...", "INFO")

    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            process_name = proc.info['name']
            if keyword.lower() in process_name.lower():
                log_message(f"  Завершаем: {process_name} (PID: {proc.info['pid']})", "INFO")
                try:
                    proc.kill()
                    killed.append(process_name)
                    time.sleep(0.3)
                except Exception as e:
                    log_message(f"    Ошибка: {e}", "WARNING")
                    failed.append(process_name)
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            continue

    if killed:
        log_message(f"  ✅ Завершено процессов: {len(killed)}", "SUCCESS")
    else:
        log_message("  Процессы не найдены", "INFO")

    return killed, failed


def check_remnants() -> Dict[str, List[str]]:
    """
    Проверяет остатки после удаления.

    Returns:
        Dict: Словарь с найденными остатками
    """
    remnants = {"files": [], "registry": [], "services": [], "processes": []}

    log_message("Проверка остатков после удаления...", "INFO")

    # Проверка файлов и папок
    for path in REMNANT_PATHS:
        if os.path.exists(path):
            remnants["files"].append(path)
            log_message(f"  Обнаружена папка: {path}", "WARNING")

    # Проверка реестра
    try:
        reg_paths = [
            r"SOFTWARE\TRBOnet",
            r"SOFTWARE\WOW6432Node\TRBOnet",
        ]

        for reg_path in reg_paths:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path):
                    remnants["registry"].append(reg_path)
                    log_message(f"  Обнаружен ключ реестра: {reg_path}", "WARNING")
            except Exception:
                pass
    except Exception:
        pass

    # Проверка сервисов
    try:
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
    except Exception:
        pass

    if not any(remnants.values()):
        log_message("  ✅ Остатки не обнаружены", "SUCCESS")

    return remnants


# ============================================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================================

def main():
    """Основная функция удаления."""
    log_message("=" * 80, "INFO")
    log_message("ЗАПУСК АВТОМАТИЧЕСКОГО УДАЛЕНИЯ TRBOnet", "INFO")
    log_message("=" * 80, "INFO")

    errors = []
    instances = []
    uninstall_method = "Неизвестно"

    # Проверка прав администратора
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        if is_admin:
            log_message("✅ Скрипт запущен с правами администратора", "SUCCESS")
        else:
            log_message("⚠️ Скрипт запущен без прав администратора!", "WARNING")
            log_message("   Некоторые операции могут не выполниться", "WARNING")
    except Exception:
        pass

    # Разбор аргументов
    force_mode = "--force" in sys.argv
    version = None

    # Ищем версию в аргументах
    for arg in sys.argv[1:]:
        if arg != "--force" and not arg.startswith("-"):
            version = arg
            break

    # ШАГ 1: Поиск установленных экземпляров
    log_message("\n📌 ШАГ 1: Поиск установленных экземпляров", "INFO")
    log_message("-" * 40, "INFO")

    found_instances = find_installed_instances()

    if not found_instances:
        log_message("⚠️ Установленные экземпляры не найдены", "WARNING")
        save_report(True, "Не найдено экземпляров", [], errors, {})
        return

    # ШАГ 2: Завершение процессов
    log_message("\n📌 ШАГ 2: Завершение процессов TRBOnet", "INFO")
    log_message("-" * 40, "INFO")

    killed, failed = kill_processes(PRODUCT_NAME)
    if failed:
        errors.append(f"Не удалось завершить процессы: {', '.join(failed)}")

    # ШАГ 3: Выбор метода удаления
    log_message("\n📌 ШАГ 3: Удаление экземпляров", "INFO")
    log_message("-" * 40, "INFO")

    if version:
        # Удаление по версии через установочный файл
        log_message(f"Удаление указанной версии: {version}", "INFO")

        # Ищем экземпляр с такой версией
        instance = find_instance_by_version(found_instances, version)

        if not instance:
            log_message(f"❌ Экземпляр с версией {version} не найден", "ERROR")
            errors.append(f"Экземпляр с версией {version} не найден")
            save_report(False, "Версия не найдена", [], errors, {})
            sys.exit(1)

        # Ищем установочный файл
        installer_path = find_installer_by_version(version)

        if not installer_path:
            log_message(f"❌ Установочный файл для версии {version} не найден", "ERROR")
            errors.append(f"Установочный файл для версии {version} не найден")
            save_report(False, "Файл не найден", [], errors, {})
            sys.exit(1)

        # Удаляем через установочный файл
        success, message = uninstall_via_installer(installer_path, instance["display_name"])
        uninstall_method = f"/uninstallinst (версия {version})"

        if success:
            instances.append(instance)
        else:
            errors.append(message)

    else:
        # Автоматическое удаление через msiexec
        log_message("Автоматическое удаление всех найденных экземпляров через msiexec", "INFO")
        uninstall_method = "msiexec (автоматическое)"

        for instance in found_instances:
            success, message = uninstall_via_msiexec(instance)

            if success:
                instances.append(instance)
            else:
                errors.append(f"{instance['display_name']}: {message}")

    # ШАГ 4: Проверка остатков
    log_message("\n📌 ШАГ 4: Проверка остатков", "INFO")
    log_message("-" * 40, "INFO")

    remnants = check_remnants()

    # ШАГ 5: Сохранение отчета
    success = len(instances) > 0 and not errors and not any(remnants.values())
    save_report(success, uninstall_method, instances, errors, remnants)

    # Вывод итогов
    log_message("\n" + "=" * 80, "INFO")

    if success:
        log_message("✅ УДАЛЕНИЕ ВЫПОЛНЕНО УСПЕШНО!", "SUCCESS")
        log_message(f"   Удалено экземпляров: {len(instances)}", "SUCCESS")
        log_message(f"   Метод: {uninstall_method}", "SUCCESS")
    else:
        log_message("⚠️ УДАЛЕНИЕ ВЫПОЛНЕНО С ОШИБКАМИ!", "WARNING")

        if errors:
            log_message(f"  Ошибки: {len(errors)}", "WARNING")
            for error in errors:
                log_message(f"    - {error}", "WARNING")

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
    except KeyboardInterrupt:
        log_message("⚠️ Операция прервана пользователем", "WARNING")
        sys.exit(0)
    except Exception as e:
        log_message(f"❌ Критическая ошибка: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1)