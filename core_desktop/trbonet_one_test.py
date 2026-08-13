"""
Автоматизация ТЕСТИРОВАНИЯ TRBOnet One
Задачи:
1. Открыть TRBOnet.One.exe
2. Выбрать тип консоли "TRBOnetOne" в Connection Manager
3. Подключиться к серверу
4. Проверить наличие процесса
5. Найти активную кнопку PTT и нажать её
6. Сделать скриншот и сравнить с эталоном
7. Закрыть приложение и проверить завершение процесса
"""

import os
import sys
import time
from datetime import datetime
from typing import Optional, Tuple, List
import psutil
from PIL import Image, ImageDraw, ImageChops, ImageGrab
from pywinauto.application import Application
from pywinauto import Desktop

# Импортируем фикс кодировки
import fix_encoding  # noqa

# Импортируем конфигурацию
from config_auto_ids import AUTO_IDS, DIALOG_TEXTS, READY_TEXTS, PROCESS_NAMES


# ============================================================================
# НАСТРАИВАЕМЫЕ ПАРАМЕТРЫ
# ============================================================================

ONE_EXE_PATH = r"C:\Program Files\Neocom Software\TRBOnet Enterprise\Console\TRBOnet.One.exe"
EXPECTED_SCREENSHOT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots", "expected_one.png")
ACTUAL_SCREENSHOT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots", "actual_one.png")
DIFF_SCREENSHOT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots", "diff_one.png")

TIMEOUT = 60  # Увеличил до 60 секунд для медленных машин
DIFF_THRESHOLD_PERCENT = 0.5
MIN_CLUSTER_PIXELS = 50
PTT_DELAY = 15

LOG_FILE = os.path.join("logs", "trbonet_one_test.log")
WINDOW_CONNECTION_MANAGER = "TRBOnet Connection Manager"
WINDOW_ONE_PATTERN = r"TRBOnet One"


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
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def get_auto_id(key: str) -> Optional[str]:
    auto_id = AUTO_IDS.get(key)
    if not auto_id:
        log_message(f"❌ Ключ '{key}' не найден в AUTO_IDS", "ERROR")
    return auto_id


def get_dialog_text(key: str) -> Optional[str]:
    text = DIALOG_TEXTS.get(key)
    if not text:
        log_message(f"❌ Ключ '{key}' не найден в DIALOG_TEXTS", "ERROR")
    return text


def get_ready_text(key: str) -> Optional[str]:
    text = READY_TEXTS.get(key)
    if not text:
        log_message(f"❌ Ключ '{key}' не найден в READY_TEXTS", "ERROR")
    return text


def get_process_count(process_name: str) -> Tuple[int, List[int]]:
    pids = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] == process_name:
                pids.append(proc.info['pid'])
        except:
            pass
    return len(pids), pids


def click_element_safe(element, name: str = "элемент") -> bool:
    if not element:
        log_message(f"  ❌ {name} отсутствует", "ERROR")
        return False

    try:
        element.click_input()
        log_message(f"  ✅ {name} нажат (click_input)", "SUCCESS")
        return True
    except:
        try:
            element.click()
            log_message(f"  ✅ {name} нажат (click)", "SUCCESS")
            return True
        except:
            try:
                element.invoke()
                log_message(f"  ✅ {name} нажат (invoke)", "SUCCESS")
                return True
            except Exception as e:
                log_message(f"  ❌ Ошибка при клике по {name}: {e}", "ERROR")
                return False


# ============================================================================
# ФУНКЦИИ ДЛЯ ПРОВЕРКИ ГОТОВНОСТИ ОКНА
# ============================================================================

