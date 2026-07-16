"""
Автоматизация ТЕСТИРОВАНИЯ DISPATCH CONSOLE
Задачи:
1. Открыть TRBOnet.Console.exe
2. Подключиться к серверу
3. Проверить наличие процесса
4. Найти панель VoiceIP и выполнить PTT
5. Сделать скриншот и сравнить с эталоном
6. Закрыть приложение через .close()
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
from config_auto_ids import AUTO_IDS, DIALOG_TEXTS, PROCESS_NAMES


# ============================================================================
# НАСТРАИВАЕМЫЕ ПАРАМЕТРЫ
# ============================================================================

# Путь к исполняемому файлу Dispatch Console
CONSOLE_EXE_PATH = r"C:\Program Files\Neocom Software\TRBOnet Enterprise\Console\TRBOnet.Console.exe"

# Базовые пути для скриншотов (в папке screenshots)
SCREENSHOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
EXPECTED_SCREENSHOT_PATH = os.path.join(SCREENSHOTS_DIR, "expected_console.png")
ACTUAL_SCREENSHOT_PATH = os.path.join(SCREENSHOTS_DIR, "actual_console.png")
DIFF_SCREENSHOT_PATH = os.path.join(SCREENSHOTS_DIR, "diff_console.png")

# Максимальное время ожидания для операций (сек)
TIMEOUT = 30

# Минимальный процент отличий для считания изображений разными
DIFF_THRESHOLD_PERCENT = 0.5

# Минимальное количество пикселей в кластере отличий
MIN_CLUSTER_PIXELS = 50

# Задержка между нажатиями PTT (сек) — время голосовой сессии
PTT_DELAY = 15

# ============================================================================
# МАСКИРОВАНИЕ ОБЛАСТЕЙ (дата/время и другие динамические элементы)
# ============================================================================

# Список областей, которые нужно закрашивать белым перед сравнением
MASK_AREAS = [
    {
        "name": "Время в правом верхнем углу",
        "type": "absolute",
        "left": 1733,
        "top": 127,
        "right": 1914,
        "bottom": 193,
    },
    {
        "name": "Время/информация в нижней части",
        "type": "absolute",
        "left": 263,
        "top": 838,
        "right": 1924,
        "bottom": 984,
    },
]

# Включить маскирование
MASK_ENABLED = True

# ============================================================================
# КОНСТАНТЫ
# ============================================================================

LOG_FILE = os.path.join("logs", "dispatch_console_test.log")
WINDOW_CONNECT_TITLE = "Connect to TRBOnet Server"
WINDOW_CONSOLE_PATTERN = r"TRBOnet Enterprise.*Dispatch Console"


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
    except:
        pass


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def get_auto_id(key: str) -> Optional[str]:
    """Возвращает AutomationId по ключу из словаря."""
    auto_id = AUTO_IDS.get(key)
    if not auto_id:
        log_message(f"❌ Ключ '{key}' не найден в AUTO_IDS", "ERROR")
    return auto_id


def get_dialog_text(key: str) -> Optional[str]:
    """Возвращает текст по ключу из словаря."""
    text = DIALOG_TEXTS.get(key)
    if not text:
        log_message(f"❌ Ключ '{key}' не найден в DIALOG_TEXTS", "ERROR")
    return text


def get_process_count(process_name: str) -> Tuple[int, List[int]]:
    """
    Возвращает количество запущенных процессов с указанным именем и их PID.
    """
    pids = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] == process_name:
                pids.append(proc.info['pid'])
        except:
            pass
    return len(pids), pids


# ============================================================================
# ФУНКЦИИ РАБОТЫ С ЭЛЕМЕНТАМИ (через descendants)
# ============================================================================

def find_element_by_auto_id(window, auto_id: str, timeout: int = TIMEOUT):
    """
    Находит элемент по AutomationId через перебор потомков.
    Использует только descendants().
    """
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
    """Находит элемент по ключу из словаря AUTO_IDS."""
    auto_id = get_auto_id(key)
    if not auto_id:
        return None
    return find_element_by_auto_id(window, auto_id, timeout)


def click_by_key(window, key: str, timeout: int = TIMEOUT) -> bool:
    """Находит элемент по ключу и кликает на него."""
    log_message(f"Клик по ключу: '{key}'", "INFO")

    element = find_element_by_key(window, key, timeout)

    if not element:
        log_message(f"❌ Не удалось найти элемент по ключу '{key}'", "ERROR")
        return False

    try:
        element.click_input()
        log_message(f"  ✅ Клик выполнен", "SUCCESS")
        return True
    except:
        try:
            element.click()
            log_message(f"  ✅ Клик выполнен", "SUCCESS")
            return True
        except Exception as e:
            log_message(f"  ❌ Ошибка при клике: {e}", "ERROR")
            return False


# ============================================================================
# ФУНКЦИИ РАБОТЫ С ОКНАМИ
# ============================================================================

def wait_for_window(title_pattern: str, timeout: int = TIMEOUT):
    """
    Ожидает появления окна по шаблону заголовка.
    Использует Desktop для поиска по всем окнам.
    """
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
# ФУНКЦИИ ЗАПУСКА
# ============================================================================

def launch_console(app_path: str):
    """
    Запускает Dispatch Console через pywinauto.
    """
    log_message(f"Запуск Dispatch Console: {app_path}", "INFO")

    try:
        if not os.path.exists(app_path):
            log_message(f"❌ Файл не найден: {app_path}", "ERROR")
            return None

        app = Application(backend="uia").start(app_path)
        log_message("✅ Приложение запущено", "SUCCESS")
        return app

    except Exception as e:
        log_message(f"❌ Ошибка при запуске приложения: {e}", "ERROR")
        return None


# ============================================================================
# ФУНКЦИИ РАБОТЫ С ПАНЕЛЯМИ
# ============================================================================

def find_panel_with_children(window, panel_auto_id: str, child_conditions: List[Tuple[str, str]]) -> Optional:
    """
    Находит панель по AutomationId, у которой есть дочерние элементы с указанными условиями.
    """
    log_message(f"Поиск панели с AutomationId: '{panel_auto_id}'", "INFO")

    panel = find_element_by_auto_id(window, panel_auto_id)

    if not panel:
        log_message(f"  ❌ Панель '{panel_auto_id}' не найдена", "ERROR")
        return None

    log_message(f"  ✅ Панель найдена, проверяем дочерние элементы...", "SUCCESS")

    children = panel.descendants()

    all_found = True
    for key, expected_name in child_conditions:
        found = False
        auto_id = get_auto_id(key)
        if not auto_id:
            all_found = False
            continue

        for child in children:
            try:
                child_auto_id = child.element_info.automation_id if hasattr(child, 'element_info') else None
                child_name = child.window_text() if hasattr(child, 'window_text') else ""
                if child_auto_id == auto_id and child_name == expected_name:
                    log_message(f"    ✅ Найден дочерний элемент: '{key}' -> '{expected_name}'", "SUCCESS")
                    found = True
                    break
            except:
                continue

        if not found:
            log_message(f"    ❌ Не найден дочерний элемент: '{key}' -> '{expected_name}'", "ERROR")
            all_found = False

    if all_found:
        log_message(f"  ✅ Все дочерние элементы найдены", "SUCCESS")
        return panel
    else:
        log_message(f"  ❌ Не все дочерние элементы найдены", "ERROR")
        return None


# ============================================================================
# ФУНКЦИИ РАБОТЫ СО СКРИНШОТАМИ (С МАСКИРОВАНИЕМ)
# ============================================================================

def apply_masks(image: Image.Image) -> Image.Image:
    """
    Закрашивает все области из MASK_AREAS белым цветом.
    """
    if not MASK_ENABLED:
        return image

    width, height = image.size
    masked = image.copy()
    draw = ImageDraw.Draw(masked)

    for area in MASK_AREAS:
        if area.get("type") == "absolute":
            mask_area = (
                area.get("left", 0),
                area.get("top", 0),
                area.get("right", width),
                area.get("bottom", height)
            )
        else:
            mask_area = (
                int(width * area.get("left_percent", 0)),
                int(height * area.get("top_percent", 0)),
                int(width * area.get("right_percent", 1.0)),
                int(height * area.get("bottom_percent", 1.0))
            )

        draw.rectangle(mask_area, fill="white")
        log_message(f"    🎭 Маскируемая область: {mask_area}", "DEBUG")

    return masked


def take_screenshot(window, save_path: str) -> bool:
    """
    Делает скриншот только окна приложения (без панели задач).
    Использует PIL.ImageGrab для захвата экрана.
    """
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
    """
    Находит кластеры отличающихся пикселей (без использования getdata).
    """
    width, height = diff_image.size
    diff_pixels = diff_image.load()

    labels = [[0] * width for _ in range(height)]
    current_label = 0

    # Первый проход: присваиваем метки
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

    # Собираем данные по кластерам
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
    """
    Сравнивает два изображения с маскированием областей.
    """
    log_message(f"Сравнение изображений...", "INFO")

    try:
        expected = Image.open(expected_path)
        actual = Image.open(actual_path)

        if expected.size != actual.size:
            log_message(f"  Размеры изображений не совпадают: {expected.size} vs {actual.size}", "WARNING")
            actual = actual.resize(expected.size)

        # Применяем маскирование к ОБОИМ изображениям
        expected_masked = apply_masks(expected)
        actual_masked = apply_masks(actual)

        diff = ImageChops.difference(expected_masked, actual_masked)

        bbox = diff.getbbox()
        if not bbox:
            log_message(f"  ✅ Изображения идентичны", "SUCCESS")
            return False, 0.0

        # Используем numpy для подсчёта отличий (быстрее и без DeprecationWarning)
        try:
            import numpy as np
            diff_array = np.array(diff)
            # Считаем пиксели, которые не чёрные (0,0,0) и не белые (255,255,255)
            diff_mask = ~((diff_array == 0) | (diff_array == 255)).all(axis=2)
            diff_pixels = np.sum(diff_mask)
        except ImportError:
            # fallback если numpy не установлен
            diff_pixels = sum(1 for p in diff.getdata() if p != (0, 0, 0) and p != (255, 255, 255))

        total_pixels = expected.size[0] * expected.size[1]
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
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================================

def main():
    """Основная функция: полная автоматизация тестирования Dispatch Console."""
    log_message("=" * 80, "INFO")
    log_message("ЗАПУСК АВТОМАТИЧЕСКОГО ТЕСТИРОВАНИЯ DISPATCH CONSOLE", "INFO")
    log_message("=" * 80, "INFO")

    log_message(f"  Путь к консоли: {CONSOLE_EXE_PATH}", "INFO")
    log_message(f"  Папка скриншотов: {SCREENSHOTS_DIR}", "INFO")
    log_message(f"  Задержка PTT: {PTT_DELAY} сек", "INFO")

    if MASK_ENABLED:
        log_message(f"  Маскирование областей: ВКЛЮЧЕНО", "INFO")
        for area in MASK_AREAS:
            log_message(f"    - {area.get('name', 'Без имени')}: {area}", "INFO")
    else:
        log_message(f"  Маскирование областей: ОТКЛЮЧЕНО", "INFO")

    app = None
    window = None
    console_pid = None
    panel = None
    process_name = PROCESS_NAMES.get("console")

    try:
        # ШАГ 1: Запуск приложения
        log_message("\n📌 ШАГ 1: Запуск Dispatch Console", "INFO")
        log_message("-" * 40, "INFO")

        app = launch_console(CONSOLE_EXE_PATH)
        if not app:
            log_message("❌ Не удалось запустить приложение", "ERROR")
            sys.exit(1)

        # ШАГ 2: Ожидание окна подключения
        log_message("\n📌 ШАГ 2: Ожидание окна подключения", "INFO")
        log_message("-" * 40, "INFO")

        connect_window = wait_for_window(WINDOW_CONNECT_TITLE)
        if not connect_window:
            log_message("❌ Окно подключения не появилось", "ERROR")
            sys.exit(1)

        # ШАГ 3: Подключение к серверу
        log_message("\n📌 ШАГ 3: Подключение к серверу", "INFO")
        log_message("-" * 40, "INFO")

        if not click_by_key(connect_window, "btn_connect"):
            log_message("❌ Не удалось нажать кнопку Connect", "ERROR")
            sys.exit(1)

        # ШАГ 4: Ожидание главного окна
        log_message("\n📌 ШАГ 4: Ожидание окна Dispatch Console", "INFO")
        log_message("-" * 40, "INFO")

        window = wait_for_window(WINDOW_CONSOLE_PATTERN, timeout=60)
        if not window:
            log_message("❌ Окно Dispatch Console не появилось", "ERROR")
            sys.exit(1)

        # Проверяем процесс и сохраняем PID
        if process_name:
            count, pids = get_process_count(process_name)
            log_message(f"  Найдено процессов '{process_name}': {count}", "INFO")
            if count > 0:
                console_pid = pids[0]
                log_message(f"  ✅ Процесс '{process_name}' запущен (PID: {console_pid})", "SUCCESS")
            else:
                log_message(f"  ❌ Процесс '{process_name}' не найден", "ERROR")
                sys.exit(1)

        # ШАГ 5: Поиск панели VoiceIPControlRadioLarge
        log_message("\n📌 ШАГ 5: Поиск панели VoiceIPControlRadioLarge", "INFO")
        log_message("-" * 40, "INFO")

        child_conditions = [
            ("lbl_radio_name", get_dialog_text("intercom")),
            ("cbx_recipients", get_dialog_text("all_call")),
        ]

        panel = find_panel_with_children(window, "VoiceIPControlRadioLarge", child_conditions)
        if not panel:
            log_message("❌ Панель VoiceIPControlRadioLarge не найдена", "ERROR")
            sys.exit(1)

        # ШАГ 6: Нажатие PTT (первое)
        log_message("\n📌 ШАГ 6: Нажатие PTT (первое)", "INFO")
        log_message("-" * 40, "INFO")

        ptt_button = find_element_by_auto_id(panel, get_auto_id("btn_ptt"))
        if not ptt_button:
            log_message("❌ Кнопка PTT не найдена", "ERROR")
            sys.exit(1)

        ptt_button.click_input()
        log_message("  ✅ PTT нажата", "SUCCESS")

        # Небольшая задержка после нажатия PTT для отрисовки интерфейса
        log_message("  ⏳ Ожидание 0.5 сек для отрисовки интерфейса...", "INFO")
        time.sleep(0.5)

        # ШАГ 7: Скриншот
        log_message("\n📌 ШАГ 7: Создание скриншота", "INFO")
        log_message("-" * 40, "INFO")

        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

        if not take_screenshot(window, ACTUAL_SCREENSHOT_PATH):
            log_message("❌ Не удалось создать скриншот", "ERROR")
            sys.exit(1)

        # ШАГ 8: Сравнение скриншотов
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

        # ШАГ 9: Уже выполнен внутри compare_images
        log_message("\n📌 ШАГ 9: Обработка отличий выполнена в шаге 8", "INFO")

        # ================================================================
        # ШАГ 10: Ожидание и повторное нажатие PTT
        # ================================================================
        log_message("\n📌 ШАГ 10: Ожидание и повторное нажатие PTT", "INFO")
        log_message("-" * 40, "INFO")

        log_message(f"  ⏳ Ожидание {PTT_DELAY} секунд (голосовая сессия)...", "INFO")
        time.sleep(PTT_DELAY)

        # Находим кнопку заново (на случай, если она пересоздалась)
        ptt_button = find_element_by_auto_id(panel, get_auto_id("btn_ptt"), timeout=5)
        if not ptt_button:
            log_message("❌ Кнопка PTT не найдена при повторном поиске", "ERROR")
            sys.exit(1)
        else:
            ptt_button.click_input()
            log_message("  ✅ PTT нажата повторно (сессия завершена)", "SUCCESS")

        # ================================================================
        # ШАГ 11: Закрытие приложения через .close()
        # ================================================================
        log_message("\n📌 ШАГ 11: Закрытие приложения", "INFO")
        log_message("-" * 40, "INFO")

        # Небольшая задержка перед закрытием
        time.sleep(2)

        # Закрываем окно через .close() — это эквивалент нажатия на крестик
        try:
            window.close()
            log_message("  ✅ .close() выполнен", "SUCCESS")
        except Exception as e:
            log_message(f"  ❌ Ошибка при .close(): {e}", "ERROR")
            sys.exit(1)

        # Проверяем, что процесс завершился
        if process_name:
            time.sleep(2)
            count, pids = get_process_count(process_name)
            if count == 0:
                log_message(f"  ✅ Процесс '{process_name}' завершился", "SUCCESS")
            else:
                log_message(f"  ⚠️ Процесс '{process_name}' всё ещё запущен (кол-во: {count})", "WARNING")

        # Итог
        log_message("\n" + "=" * 80, "INFO")
        log_message("✅ ТЕСТИРОВАНИЕ DISPATCH CONSOLE ВЫПОЛНЕНО", "INFO")
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