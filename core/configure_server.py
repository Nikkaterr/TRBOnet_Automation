"""
Автоматизация НАСТРОЙКИ TRBOnet Server через pywinauto
Использует конфигурацию из config_auto_ids.py
Принимает версию из аргументов командной строки
"""

import os
import sys
import time
from typing import Optional
from datetime import datetime
from pywinauto.application import Application
from pywinauto import Desktop

# Импортируем фикс кодировки
import fix_encoding  # noqa

# Импортируем конфигурацию
from config_auto_ids import AUTO_IDS, DIALOG_TEXTS
from config import SERVER_EXE_PATH


# ============================================================================
# НАСТРАИВАЕМЫЕ ПАРАМЕТРЫ
# ============================================================================

# Максимальное время ожидания для операций (сек)
TIMEOUT = 30

# Задержка между действиями (сек)
SMALL_DELAY = 1
MEDIUM_DELAY = 2
LARGE_DELAY = 5

# ============================================================================
# КОНСТАНТЫ
# ============================================================================

LOG_FILE = os.path.join("logs", "configure_trbonet_server.log")
WINDOW_TITLE = "TRBOnet Enterprise 6.5 / Server"
DB_NAME_TEMPLATE = "TRBONET_{version}"


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
# ВСЕ ФУНКЦИИ (БЕЗ ИЗМЕНЕНИЙ — см. предыдущую версию)
# ============================================================================

def launch_app(app_path: str):
    log_message(f"Запуск приложения: {app_path}", "INFO")
    try:
        if not os.path.exists(app_path):
            log_message(f"❌ Файл не найден: {app_path}", "ERROR")
            return None
        app = Application(backend="uia").start(app_path)
        time.sleep(LARGE_DELAY)
        log_message("✅ Приложение запущено", "SUCCESS")
        return app
    except Exception as e:
        log_message(f"❌ Ошибка при запуске приложения: {e}", "ERROR")
        return None


def find_window(app, title: str, timeout: int = TIMEOUT):
    log_message(f"Поиск окна: '{title}'...", "INFO")
    try:
        window = app.window(title_re=title).wait('visible', timeout=timeout)
        log_message(f"✅ Окно найдено: '{title}'", "SUCCESS")
        return window
    except Exception as e:
        log_message(f"❌ Окно не найдено: {e}", "ERROR")
        return None


def get_auto_id(key: str) -> Optional[str]:
    auto_id = AUTO_IDS.get(key)
    if not auto_id:
        log_message(f"❌ Ключ '{key}' не найден в AUTO_IDS", "ERROR")
    return auto_id


def find_element_by_auto_id(window, auto_id: str, timeout: int = TIMEOUT):
    log_message(f"  Поиск элемента по AutomationId: '{auto_id}'", "INFO")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            all_elements = window.descendants()
            for elem in all_elements:
                try:
                    if hasattr(elem, 'element_info') and hasattr(elem.element_info, 'automation_id'):
                        elem_auto_id = elem.element_info.automation_id
                        if elem_auto_id == auto_id:
                            elem_name = elem.window_text() if hasattr(elem, 'window_text') else ""
                            log_message(f"    ✅ Найден: '{elem_name}'", "SUCCESS")
                            return elem
                except:
                    continue
            time.sleep(0.5)
        except Exception as e:
            log_message(f"  Ошибка при поиске: {e}", "WARNING")
            time.sleep(0.5)
    log_message(f"  ❌ Элемент с AutomationId '{auto_id}' не найден", "ERROR")
    return None


def click_by_key(window, key: str, timeout: int = TIMEOUT) -> bool:
    log_message(f"Клик по ключу: '{key}'", "INFO")
    element = find_element_by_auto_id(window, get_auto_id(key), timeout)
    if not element:
        log_message(f"❌ Не удалось найти элемент по ключу '{key}'", "ERROR")
        return False
    try:
        element.click_input()
        time.sleep(SMALL_DELAY)
        log_message(f"  ✅ Клик выполнен", "SUCCESS")
        return True
    except:
        try:
            element.click()
            time.sleep(SMALL_DELAY)
            log_message(f"  ✅ Клик выполнен", "SUCCESS")
            return True
        except Exception as e:
            log_message(f"  ❌ Ошибка при клике: {e}", "ERROR")
            return False