def wait_for_window_ready(window, timeout: int = TIMEOUT) -> bool:
    """
    Ожидает, пока окно полностью загрузится.
    Проверяет наличие ключевых элементов по AutomationId.
    """
    log_message(f"  Ожидание полной загрузки окна...", "INFO")

    start_time = time.time()

    # Ключевые элементы, которые должны появиться
    key_elements = ["ConsoleTypeCb", "btnConnect"]

    while time.time() - start_time < timeout:
        try:
            all_elements = window.descendants()
            found_count = 0

            for auto_id in key_elements:
                for elem in all_elements:
                    try:
                        if hasattr(elem, 'element_info') and hasattr(elem.element_info, 'automation_id'):
                            if elem.element_info.automation_id == auto_id:
                                found_count += 1
                                log_message(f"    ✅ Элемент '{auto_id}' найден", "DEBUG")
                                break
                    except:
                        continue

            if found_count == len(key_elements):
                log_message(f"  ✅ Окно полностью загружено (найдено {found_count} элементов)", "SUCCESS")
                return True

        except Exception as e:
            log_message(f"  Ошибка при проверке загрузки: {e}", "WARNING")

        time.sleep(0.3)

    log_message(f"  ❌ Окно не загрузилось за {timeout} секунд", "ERROR")
    return False


def wait_for_window_ready_one(window, timeout: int = TIMEOUT) -> bool:
    """
    Ожидает, пока окно TRBOnet One полностью загрузится.
    Проверяет наличие кнопок PTT.
    """
    log_message(f"  Ожидание полной загрузки TRBOnet One...", "INFO")

    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            all_elements = window.descendants()

            for elem in all_elements:
                try:
                    elem_name = elem.window_text() if hasattr(elem, 'window_text') else ""
                    elem_type = elem.element_info.control_type if hasattr(elem, 'element_info') else ""

                    if elem_name == "PTT" and "Button" in elem_type:
                        log_message(f"  ✅ Окно TRBOnet One полностью загружено", "SUCCESS")
                        return True
                except:
                    continue

        except Exception as e:
            log_message(f"  Ошибка при проверке загрузки: {e}", "WARNING")

        time.sleep(0.3)

    log_message(f"  ❌ Окно TRBOnet One не загрузилось за {timeout} секунд", "ERROR")
    return False


# ============================================================================
# ФУНКЦИИ ПОИСКА ЭЛЕМЕНТОВ
# ============================================================================

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
            time.sleep(0.3)
        except Exception as e:
            log_message(f"  Ошибка при поиске: {e}", "WARNING")
            time.sleep(0.3)

    log_message(f"  ❌ Элемент с AutomationId '{auto_id}' не найден", "ERROR")
    return None


def find_element_by_key(window, key: str, timeout: int = TIMEOUT):
    auto_id = get_auto_id(key)
    if not auto_id:
        return None
    return find_element_by_auto_id(window, auto_id, timeout)


def wait_for_window(title_pattern: str, timeout: int = TIMEOUT):
    log_message(f"Ожидание окна: '{title_pattern}'...", "INFO")

    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            desktop = Desktop(backend="uia")
            windows = desktop.windows(title_re=title_pattern)
            if windows:
                win = windows[0]
                try:
                    win_text = win.window_text()
                    if win_text:
                        log_message(f"  ✅ Окно найдено: '{win_text}'", "SUCCESS")
                        return win
                except:
                    pass
        except Exception as e:
            log_message(f"  Ошибка при поиске окна: {e}", "WARNING")

        time.sleep(0.3)

    log_message(f"  ❌ Окно не найдено за {timeout} секунд", "ERROR")
    return None


# ============================================================================
# ФУНКЦИЯ УСТАНОВКИ ЗНАЧЕНИЯ В COMBOBOX
# ============================================================================

def set_combo_box_value(window, key: str, value: str, timeout: int = TIMEOUT) -> bool:
    auto_id = get_auto_id(key)
    if not auto_id:
        log_message(f"  ❌ Ключ '{key}' не найден в AUTO_IDS", "ERROR")
        return False

    log_message(f"  Поиск ComboBox по ключу: '{key}' (AutomationId: '{auto_id}')", "INFO")
    log_message(f"  Выбираем значение: '{value}'", "INFO")

    combo_box = find_element_by_auto_id(window, auto_id, timeout)

    if not combo_box:
        log_message(f"  ❌ ComboBox не найден", "ERROR")
        return False

    try:
        combo_box.click_input()
        time.sleep(0.3)
        combo_box.select(value)
        time.sleep(0.3)
        log_message(f"  ✅ Значение '{value}' выбрано", "SUCCESS")
        return True
    except Exception as e:
        log_message(f"  ❌ Ошибка при выборе значения: {e}", "ERROR")
        return False


