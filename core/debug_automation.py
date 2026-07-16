"""
Скрипт для отладки AutomationId в TRBOnet Server
Автоматически переходит на вкладку Database
"""

import os
import sys
import time
import ctypes
from typing import Optional
from datetime import datetime
from pywinauto.application import Application
from pywinauto import Desktop
from pywinauto.timings import wait_until


# ============================================================================
# НАСТРАИВАЕМЫЕ ПАРАМЕТРЫ
# ============================================================================

SERVER_EXE_PATH = r"C:\Program Files\Neocom Software\TRBOnet Enterprise\Server\TRBOnet.Server.exe"
WINDOW_TITLE = "TRBOnet Enterprise 6.5 / Server"
REPORT_FILE = "automation_ids_database_report.txt"
TIMEOUT = 30
SMALL_DELAY = 1
MEDIUM_DELAY = 2
LARGE_DELAY = 5


# ============================================================================
# ЛОГГИРОВАНИЕ
# ============================================================================

def log_message(message: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


# ============================================================================
# ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА
# ============================================================================

def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def run_as_admin():
    log_message("Запрос прав администратора...", "INFO")
    script = os.path.abspath(sys.argv[0])
    params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
    try:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script}" {params}', None, 1
        )
        sys.exit(0)
    except Exception as e:
        log_message(f"Ошибка при запросе прав администратора: {e}", "ERROR")
        sys.exit(1)


# ============================================================================
# ЗАПУСК ПРИЛОЖЕНИЯ
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


# ============================================================================
# ПОИСК ОКНА
# ============================================================================

def find_window(app, title: str, timeout: int = TIMEOUT):
    log_message(f"Поиск окна: '{title}'...", "INFO")
    try:
        window = app.window(title_re=title).wait('visible', timeout=timeout)
        log_message(f"✅ Окно найдено: '{title}'", "SUCCESS")
        return window
    except Exception as e:
        log_message(f"❌ Окно не найдено: {e}", "ERROR")
        return None


# ============================================================================
# ПЕРЕХОД НА ВКЛАДКУ DATABASE (УЛУЧШЕННЫЙ)
# ============================================================================

def switch_to_database_tab(window):
    """
    Переходит на вкладку Database в дереве слева.
    Использует несколько способов для надёжности.
    """
    log_message("Переход на вкладку Database...", "INFO")

    try:
        # Способ 1: Найти элемент в дереве напрямую через перебор
        log_message("  Способ 1: Поиск 'Database' в дереве...", "INFO")
        all_elements = window.descendants()
        database_item = None

        for elem in all_elements:
            try:
                elem_name = elem.window_text()
                elem_type = elem.element_info.control_type if hasattr(elem, 'element_info') else ""
                if elem_name == "Database" and "TreeItem" in elem_type:
                    database_item = elem
                    log_message(f"  ✅ Найден элемент 'Database' в дереве", "SUCCESS")
                    break
            except:
                continue

        if database_item:
            # Пробуем кликнуть
            database_item.click_input()
            time.sleep(MEDIUM_DELAY)

            # Проверяем, что вкладка изменилась
            # Ищем признак вкладки Database - панель ConfigControlDatabase
            config_panel = window.child_window(auto_id="ConfigControlDatabase")
            if config_panel.exists():
                log_message("  ✅ Переход на Database подтверждён (найдена ConfigControlDatabase)", "SUCCESS")
                return True
            else:
                log_message("  ⚠️ Клик выполнен, но ConfigControlDatabase не найдена", "WARNING")
                # Пробуем найти в потомках
                for elem in window.descendants():
                    try:
                        if hasattr(elem, 'automation_id') and elem.automation_id == "ConfigControlDatabase":
                            log_message("  ✅ ConfigControlDatabase найдена в потомках", "SUCCESS")
                            return True
                    except:
                        continue

        # Способ 2: Использовать m_tree
        log_message("  Способ 2: Поиск через m_tree...", "INFO")
        tree = window.child_window(auto_id="m_tree")
        if tree.exists():
            # Ищем элемент Database внутри дерева
            database_item = tree.child_window(title="Database", control_type="TreeItem")
            if database_item.exists():
                database_item.click_input()
                time.sleep(MEDIUM_DELAY)

                # Проверяем
                config_panel = window.child_window(auto_id="ConfigControlDatabase")
                if config_panel.exists():
                    log_message("  ✅ Переход на Database подтверждён (через m_tree)", "SUCCESS")
                    return True

        # Способ 3: Поиск по частичному совпадению
        log_message("  Способ 3: Поиск по частичному совпадению...", "INFO")
        for elem in all_elements:
            try:
                elem_name = elem.window_text()
                if "Database" in elem_name and "TreeItem" in str(elem.element_info.control_type):
                    elem.click_input()
                    time.sleep(MEDIUM_DELAY)

                    config_panel = window.child_window(auto_id="ConfigControlDatabase")
                    if config_panel.exists():
                        log_message("  ✅ Переход на Database подтверждён (частичное совпадение)", "SUCCESS")
                        return True
            except:
                continue

        log_message("  ❌ Не удалось перейти на Database", "ERROR")
        return False

    except Exception as e:
        log_message(f"  ❌ Ошибка при переходе на Database: {e}", "ERROR")
        return False


