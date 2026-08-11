"""
Скрипт для сбора всех AutomationId элементов в указанном приложении.
Запускается отдельно, не требует интеграции в проект.
"""

import time
import os
import json
from pywinauto import Application, Desktop
from pywinauto.controls import uiawrapper


def get_all_auto_ids(window, parent_path=""):
    """
    Рекурсивно обходит все элементы окна и собирает AutomationId.

    Args:
        window: окно или элемент pywinauto
        parent_path: путь к родительскому элементу (для вложенности)

    Returns:
        list: список словарей с информацией об элементах
    """
    results = []

    try:
        # Получаем информацию о текущем элементе
        elem_info = window.element_info
        auto_id = elem_info.automation_id if hasattr(elem_info, 'automation_id') else ""
        control_type = elem_info.control_type if hasattr(elem_info, 'control_type') else ""
        name = elem_info.name if hasattr(elem_info, 'name') else ""

        # Добавляем текущий элемент, если у него есть AutoId
        if auto_id and auto_id.strip():
            results.append({
                "automation_id": auto_id,
                "control_type": control_type,
                "name": name,
                "path": parent_path + " > " + (name or control_type or "unknown")
            })

        # Рекурсивно обходим дочерние элементы
        try:
            children = window.children()
            for child in children:
                child_path = parent_path + " > " + (name or control_type or "root")
                results.extend(get_all_auto_ids(child, child_path))
        except:
            # Если нет детей или ошибка, пропускаем
            pass

    except Exception as e:
        # Игнорируем ошибки для отдельных элементов
        pass

    return results


def find_all_elements_by_auto_id(app_title, app_path=None, timeout=10):
    """
    Находит все элементы с AutomationId в приложении.

    Args:
        app_title: заголовок окна приложения (частичное совпадение)
        app_path: путь к .exe (если приложение не запущено)
        timeout: время ожидания окна

    Returns:
        dict: словарь с результатами
    """
    print(f"🔍 Поиск элементов в приложении: '{app_title}'")

    # Если приложение не запущено - запускаем
    app = None
    window = None

    try:
        # Пробуем найти уже запущенное окно
        desktop = Desktop(backend="uia")
        windows = desktop.windows(title_re=f".*{app_title}.*")

        if windows:
            print(f"✅ Найдено запущенное окно")
            window = windows[0]
            window.set_focus()
            time.sleep(1)
        elif app_path and os.path.exists(app_path):
            # Если окно не найдено, запускаем приложение
            print(f"🚀 Запускаем приложение: {app_path}")
            app = Application(backend="uia").start(app_path)
            time.sleep(5)  # Ждем загрузки

            # Ищем окно
            window = app.window(title_re=f".*{app_title}.*")
            window.wait('visible', timeout=timeout)
            print(f"✅ Приложение запущено, окно найдено")
        else:
            print(f"❌ Окно '{app_title}' не найдено, и путь к .exe не указан")
            return {"error": "Window not found"}

        # Собираем все элементы
        print("📋 Сбор элементов...")
        results = get_all_auto_ids(window)

        # Сортируем по AutomationId
        results.sort(key=lambda x: x.get("automation_id", ""))

        return {
            "total": len(results),
            "elements": results
        }

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return {"error": str(e)}


def save_results_to_json(results, filename="automation_ids.json"):
    """Сохраняет результаты в JSON файл."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"💾 Результаты сохранены в: {filename}")


def print_summary(results):
    """Выводит краткую сводку по найденным элементам."""
    elements = results.get("elements", [])
    if not elements:
        print("⚠️ Элементы с AutomationId не найдены")
        return

    print(f"\n📊 Найдено элементов с AutomationId: {len(elements)}")
    print("\n🔑 Список AutomationId (первые 20):")
    for i, elem in enumerate(elements[:20]):
        print(f"  {i + 1}. ID: '{elem['automation_id']}' | Тип: {elem['control_type']} | Имя: {elem['name']}")

    if len(elements) > 20:
        print(f"  ... и еще {len(elements) - 20} элементов")


# ============================================================
# НАСТРОЙКА ПАРАМЕТРОВ (ИЗМЕНЯЙ ЗДЕСЬ)
# ============================================================

if __name__ == "__main__":
    # 🔧 ИЗМЕНИ ЭТИ ПАРАМЕТРЫ ПОД СВОЕ ПРИЛОЖЕНИЕ

    # Заголовок окна (частичное совпадение)
    APP_TITLE = "TRBOnet Enterprise"

    # Путь к .exe (если приложение не запущено)
    # Оставь пустым, если приложение уже открыто
    APP_PATH = r""  # или оставь ""

    # Имя файла для сохранения результатов
    OUTPUT_FILE = "automation_ids.json"

    # ============================================================

    print("=" * 60)
    print("🔍 Сбор AutomationId элементов приложения")
    print("=" * 60)

    # Запускаем сбор
    results = find_all_elements_by_auto_id(APP_TITLE, APP_PATH)

    if results.get("error"):
        print(f"\n❌ Ошибка: {results['error']}")
        print("\n💡 Возможные решения:")
        print("  1. Проверьте, что приложение запущено")
        print("  2. Уточните заголовок окна (частичное совпадение)")
        print("  3. Укажите правильный путь к .exe")
    else:
        # Выводим сводку
        print_summary(results)

        # Сохраняем в JSON
        save_results_to_json(results, OUTPUT_FILE)

        print("\n✅ Готово! Теперь можешь:")
        print(f"  - Открыть файл {OUTPUT_FILE} в редакторе")
        print("  - Искать нужные AutomationId по ключевым словам")
        print("  - Добавлять найденные ID в core/config_auto_ids.py")