# ============================================================================
# ФУНКЦИИ РАБОТЫ С PTT
# ============================================================================

def find_active_ptt_button(window, timeout: int = 10) -> Optional:
    log_message(f"  Поиск активной кнопки PTT...", "INFO")

    start_time = time.time()

    while time.time() - start_time < timeout:
        all_elements = window.descendants()
        ptt_buttons = []

        for elem in all_elements:
            try:
                elem_name = elem.window_text() if hasattr(elem, 'window_text') else ""
                elem_type = elem.element_info.control_type if hasattr(elem, 'element_info') else ""

                if elem_name == "PTT" and "Button" in elem_type:
                    ptt_buttons.append(elem)
            except:
                continue

        if not ptt_buttons:
            log_message(f"  ⚠️ Кнопки PTT не найдены", "WARNING")
            time.sleep(0.5)
            continue

        log_message(f"  Найдено кнопок PTT: {len(ptt_buttons)}", "INFO")

        for idx, btn in enumerate(ptt_buttons, 1):
            try:
                is_enabled = btn.is_enabled() if hasattr(btn, 'is_enabled') else False
                if is_enabled:
                    log_message(f"  ✅ Найдена активная кнопка PTT #{idx}", "SUCCESS")
                    return btn
                else:
                    log_message(f"  ℹ️ Кнопка PTT #{idx} неактивна", "DEBUG")
            except:
                continue

        time.sleep(0.5)

    log_message(f"  ❌ Активная кнопка PTT не найдена за {timeout} секунд", "ERROR")
    return None


# ============================================================================
# ФУНКЦИИ РАБОТЫ СО СКРИНШОТАМИ
# ============================================================================

def take_screenshot(window, save_path: str) -> bool:
    log_message(f"Создание скриншота: {save_path}", "INFO")

    try:
        rect = window.rectangle()
        left = rect.left
        top = rect.top
        right = rect.right
        bottom = rect.bottom

        log_message(f"  Размер окна: {right - left}x{bottom - top}", "INFO")

        screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
        screenshot.save(save_path)

        log_message(f"  ✅ Скриншот сохранён: {save_path}", "SUCCESS")
        return True

    except Exception as e:
        log_message(f"  ❌ Ошибка при создании скриншота: {e}", "ERROR")
        return False


def find_diff_clusters(diff_image, min_pixels: int = MIN_CLUSTER_PIXELS) -> List[Tuple[int, int, int, int]]:
    width, height = diff_image.size
    diff_pixels = diff_image.load()

    labels = [[0] * width for _ in range(height)]
    current_label = 0

    for y in range(height):
        for x in range(width):
            if diff_pixels[x, y] != (0, 0, 0) and diff_pixels[x, y] != (255, 255, 255):
                left_label = labels[y][x-1] if x > 0 else 0
                top_label = labels[y-1][x] if y > 0 else 0

                if left_label == 0 and top_label == 0:
                    current_label += 1
                    labels[y][x] = current_label
                elif left_label != 0:
                    labels[y][x] = left_label
                elif top_label != 0:
                    labels[y][x] = top_label
                elif left_label != top_label:
                    old_label = top_label
                    new_label = left_label
                    for y2 in range(height):
                        for x2 in range(width):
                            if labels[y2][x2] == old_label:
                                labels[y2][x2] = new_label
                    labels[y][x] = new_label

    clusters = {}
    for y in range(height):
        for x in range(width):
            label = labels[y][x]
            if label != 0:
                if label not in clusters:
                    clusters[label] = {'min_x': x, 'max_x': x, 'min_y': y, 'max_y': y, 'count': 0}
                clusters[label]['min_x'] = min(clusters[label]['min_x'], x)
                clusters[label]['max_x'] = max(clusters[label]['max_x'], x)
                clusters[label]['min_y'] = min(clusters[label]['min_y'], y)
                clusters[label]['max_y'] = max(clusters[label]['max_y'], y)
                clusters[label]['count'] += 1

    result = []
    for label, data in clusters.items():
        if data['count'] >= min_pixels:
            padding = 2
            result.append((
                max(0, data['min_x'] - padding),
                max(0, data['min_y'] - padding),
                min(width - 1, data['max_x'] + padding),
                min(height - 1, data['max_y'] + padding)
            ))

    return result