def set_combo_value_by_key(window, key: str, value: str, timeout: int = TIMEOUT) -> bool:
    auto_id = get_auto_id(key)
    if not auto_id:
        return False
    log_message(f"Поиск ComboBox по ключу: '{key}'", "INFO")
    log_message(f"  Устанавливаем значение: '{value}'", "INFO")
    combo_box = find_element_by_auto_id(window, auto_id, timeout)
    if not combo_box:
        log_message(f"  ❌ ComboBox не найден", "ERROR")
        return False
    try:
        combo_box.click_input()
        time.sleep(SMALL_DELAY)
        combo_box.type_keys("^a")
        time.sleep(SMALL_DELAY)
        combo_box.type_keys("{DEL}")
        time.sleep(SMALL_DELAY)
        combo_box.type_keys(value)
        time.sleep(SMALL_DELAY)
        combo_box.type_keys("{TAB}")
        time.sleep(SMALL_DELAY)
        log_message(f"  ✅ Значение '{value}' установлено", "SUCCESS")
        return True
    except Exception as e:
        log_message(f"  ❌ Ошибка при установке значения: {e}", "ERROR")
        return False


def wait_for_text(window, text: str, timeout: int = TIMEOUT) -> bool:
    log_message(f"  Ожидание текста: '{text}'...", "INFO")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            all_elements = window.descendants()
            for elem in all_elements:
                try:
                    elem_name = elem.window_text()
                    if text.lower() in elem_name.lower():
                        log_message(f"  ✅ Текст найден: '{text}'", "SUCCESS")
                        return True
                except:
                    continue
        except:
            pass
        time.sleep(0.5)
    log_message(f"  ❌ Текст не найден: '{text}'", "ERROR")
    return False


def wait_for_dialog_text(text: str, timeout: int = TIMEOUT) -> bool:
    log_message(f"  Ожидание текста в диалоге: '{text}'...", "INFO")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            desktop = Desktop(backend="uia")
            windows = desktop.windows(title_re=".*TRBOnet Enterprise.*")
            for win in windows:
                try:
                    all_elements = win.descendants()
                    for elem in all_elements:
                        try:
                            elem_name = elem.window_text()
                            if text.lower() in elem_name.lower():
                                log_message(f"  ✅ Текст найден в диалоге", "SUCCESS")
                                return True
                        except:
                            continue
                except:
                    continue
        except Exception as e:
            log_message(f"  Ошибка при поиске диалога: {e}", "WARNING")
        time.sleep(0.5)
    log_message(f"  ❌ Текст не найден: '{text}'", "ERROR")
    return False


def click_dialog_button(button_text: str, timeout: int = TIMEOUT) -> bool:
    log_message(f"  Поиск кнопки '{button_text}' в диалоге...", "INFO")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            desktop = Desktop(backend="uia")
            windows = desktop.windows(title_re=".*TRBOnet Enterprise.*")
            for win in windows:
                try:
                    all_elements = win.descendants()
                    for elem in all_elements:
                        try:
                            elem_name = elem.window_text()
                            elem_type = elem.element_info.control_type if hasattr(elem, 'element_info') else ""
                            if elem_name == button_text and "Button" in elem_type:
                                elem.click_input()
                                time.sleep(SMALL_DELAY)
                                log_message(f"  ✅ Кнопка '{button_text}' нажата", "SUCCESS")
                                return True
                        except:
                            continue
                except:
                    continue
        except Exception as e:
            log_message(f"  Ошибка при поиске кнопки: {e}", "WARNING")
        time.sleep(0.5)
    log_message(f"  ❌ Кнопка '{button_text}' не найдена", "ERROR")
    return False