# ============================================================================
# СОХРАНЕНИЕ ОТЧЁТА
# ============================================================================

def save_automation_ids_report(window, filename: str = REPORT_FILE):
    log_message(f"Сохранение отчёта в файл: {filename}", "INFO")

    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("ОТЧЁТ ПО AUTOMATIONID В TRBOnet Server")
    report_lines.append(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 80)
    report_lines.append("")

    try:
        all_elements = window.descendants()
        count = 0

        for elem in all_elements:
            try:
                auto_id = None

                if hasattr(elem, 'element_info') and hasattr(elem.element_info, 'automation_id'):
                    auto_id = elem.element_info.automation_id

                if not auto_id and hasattr(elem, 'automation_id'):
                    try:
                        auto_id = elem.automation_id()
                    except:
                        pass

                if auto_id:
                    elem_name = elem.window_text() if hasattr(elem, 'window_text') else ""
                    elem_type = elem.element_info.control_type if hasattr(elem, 'element_info') and hasattr(elem.element_info, 'control_type') else ""
                    report_lines.append(f"  AutomationId: '{auto_id}' | Name: '{elem_name}' | Type: '{elem_type}'")
                    count += 1

            except Exception as e:
                continue

        report_lines.append("")
        report_lines.append(f"Всего найдено элементов с AutomationId: {count}")
        report_lines.append("=" * 80)

        report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))

        log_message(f"✅ Отчёт сохранён в файл: {report_path}", "SUCCESS")
        log_message(f"   Найдено элементов с AutomationId: {count}", "INFO")

    except Exception as e:
        log_message(f"❌ Ошибка при сохранении отчёта: {e}", "ERROR")


# ============================================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================================

def main():
    log_message("=" * 70, "INFO")
    log_message("🛠️  ОТЛАДКА AUTOMATIONID В TRBOnet Server", "INFO")
    log_message("=" * 70, "INFO")

    if not is_admin():
        log_message("Требуются права администратора. Запрос...", "INFO")
        run_as_admin()
        return

    log_message("✅ Скрипт запущен с правами администратора", "SUCCESS")

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

        log_message("✅ Главное окно найдено", "SUCCESS")
        time.sleep(MEDIUM_DELAY)

        # Шаг 2: Переход на вкладку Database
        log_message("\n📌 ШАГ 2: Переход на вкладку Database", "INFO")
        log_message("-" * 40, "INFO")

        # ПРОБУЕМ ПЕРЕЙТИ НА DATABASE
        switch_to_database_tab(window)

        # Дополнительная задержка для полной загрузки вкладки
        time.sleep(LARGE_DELAY)

        # Шаг 3: Сохранение отчёта
        log_message("\n📌 ШАГ 3: Сохранение отчёта по AutomationId", "INFO")
        log_message("-" * 40, "INFO")

        save_automation_ids_report(window)

        # Шаг 4: Проверка ключевых AutomationId
        log_message("\n📌 ШАГ 4: Проверка ключевых AutomationId", "INFO")
        log_message("-" * 40, "INFO")

        key_ids = [
            "ConfigControlDatabase",  # Панель Database
            "m_boxDatabase",          # ComboBox для базы данных
            "m_btnCreate",            # Кнопка Create Database
            "m_btnUpgrade",           # Кнопка Upgrade Database
            "m_btnTest",              # Кнопка Test Connection
            "m_boxServer",            # ComboBox для SQL Server
            "m_boxAuthorization"      # ComboBox для авторизации
        ]

        found_count = 0
        for auto_id in key_ids:
            element = window.child_window(auto_id=auto_id)
            if element.exists():
                elem_name = element.window_text() if hasattr(element, 'window_text') else ""
                log_message(f"  ✅ '{auto_id}' найден: '{elem_name}'", "SUCCESS")
                found_count += 1
            else:
                log_message(f"  ❌ '{auto_id}' не найден", "ERROR")

        log_message(f"\n  Найдено AutomationId из списка: {found_count}/{len(key_ids)}", "INFO")

        # Итог
        log_message("\n" + "=" * 70, "INFO")
        if found_count >= 3:
            log_message("✅ ОТЛАДКА ЗАВЕРШЕНА! Найдены ключевые AutomationId", "SUCCESS")
        else:
            log_message("⚠️ ОТЛАДКА ЗАВЕРШЕНА! Некоторые AutomationId не найдены", "WARNING")
            log_message("  Возможно, переход на Database не сработал", "INFO")
        log_message(f"  Отчёт сохранён в: {REPORT_FILE}", "INFO")
        log_message("=" * 70, "INFO")

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