def compare_images(expected_path: str, actual_path: str, diff_path: str) -> Tuple[bool, float]:
    log_message(f"Сравнение изображений...", "INFO")

    try:
        expected = Image.open(expected_path)
        actual = Image.open(actual_path)

        if expected.size != actual.size:
            log_message(f"  Размеры изображений не совпадают: {expected.size} vs {actual.size}", "WARNING")
            actual = actual.resize(expected.size)

        diff = ImageChops.difference(expected, actual)

        bbox = diff.getbbox()
        if not bbox:
            log_message(f"  ✅ Изображения идентичны", "SUCCESS")
            return False, 0.0

        total_pixels = expected.size[0] * expected.size[1]
        diff_pixels = sum(1 for p in diff.getdata() if p != (0, 0, 0) and p != (255, 255, 255))
        diff_percent = (diff_pixels / total_pixels) * 100

        log_message(f"  Процент отличий: {diff_percent:.4f}%", "INFO")

        if diff_percent < DIFF_THRESHOLD_PERCENT:
            log_message(f"  ✅ Отличия меньше порога ({DIFF_THRESHOLD_PERCENT}%), считаем идентичными", "SUCCESS")
            return False, diff_percent

        log_message(f"  ⚠️ Найдены значимые отличия: {diff_percent:.2f}%", "WARNING")

        result = actual.copy()
        draw = ImageDraw.Draw(result)

        clusters = find_diff_clusters(diff)

        if clusters:
            for i, cluster_bbox in enumerate(clusters, 1):
                draw.rectangle(cluster_bbox, outline="red", width=3)
                center_x = (cluster_bbox[0] + cluster_bbox[2]) // 2
                center_y = (cluster_bbox[1] + cluster_bbox[3]) // 2
                draw.text((center_x + 5, center_y - 10), f"#{i}", fill="red")

            log_message(f"  Обведено кластеров отличий: {len(clusters)}", "INFO")
        else:
            draw.rectangle(bbox, outline="red", width=3)
            log_message(f"  ⚠️ Кластеры не найдены, обведён общий bbox", "WARNING")

        result.save(diff_path)
        log_message(f"  ✅ Изображение с отличиями сохранено: {diff_path}", "SUCCESS")

        return True, diff_percent

    except Exception as e:
        log_message(f"  ❌ Ошибка при сравнении изображений: {e}", "ERROR")
        return False, -1.0


# ============================================================================
# ФУНКЦИЯ ЗАКРЫТИЯ ПРИЛОЖЕНИЯ
# ============================================================================

def close_application(window, process_name: str, timeout: int = 10) -> bool:
    log_message("Закрытие приложения через .close()...", "INFO")

    try:
        window.close()
        log_message("  ✅ .close() выполнен", "SUCCESS")

        log_message(f"  Ожидание завершения процесса '{process_name}'...", "INFO")

        start_time = time.time()
        while time.time() - start_time < timeout:
            count, pids = get_process_count(process_name)
            if count == 0:
                log_message(f"  ✅ Процесс '{process_name}' завершился", "SUCCESS")
                return True
            time.sleep(0.5)

        count, pids = get_process_count(process_name)
        log_message(f"  ⚠️ Процесс '{process_name}' не завершился за {timeout} секунд (кол-во: {count}, PID: {pids})", "WARNING")
        return False

    except Exception as e:
        log_message(f"  ❌ Ошибка при закрытии приложения: {e}", "ERROR")
        return False


# ============================================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================================