def step_switch_to_database_tab(window) -> bool:
    log_message("Переход на вкладку Database...", "INFO")
    try:
        all_elements = window.descendants()
        tree_auto_id = get_auto_id("tree")
        if not tree_auto_id:
            return False
        tree = None
        for elem in all_elements:
            try:
                if hasattr(elem, 'element_info') and hasattr(elem.element_info, 'automation_id'):
                    if elem.element_info.automation_id == tree_auto_id:
                        tree = elem
                        log_message("  ✅ Найдено дерево", "SUCCESS")
                        break
            except:
                continue
        if not tree:
            log_message("  ❌ Дерево не найдено", "ERROR")
            return False
        tree_descendants = tree.descendants()
        database_item = None
        for elem in tree_descendants:
            try:
                elem_name = elem.window_text() if hasattr(elem, 'window_text') else ""
                elem_type = elem.element_info.control_type if hasattr(elem, 'element_info') else ""
                if elem_name == "Database" and "TreeItem" in elem_type:
                    database_item = elem
                    log_message("  ✅ Найден элемент 'Database'", "SUCCESS")
                    break
            except:
                continue
        if not database_item:
            log_message("  ❌ Элемент 'Database' не найден", "ERROR")
            return False
        database_item.click_input()
        time.sleep(MEDIUM_DELAY)
        log_message("  ✅ Клик по 'Database' выполнен", "SUCCESS")
        return True
    except Exception as e:
        log_message(f"  ❌ Ошибка при переходе на Database: {e}", "ERROR")
        return False


def step_switch_to_service_tab(window) -> bool:
    log_message("Переход на вкладку Service...", "INFO")
    try:
        all_elements = window.descendants()
        for elem in all_elements:
            try:
                elem_name = elem.window_text() if hasattr(elem, 'window_text') else ""
                elem_type = elem.element_info.control_type if hasattr(elem, 'element_info') else ""
                if elem_name == "Service" and "TreeItem" in elem_type:
                    elem.click_input()
                    time.sleep(MEDIUM_DELAY)
                    log_message("  ✅ Переход на Service выполнен", "SUCCESS")
                    return True
            except:
                continue
        log_message("  ❌ Элемент 'Service' не найден", "ERROR")
        return False
    except Exception as e:
        log_message(f"  ❌ Ошибка при переходе на Service: {e}", "ERROR")
        return False


def step_click_start_service(window) -> bool:
    log_message("Клик по 'Start service'...", "INFO")
    if click_by_key(window, "btn_start_service"):
        return True
    log_message("  Пробуем найти 'Start service' по имени...", "INFO")
    all_elements = window.descendants()
    for elem in all_elements:
        try:
            elem_name = elem.window_text()
            if elem_name == "Start service":
                elem.click_input()
                time.sleep(MEDIUM_DELAY)
                log_message("  ✅ Клик по 'Start service' выполнен", "SUCCESS")
                return True
        except:
            continue
    log_message("  ❌ 'Start service' не найден", "ERROR")
    return False


def step_wait_and_close_creation_dialog(db_name: str) -> bool:
    log_message(f"Ожидание диалога создания БД '{db_name}'...", "INFO")
    if not wait_for_dialog_text(DIALOG_TEXTS["creation_dialog"]):
        log_message("  ❌ Диалог создания БД не появился", "ERROR")
        return False
    if not click_dialog_button("OK"):
        log_message("  ❌ Кнопка OK не найдена", "ERROR")
        return False
    log_message("  ✅ Диалог закрыт", "SUCCESS")
    return True


def step_handle_restart_dialog() -> bool:
    log_message("Ожидание диалога перезапуска сервера...", "INFO")
    if not wait_for_dialog_text(DIALOG_TEXTS["restart_dialog"]):
        log_message("  ❌ Диалог перезапуска не появился", "WARNING")
        return False
    if not click_dialog_button("Yes"):
        log_message("  ❌ Кнопка Yes не найдена", "ERROR")
        return False
    log_message("  ✅ Диалог обработан", "SUCCESS")
    return True


# ============================================================================
# ОСНОВНАЯ ФУНКЦИЯ (убрана проверка прав)
# ============================================================================