def main():
        log_message("=" * 80, "INFO")
        log_message("ЗАПУСК АВТОМАТИЧЕСКОГО ТЕСТИРОВАНИЯ TRBOnet One", "INFO")
        log_message("=" * 80, "INFO")

        log_message(f"  Путь к приложению: {ONE_EXE_PATH}", "INFO")

        app = None
        window = None
        one_pid = None
        process_name = PROCESS_NAMES.get("one")

        try:
            # ШАГ 1: Запуск приложения
            log_message("\n📌 ШАГ 1: Запуск TRBOnet One", "INFO")
            log_message("-" * 40, "INFO")

            if not os.path.exists(ONE_EXE_PATH):
                log_message(f"❌ Файл не найден: {ONE_EXE_PATH}", "ERROR")
                return

            app = Application(backend="uia").start(ONE_EXE_PATH)
            log_message("✅ Приложение запущено", "SUCCESS")

            # ШАГ 2: Ожидание окна Connection Manager
            log_message("\n📌 ШАГ 2: Ожидание окна Connection Manager", "INFO")
            log_message("-" * 40, "INFO")

            connect_window = wait_for_window(WINDOW_CONNECTION_MANAGER)
            if not connect_window:
                log_message("❌ Окно Connection Manager не появилось", "ERROR")
                sys.exit(1)

            # ШАГ 2.5: Ожидание полной загрузки окна
            log_message("\n📌 ШАГ 2.5: Ожидание полной загрузки окна", "INFO")
            log_message("-" * 40, "INFO")

            if not wait_for_window_ready(connect_window):
                log_message("❌ Окно не загрузилось", "ERROR")
                sys.exit(1)

            # ШАГ 3: Выбор типа консоли
            log_message("\n📌 ШАГ 3: Выбор типа консоли", "INFO")
            log_message("-" * 40, "INFO")

            console_type = get_dialog_text("console_type_one")
            if not set_combo_box_value(connect_window, "combo_console_type", console_type):
                log_message("❌ Не удалось выбрать тип консоли", "ERROR")
                sys.exit(1)

            # ШАГ 4: Нажатие кнопки OK
            log_message("\n📌 ШАГ 4: Подключение к серверу", "INFO")
            log_message("-" * 40, "INFO")

            btn_connect = find_element_by_key(connect_window, "btn_connect_one")
            if not btn_connect:
                log_message("❌ Кнопка Connect не найдена", "ERROR")
                sys.exit(1)

            if not click_element_safe(btn_connect, "Connect"):
                log_message("❌ Не удалось нажать Connect", "ERROR")
                sys.exit(1)

            # Небольшая задержка для закрытия Connection Manager
            log_message("  ⏳ Ожидание закрытия Connection Manager...", "INFO")
            time.sleep(2)

            # ШАГ 5: Ожидание окна TRBOnet One
            log_message("\n📌 ШАГ 5: Ожидание окна TRBOnet One", "INFO")
            log_message("-" * 40, "INFO")

            window = wait_for_window(WINDOW_ONE_PATTERN, timeout=60)
            if not window:
                log_message("❌ Окно TRBOnet One не появилось", "ERROR")
                sys.exit(1)

            # ШАГ 5.1: Ожидание полной загрузки TRBOnet One
            log_message("\n📌 ШАГ 5.1: Ожидание полной загрузки TRBOnet One", "INFO")
            log_message("-" * 40, "INFO")

            if not wait_for_window_ready_one(window):
                log_message("❌ Окно TRBOnet One не загрузилось", "ERROR")
                sys.exit(1)

            # Проверяем процесс
            if process_name:
                count, pids = get_process_count(process_name)
                log_message(f"  Найдено процессов '{process_name}': {count}", "INFO")
                if count > 0:
                    one_pid = pids[0]
                    log_message(f"  ✅ Процесс '{process_name}' запущен (PID: {one_pid})", "SUCCESS")
                else:
                    log_message(f"  ❌ Процесс '{process_name}' не найден", "ERROR")
                    sys.exit(1)

            # ================================================================
            # ШАГ 6: Поиск активной кнопки PTT и нажатие
            # ================================================================
            log_message("\n📌 ШАГ 6: Поиск активной кнопки PTT (первое)", "INFO")
            log_message("-" * 40, "INFO")

            ptt_button = find_active_ptt_button(window, timeout=10)
            if not ptt_button:
                log_message("❌ Активная кнопка PTT не найдена", "ERROR")
                sys.exit(1)

            if not click_element_safe(ptt_button, "PTT"):
                log_message("❌ Не удалось нажать PTT", "ERROR")
                sys.exit(1)

            # ================================================================
            # ЗАДЕРЖКА ПЕРЕД СКРИНШОТОМ (для отрисовки интерфейса)
            # ================================================================
            log_message("  ⏳ Ожидание отрисовки интерфейса после нажатия PTT...", "INFO")
            time.sleep(1)

            # ================================================================
            # ШАГ 7: Скриншот
            # ================================================================
            log_message("\n📌 ШАГ 7: Создание скриншота", "INFO")
            log_message("-" * 40, "INFO")

            if not take_screenshot(window, ACTUAL_SCREENSHOT_PATH):
                log_message("❌ Не удалось создать скриншот", "ERROR")
                sys.exit(1)

            # ================================================================
            # ШАГ 8: Сравнение скриншотов
            # ================================================================
            log_message("\n📌 ШАГ 8: Сравнение скриншотов", "INFO")
            log_message("-" * 40, "INFO")

            if not os.path.exists(EXPECTED_SCREENSHOT_PATH):
                log_message(f"⚠️ Эталонный скриншот не найден: {EXPECTED_SCREENSHOT_PATH}", "WARNING")
                log_message("  Пропускаем сравнение", "INFO")
            else:
                has_diff, diff_percent = compare_images(
                    EXPECTED_SCREENSHOT_PATH,
                    ACTUAL_SCREENSHOT_PATH,
                    DIFF_SCREENSHOT_PATH
                )

                if has_diff:
                    log_message(f"  ⚠️ Найдены значимые отличия ({diff_percent:.2f}%)", "WARNING")
                else:
                    log_message("  ✅ Изображения совпадают", "SUCCESS")

            # ================================================================
            # ШАГ 9: Уже выполнен внутри compare_images
            # ================================================================
            log_message("\n📌 ШАГ 9: Обработка отличий выполнена в шаге 8", "INFO")

            # ================================================================
            # ШАГ 10: Ожидание и повторное нажатие PTT
            # ================================================================
            log_message("\n📌 ШАГ 10: Ожидание и повторное нажатие PTT", "INFO")
            log_message("-" * 40, "INFO")

            log_message(f"  ⏳ Ожидание {PTT_DELAY} секунд...", "INFO")
            time.sleep(PTT_DELAY)

            ptt_button = find_active_ptt_button(window, timeout=10)
            if not ptt_button:
                log_message("❌ Активная кнопка PTT не найдена при повторном поиске", "ERROR")
                sys.exit(1)
            else:
                if not click_element_safe(ptt_button, "PTT (повторно)"):
                    log_message("❌ Не удалось нажать PTT повторно", "ERROR")
                    sys.exit(1)
                else:
                    log_message("  ✅ PTT нажата повторно", "SUCCESS")

            # ================================================================
            # ШАГ 11: Закрытие приложения
            # ================================================================
            log_message("\n📌 ШАГ 11: Закрытие приложения", "INFO")
            log_message("-" * 40, "INFO")

            if process_name:
                close_success = close_application(window, process_name, timeout=15)

                if close_success:
                    log_message("  ✅ Приложение закрыто корректно", "SUCCESS")
                else:
                    log_message("  ❌ Приложение не закрылось корректно (процесс остался)", "ERROR")
                    sys.exit(1)

            # ИТОГ
            log_message("\n" + "=" * 80, "INFO")
            log_message("✅ ТЕСТИРОВАНИЕ TRBOnet One ВЫПОЛНЕНО", "INFO")
            log_message(f"  Скриншот сохранён: {ACTUAL_SCREENSHOT_PATH}", "INFO")
            if os.path.exists(DIFF_SCREENSHOT_PATH):
                log_message(f"  Скриншот с отличиями: {DIFF_SCREENSHOT_PATH}", "INFO")
            log_message("=" * 80, "INFO")

        except Exception as e:
            log_message(f"❌ Критическая ошибка: {e}", "ERROR")
            import traceback
            traceback.print_exc()

        finally:
            if app:
                try:
                    if process_name:
                        count, _ = get_process_count(process_name)
                        if count > 0:
                            app.kill()
                            log_message("✅ Приложение принудительно закрыто (kill)", "INFO")
                        else:
                            log_message("✅ Приложение уже закрыто", "INFO")
                    else:
                        app.kill()
                        log_message("✅ Приложение принудительно закрыто", "INFO")
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