def main():
    log_message("=" * 80, "INFO")
    log_message("ЗАПУСК АВТОМАТИЧЕСКОЙ НАСТРОЙКИ TRBOnet Server", "INFO")
    log_message("=" * 80, "INFO")

    log_message("✅ Скрипт запущен с правами администратора", "SUCCESS")

    # Получаем версию из аргументов
    if len(sys.argv) < 2:
        log_message("❌ Версия не указана. Использование: python configure_server.py <версия>", "ERROR")
        log_message("   Пример: python configure_server.py 6.5.0.9140", "INFO")
        sys.exit(1)

    version = sys.argv[1]
    db_name = DB_NAME_TEMPLATE.format(version=version)
    log_message(f"  Версия: {version}", "INFO")
    log_message(f"  Имя БД: {db_name}", "INFO")
    log_message(f"  Путь к серверу: {SERVER_EXE_PATH}", "INFO")

    app = None

    try:
        # Шаг 1: Запуск приложения
        log_message("\n📌 ШАГ 1: Запуск приложения", "INFO")
        log_message("-" * 40, "INFO")

        app = launch_app(SERVER_EXE_PATH)
        if not app:
            log_message("❌ Не удалось запустить приложение", "ERROR")
            return

        window = find_window(app, WINDOW_TITLE)
        if not window:
            log_message("❌ Не найдено главное окно", "ERROR")
            return

        # Шаг 2: Переход на вкладку Database
        log_message("\n📌 ШАГ 2: Переход на вкладку Database", "INFO")
        log_message("-" * 40, "INFO")

        if not step_switch_to_database_tab(window):
            log_message("❌ Не удалось перейти на Database", "ERROR")
            return

        # Шаг 3: Установка имени базы данных
        log_message("\n📌 ШАГ 3: Установка имени базы данных", "INFO")
        log_message("-" * 40, "INFO")

        if not set_combo_value_by_key(window, "dd_list_database", db_name):
            log_message("❌ Не удалось установить имя БД", "ERROR")
            return

        # Шаг 4: Клик по Create Database
        log_message("\n📌 ШАГ 4: Клик по 'Create Database'", "INFO")
        log_message("-" * 40, "INFO")

        if not click_by_key(window, "btn_create_database"):
            log_message("❌ Не удалось кликнуть по 'Create Database'", "ERROR")
            return

        # Шаг 5: Ожидание и закрытие диалога
        log_message("\n📌 ШАГ 5: Ожидание и закрытие диалога создания БД", "INFO")
        log_message("-" * 40, "INFO")

        if not step_wait_and_close_creation_dialog(db_name):
            log_message("❌ Не удалось обработать диалог создания БД", "ERROR")
            return

        # Шаг 6: Переход на вкладку Service
        log_message("\n📌 ШАГ 6: Переход на вкладку Service", "INFO")
        log_message("-" * 40, "INFO")

        if not step_switch_to_service_tab(window):
            log_message("❌ Не удалось перейти на Service", "ERROR")
            return

        # Шаг 7: Клик по Install Service
        log_message("\n📌 ШАГ 7: Клик по 'Install Service'", "INFO")
        log_message("-" * 40, "INFO")

        if not click_by_key(window, "btn_install_service"):
            log_message("❌ Не удалось кликнуть по 'Install Service'", "ERROR")
            return

        # Шаг 8: Клик по Start service
        log_message("\n📌 ШАГ 8: Клик по 'Start service'", "INFO")
        log_message("-" * 40, "INFO")

        if not step_click_start_service(window):
            log_message("❌ Не удалось кликнуть по 'Start service'", "ERROR")
            return

        # Шаг 9: Ожидание Service started
        log_message("\n📌 ШАГ 9: Ожидание 'Service started'", "INFO")
        log_message("-" * 40, "INFO")

        if not wait_for_text(window, DIALOG_TEXTS["service_started"]):
            log_message("❌ 'Service started' не появился", "ERROR")
            return

        # Шаг 10: Клик по OK
        log_message("\n📌 ШАГ 10: Клик по кнопке OK", "INFO")
        log_message("-" * 40, "INFO")

        if not click_by_key(window, "btn_ok"):
            log_message("❌ Не удалось кликнуть по OK", "ERROR")
            return

        # Шаг 11: Диалог перезапуска
        log_message("\n📌 ШАГ 11: Обработка диалога перезапуска", "INFO")
        log_message("-" * 40, "INFO")

        step_handle_restart_dialog()

        # Итог
        log_message("\n" + "=" * 80, "INFO")
        log_message("✅ НАСТРОЙКА TRBOnet Server ВЫПОЛНЕНА УСПЕШНО!", "SUCCESS")
        log_message(f"   Версия: {version}", "SUCCESS")
        log_message(f"   База данных: {db_name}", "SUCCESS")
        log_message("=" * 80, "INFO")

    except Exception as e:
        log_message(f"❌ Критическая ошибка: {e}", "ERROR")
        import traceback
        traceback.print_exc()

    finally:
        if app:
            try:
                app.kill()
                log_message("✅ Приложение закрыто", "INFO")
            except:
                pass


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