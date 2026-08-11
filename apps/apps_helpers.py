"""
apps_helpers.py - Класс AppsHelper для автоматизации работы с приложением через UI Automation

Назначение: Содержит все низкоуровневые функции для взаимодействия с приложением.
Используется как библиотека утилит для configurator.py и тестов.
"""

import time
import os
import psutil
from typing import Optional, Any, List, Tuple
from PIL import Image, ImageDraw, ImageChops, ImageGrab
import pyautogui
from pywinauto import Application, Desktop
from core.config import TIMEOUT, SMALL_DELAY, LARGE_DELAY
from core.config_auto_ids import AUTO_IDS


class AppsHelper:
    """
    Класс-помощник для автоматизации работы с приложением через UI Automation.

    Атрибуты:
        app: Объект Application из pywinauto
        main_window: Главное окно приложения
        desktop: Объект Desktop для работы с диалогами
    """

    def __init__(self, app_path: Optional[str] = None):
        """
        Инициализация помощника.

        Args:
            app_path: Путь к исполняемому файлу приложения (опционально)
        """
        self.app = None
        self.main_window = None
        self.desktop = Desktop(backend="uia")

        if app_path:
            self.launch_app(app_path)

    def log_message(self, message: str, level: str = "INFO") -> None:
        """
        Выводит сообщение в консоль с временной меткой и уровнем логирования.

        Args:
            message: Текст сообщения
            level: Уровень логирования (INFO, SUCCESS, WARNING, ERROR)

        Returns:
            None

        Пример:
            self.log_message("Запуск приложения", "INFO")
            # Вывод: [2026-07-27 14:30:15] [INFO] Запуск приложения
        """
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{current_time}] [{level}] {message}")

    def launch_app(self, app_path: str) -> Optional[Application]:
        """
        Запускает приложение по указанному пути с использованием pywinauto.

        Args:
            app_path: Путь к исполняемому файлу приложения

        Returns:
            Объект Application при успешном запуске, None при ошибке
        """
        self.log_message(f"Запуск приложения: {app_path}", "INFO")
        try:
            if not os.path.exists(app_path):
                self.log_message(f"❌ Файл не найден: {app_path}", "ERROR")
                return None

            self.app = Application(backend="uia").start(app_path)
            time.sleep(LARGE_DELAY)
            self.log_message("✅ Приложение запущено", "SUCCESS")
            return self.app
        except Exception as e:
            self.log_message(f"❌ Ошибка при запуске приложения: {e}", "ERROR")
            return None

    def connect_app(self, process_id: int) -> Optional[Application]:
        """
        Подключается к уже запущенному приложению по ID процесса.

        Args:
            process_id: ID процесса приложения

        Returns:
            Объект Application при успешном подключении, None при ошибке
        """
        self.log_message(f"Подключение к процессу: {process_id}", "INFO")
        try:
            self.app = Application(backend="uia").connect(process=process_id)
            self.log_message(f"✅ Подключено к процессу {process_id}", "SUCCESS")
            return self.app
        except Exception as e:
            self.log_message(f"❌ Ошибка при подключении: {e}", "ERROR")
            return None

    def find_window(self, title: str, timeout: int = TIMEOUT) -> Optional[Any]:
        """
        Ищет окно с указанным заголовком в приложении.

        Args:
            title: Заголовок окна (поддерживает регулярные выражения)
            timeout: Время ожидания в секундах

        Returns:
            Объект Window при успешном поиске, None при ошибке
        """
        if not self.app:
            self.log_message("❌ Приложение не запущено", "ERROR")
            return None

        self.log_message(f"Поиск окна: '{title}'...", "INFO")
        try:
            window = self.app.window(title_re=title).wait('visible', timeout=timeout)
            self.log_message(f"✅ Окно найдено: '{title}'", "SUCCESS")
            return window
        except Exception as e:
            self.log_message(f"❌ Окно не найдено: {e}", "ERROR")
            return None

    def set_main_window(self, title: str, timeout: int = TIMEOUT) -> bool:
        """
        Устанавливает главное окно приложения.

        Args:
            title: Заголовок главного окна
            timeout: Время ожидания в секундах

        Returns:
            True при успешной установке, False при ошибке
        """
        window = self.find_window(title, timeout)
        if window:
            self.main_window = window
            return True
        return False

    def get_auto_id(self, key: str) -> Optional[str]:
        """
        Возвращает AutomationId из словаря AUTO_IDS по ключу.

        Args:
            key: Ключ для поиска в словаре AUTO_IDS

        Returns:
            Строка AutomationId или None, если ключ не найден
        """
        auto_id = AUTO_IDS.get(key)
        if not auto_id:
            self.log_message(f"❌ Ключ '{key}' не найден в AUTO_IDS", "ERROR")
        return auto_id

    def find_element_by_auto_id(self, window: Any, auto_id: str, timeout: int = TIMEOUT) -> Optional[Any]:
        """
        Ищет элемент по AutomationId внутри указанного окна.

        Args:
            window: Объект окна из pywinauto
            auto_id: AutomationId для поиска
            timeout: Время ожидания в секундах

        Returns:
            Найденный элемент или None при ошибке
        """
        self.log_message(f"  Поиск элемента по AutomationId: '{auto_id}'", "INFO")
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
                                self.log_message(f"    ✅ Найден: '{elem_name}'", "SUCCESS")
                                return elem
                    except:
                        continue
                time.sleep(0.5)
            except Exception as e:
                self.log_message(f"  Ошибка при поиске: {e}", "WARNING")
                time.sleep(0.5)

        self.log_message(f"  ❌ Элемент с AutomationId '{auto_id}' не найден", "ERROR")
        return None

    def find_element_by_key(self, window: Any, key: str, timeout: int = TIMEOUT) -> Optional[Any]:
        """
        Находит элемент по ключу из AUTO_IDS.

        Args:
            window: Объект окна из pywinauto
            key: Ключ в словаре AUTO_IDS
            timeout: Время ожидания в секундах

        Returns:
            Найденный элемент или None при ошибке
        """
        auto_id = self.get_auto_id(key)
        if not auto_id:
            return None
        return self.find_element_by_auto_id(window, auto_id, timeout)

    def click_by_key(self, window: Any, key: str, timeout: int = TIMEOUT) -> bool:
        """
        Находит элемент по ключу из AUTO_IDS и выполняет клик.

        Args:
            window: Объект окна из pywinauto
            key: Ключ в словаре AUTO_IDS
            timeout: Время ожидания в секундах

        Returns:
            True при успешном клике, False при ошибке
        """
        self.log_message(f"Клик по ключу: '{key}'", "INFO")

        auto_id = self.get_auto_id(key)
        if not auto_id:
            return False

        element = self.find_element_by_auto_id(window, auto_id, timeout)
        if not element:
            self.log_message(f"❌ Не удалось найти элемент по ключу '{key}'", "ERROR")
            return False

        try:
            element.click_input()
            time.sleep(SMALL_DELAY)
            self.log_message(f"  ✅ Клик выполнен", "SUCCESS")
            return True
        except:
            try:
                element.click()
                time.sleep(SMALL_DELAY)
                self.log_message(f"  ✅ Клик выполнен", "SUCCESS")
                return True
            except Exception as e:
                self.log_message(f"  ❌ Ошибка при клике: {e}", "ERROR")
                return False

    def click_by_key_main(self, key: str, timeout: int = TIMEOUT) -> bool:
        """
        Выполняет клик по элементу в главном окне по ключу из AUTO_IDS.

        Args:
            key: Ключ в словаре AUTO_IDS
            timeout: Время ожидания в секундах

        Returns:
            True при успешном клике, False при ошибке
        """
        if not self.main_window:
            self.log_message("❌ Главное окно не установлено", "ERROR")
            return False
        return self.click_by_key(self.main_window, key, timeout)

    def click_element_safe(self, element: Any, name: str = "элемент") -> bool:
        """
        Безопасный клик по элементу с несколькими способами.

        Args:
            element: Объект элемента из pywinauto
            name: Название элемента для логирования

        Returns:
            True при успешном клике, False при ошибке
        """
        if not element:
            self.log_message(f"  ❌ {name} отсутствует", "ERROR")
            return False

        try:
            element.click_input()
            self.log_message(f"  ✅ {name} нажат (click_input)", "SUCCESS")
            return True
        except:
            try:
                element.click()
                self.log_message(f"  ✅ {name} нажат (click)", "SUCCESS")
                return True
            except:
                try:
                    element.invoke()
                    self.log_message(f"  ✅ {name} нажат (invoke)", "SUCCESS")
                    return True
                except Exception as e:
                    self.log_message(f"  ❌ Ошибка при клике по {name}: {e}", "ERROR")
                    return False

    def set_combo_text_by_key(self, window: Any, key: str, value: str, timeout: int = TIMEOUT) -> bool:
        """
               Находит ComboBox по ключу из AUTO_IDS и устанавливает указанное значение.
               Поддерживает разные способы ввода для разных типов ComboBox.

               Args:
                   window: Объект окна из pywinauto
                   key: Ключ в словаре AUTO_IDS
                   value: Значение для установки в ComboBox
                   timeout: Время ожидания в секундах

               Returns:
                   True при успешной установке значения, False при ошибке
               """
        auto_id = self.get_auto_id(key)
        if not auto_id:
            return False

        self.log_message(f"Поиск ComboBox по ключу: '{key}'", "INFO")
        self.log_message(f"  Устанавливаем значение: '{value}'", "INFO")

        combo_box = self.find_element_by_auto_id(window, auto_id, timeout)
        if not combo_box:
            self.log_message(f"  ❌ ComboBox не найден", "ERROR")
            return False

        # СПОСОБ 1: Пробуем установить через set_text (работает для WPF)
        try:
            if hasattr(combo_box, 'set_text'):
                combo_box.set_text(value)
                time.sleep(SMALL_DELAY)
                self.log_message(f"  ✅ Значение '{value}' установлено (set_text)", "SUCCESS")
                return True
        except Exception as e:
            self.log_message(f"  ⚠️ Способ set_text не сработал: {e}", "WARNING")

        # СПОСОБ 2: Пробуем через элемент WPF напрямую
        try:
            # Для WPF элементов часто работает через element_info
            if hasattr(combo_box, 'element_info'):
                # Пробуем найти TextBox внутри ComboBox
                descendants = combo_box.descendants()
                for child in descendants:
                    try:
                        if hasattr(child, 'element_info'):
                            control_type = child.element_info.control_type if hasattr(child.element_info,
                                                                                      'control_type') else ""
                            if "Edit" in control_type or "Text" in control_type:
                                child.set_text(value)
                                time.sleep(SMALL_DELAY)
                                self.log_message(f"  ✅ Значение '{value}' установлено (через дочерний Edit)", "SUCCESS")
                                return True
                    except:
                        continue
        except Exception as e:
            self.log_message(f"  ⚠️ Способ через дочерний Edit не сработал: {e}", "WARNING")

        # СПОСОБ 3: Пробуем через LegacyIAccessible Value
        try:
            if hasattr(combo_box, 'legacy_accessible'):
                legacy = combo_box.legacy_accessible
                if legacy and hasattr(legacy, 'Value'):
                    legacy.Value = value
                    time.sleep(SMALL_DELAY)
                    self.log_message(f"  ✅ Значение '{value}' установлено (LegacyIAccessible)", "SUCCESS")
                    return True
        except Exception as e:
            self.log_message(f"  ⚠️ Способ LegacyIAccessible не сработал: {e}", "WARNING")

        # СПОСОБ 4: Пробуем через element_info.set_value
        try:
            if hasattr(combo_box, 'element_info') and hasattr(combo_box.element_info, 'set_value'):
                combo_box.element_info.set_value(value)
                time.sleep(SMALL_DELAY)
                self.log_message(f"  ✅ Значение '{value}' установлено (element_info.set_value)", "SUCCESS")
                return True
        except Exception as e:
            self.log_message(f"  ⚠️ Способ element_info.set_value не сработал: {e}", "WARNING")

        # СПОСОБ 5: Ввод с клавиатуры с использованием буфера обмена (для IP-адресов)
        try:
            combo_box.click_input()
            time.sleep(SMALL_DELAY)

            # Выделяем всё
            combo_box.type_keys("^a")
            time.sleep(SMALL_DELAY)

            # Копируем значение в буфер обмена (Windows)
            import subprocess
            subprocess.run(['powershell', '-command', f'Set-Clipboard -Value "{value}"'],
                           capture_output=True, text=True)
            time.sleep(SMALL_DELAY)

            # Вставляем из буфера
            combo_box.type_keys("^v")
            time.sleep(SMALL_DELAY)

            # Нажимаем Enter или Tab для подтверждения
            combo_box.type_keys("{ENTER}")
            time.sleep(SMALL_DELAY)

            self.log_message(f"  ✅ Значение '{value}' установлено (вставка из буфера)", "SUCCESS")
            return True
        except Exception as e:
            self.log_message(f"  ⚠️ Способ вставки из буфера не сработал: {e}", "WARNING")

        # СПОСОБ 6: Классический способ с кликом и посимвольным вводом
        try:
            # Кликаем для фокуса
            combo_box.click_input()
            time.sleep(SMALL_DELAY)

            # Пробуем очистить через Ctrl+A и Delete
            combo_box.type_keys("^a")
            time.sleep(SMALL_DELAY)
            combo_box.type_keys("{DEL}")
            time.sleep(SMALL_DELAY)

            # Вводим значение посимвольно с задержкой
            self.log_message(f"  Ввод значения посимвольно...", "INFO")
            for char in value:
                combo_box.type_keys(char)
                time.sleep(0.1)  # Задержка между символами

            time.sleep(SMALL_DELAY)

            # Нажимаем Enter для подтверждения
            combo_box.type_keys("{ENTER}")
            time.sleep(SMALL_DELAY)

            self.log_message(f"  ✅ Значение '{value}' установлено (посимвольный ввод)", "SUCCESS")
            return True
        except Exception as e:
            self.log_message(f"  ⚠️ Способ посимвольного ввода не сработал: {e}", "WARNING")

        # Если все способы не сработали
        self.log_message(f"  ❌ Не удалось установить значение '{value}' ни одним из способов", "ERROR")
        return False

    def select_combo_item_by_key(self, window: Any, key: str, value: str, timeout: int = TIMEOUT) -> bool:
        """
        Выбирает значение из выпадающего списка ComboBox по ключу из AUTO_IDS.
        Используется для ComboBox, которые поддерживают только выбор из списка.

        Args:
            window: Объект окна из pywinauto
            key: Ключ в словаре AUTO_IDS
            value: Значение для выбора из списка
            timeout: Время ожидания в секундах

        Returns:
            True при успешном выборе значения, False при ошибке

        Пример:
            # Выбор значения из выпадающего списка
            helper.select_combo_item_by_key(window, "console_type", "TRBOnetOne")
        """
        auto_id = self.get_auto_id(key)
        if not auto_id:
            return False

        self.log_message(f"Выбор значения из ComboBox по ключу: '{key}' (AutomationId: '{auto_id}')", "INFO")
        self.log_message(f"  Выбираем значение: '{value}'", "INFO")

        combo_box = self.find_element_by_auto_id(window, auto_id, timeout)
        if not combo_box:
            self.log_message(f"  ❌ ComboBox не найден", "ERROR")
            return False

        try:
            # Кликаем для раскрытия списка
            combo_box.click_input()
            time.sleep(SMALL_DELAY)

            # Используем select для выбора значения
            combo_box.select(value)
            time.sleep(SMALL_DELAY)

            self.log_message(f"  ✅ Значение '{value}' выбрано", "SUCCESS")
            return True
        except Exception as e:
            self.log_message(f"  ❌ Ошибка при выборе значения: {e}", "ERROR")
            return False

    def set_combo_value_by_key_main(self, key: str, value: str, timeout: int = TIMEOUT) -> bool:
        """
        Устанавливает значение ComboBox в главном окне по ключу из AUTO_IDS.

        Args:
            key: Ключ в словаре AUTO_IDS
            value: Значение для установки в ComboBox
            timeout: Время ожидания в секундах

        Returns:
            True при успешной установке значения, False при ошибке
        """
        if not self.main_window:
            self.log_message("❌ Главное окно не установлено", "ERROR")
            return False
        return self.set_combo_text_by_key(self.main_window, key, value, timeout)

    def wait_for_text(self, window: Any, text: str, timeout: int = TIMEOUT) -> bool:
        """
        Ожидает появления указанного текста в любом элементе окна.

        Args:
            window: Объект окна из pywinauto
            text: Текст для поиска
            timeout: Время ожидания в секундах

        Returns:
            True при обнаружении текста, False при превышении таймаута
        """
        self.log_message(f"  Ожидание текста: '{text}'...", "INFO")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                all_elements = window.descendants()
                for elem in all_elements:
                    try:
                        elem_name = elem.window_text()
                        if text.lower() in elem_name.lower():
                            self.log_message(f"  ✅ Текст найден: '{text}'", "SUCCESS")
                            return True
                    except:
                        continue
            except:
                pass
            time.sleep(0.5)

        self.log_message(f"  ❌ Текст не найден: '{text}'", "ERROR")
        return False

    def wait_for_text_main(self, text: str, timeout: int = TIMEOUT) -> bool:
        """
        Ожидает появления указанного текста в главном окне.

        Args:
            text: Текст для поиска
            timeout: Время ожидания в секундах

        Returns:
            True при обнаружении текста, False при превышении таймаута
        """
        if not self.main_window:
            self.log_message("❌ Главное окно не установлено", "ERROR")
            return False
        return self.wait_for_text(self.main_window, text, timeout)

    def wait_for_dialog_text(self, text: str, timeout: int = TIMEOUT) -> bool:
        """
        Ожидает появления указанного текста в любом диалоговом окне приложения.
        Поиск ведётся по всем окнам (расширенная версия).

        Args:
            text: Текст для поиска
            timeout: Время ожидания в секундах

        Returns:
            True при обнаружении текста, False при превышении таймаута
        """
        self.log_message(f"  Ожидание текста в диалоге: '{text}'...", "INFO")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                windows = self.desktop.windows()

                for win in windows:
                    try:
                        win_text = win.window_text()
                        if win_text and text.lower() in win_text.lower():
                            self.log_message(f"  ✅ Текст найден в окне: '{win_text}'", "SUCCESS")
                            return True

                        all_elements = win.descendants()
                        for elem in all_elements:
                            try:
                                elem_text = elem.window_text()
                                if elem_text and text.lower() in elem_text.lower():
                                    self.log_message(f"  ✅ Текст найден в элементе: '{elem_text}'", "SUCCESS")
                                    return True
                            except:
                                continue
                    except:
                        continue
            except Exception as e:
                self.log_message(f"  Ошибка при поиске диалога: {e}", "WARNING")

            time.sleep(0.5)

        self.log_message(f"  ❌ Текст не найден: '{text}'", "ERROR")
        return False

    def click_dialog_button(self, button_text: str, timeout: int = TIMEOUT) -> bool:
        """
        Ищет кнопку с указанным текстом в любом диалоговом окне приложения и кликает по ней.

        Args:
            button_text: Текст на кнопке
            timeout: Время ожидания в секундах

        Returns:
            True при успешном клике, False при ошибке
        """
        self.log_message(f"  Поиск кнопки '{button_text}' в диалоге...", "INFO")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                windows = self.desktop.windows(title_re=".*TRBOnet Enterprise.*")

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
                                    self.log_message(f"  ✅ Кнопка '{button_text}' нажата", "SUCCESS")
                                    return True
                            except:
                                continue
                    except:
                        continue
            except Exception as e:
                self.log_message(f"  Ошибка при поиске кнопки: {e}", "WARNING")

            time.sleep(0.5)

        self.log_message(f"  ❌ Кнопка '{button_text}' не найдена", "ERROR")
        return False

    def find_element_by_text(self, window: Any, text: str, timeout: int = TIMEOUT) -> Optional[Any]:
        """
        Ищет элемент по тексту внутри указанного окна.

        Args:
            window: Объект окна из pywinauto
            text: Текст для поиска
            timeout: Время ожидания в секундах

        Returns:
            Найденный элемент или None при ошибке
        """
        self.log_message(f"  Поиск элемента по тексту: '{text}'...", "INFO")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                all_elements = window.descendants()
                for elem in all_elements:
                    try:
                        elem_name = elem.window_text()
                        if text.lower() in elem_name.lower():
                            self.log_message(f"  ✅ Элемент найден: '{text}'", "SUCCESS")
                            return elem
                    except:
                        continue
                time.sleep(0.5)
            except Exception as e:
                self.log_message(f"  Ошибка при поиске: {e}", "WARNING")
                time.sleep(0.5)

        self.log_message(f"  ❌ Элемент с текстом '{text}' не найден", "ERROR")
        return None

    def find_element_by_text_main(self, text: str, timeout: int = TIMEOUT) -> Optional[Any]:
        """
        Ищет элемент по тексту в главном окне.

        Args:
            text: Текст для поиска
            timeout: Время ожидания в секундах

        Returns:
            Найденный элемент или None при ошибке
        """
        if not self.main_window:
            self.log_message("❌ Главное окно не установлено", "ERROR")
            return None
        return self.find_element_by_text(self.main_window, text, timeout)

    def type_text(self, window: Any, text: str, clear_first: bool = True) -> bool:
        """
        Вводит текст в активный элемент окна.

        Args:
            window: Объект окна из pywinauto
            text: Текст для ввода
            clear_first: Очистить поле перед вводом

        Returns:
            True при успешном вводе, False при ошибке
        """
        try:
            if clear_first:
                window.type_keys("^a")  # Ctrl+A - выделить всё
                time.sleep(SMALL_DELAY)
                window.type_keys("{DEL}")  # Delete - удалить выделенное
                time.sleep(SMALL_DELAY)

            window.type_keys(text)
            time.sleep(SMALL_DELAY)
            self.log_message(f"  ✅ Текст введен: '{text}'", "SUCCESS")
            return True
        except Exception as e:
            self.log_message(f"  ❌ Ошибка при вводе текста: {e}", "ERROR")
            return False

    def get_element_text(self, element: Any) -> Optional[str]:
        """
        Получает текст из элемента.

        Args:
            element: Элемент из pywinauto

        Returns:
            Текст элемента или None при ошибке
        """
        try:
            text = element.window_text()
            return text
        except Exception as e:
            self.log_message(f"  ❌ Ошибка при получении текста: {e}", "ERROR")
            return None

    def scroll_element(self, element: Any, direction: str = "Down", scroll_count: int = 1) -> bool:
        """
        Выполняет скроллинг указанного элемента в заданном направлении.

        Args:
            element: Объект элемента из pywinauto (окно, панель или конкретный элемент)
            direction: Направление скроллинга ("Up" или "Down")
            scroll_count: Количество шагов скроллинга (по умолчанию 1)

        Returns:
            True при успешном скроллинге, False при ошибке или если элемент не найден

        Пример:
            # Скролл вниз на 3 шага
            helper.scroll_element(window, "Down", 3)

            # Скролл вверх на 1 шаг
            helper.scroll_element(window, "Up")
        """
        self.log_message(f"  Выполнение скролла: {direction} для элемента", "INFO")

        try:
            # Ищем дочерний элемент с типом ScrollBar
            scrollbar = None

            # Проверяем все дочерние элементы
            all_descendants = element.descendants()

            for child in all_descendants:
                try:
                    # Получаем control_type элемента
                    if hasattr(child, 'element_info') and hasattr(child.element_info, 'control_type'):
                        control_type = child.element_info.control_type

                        # Ищем ScrollBar
                        if "ScrollBar" in control_type or "scroll" in control_type.lower():
                            scrollbar = child
                            self.log_message(f"    Найден ScrollBar: {control_type}", "INFO")
                            break
                except:
                    continue

            # Если ScrollBar не найден, проверяем сам элемент
            if not scrollbar:
                try:
                    # Проверяем, может сам элемент является скроллом
                    if hasattr(element, 'element_info') and hasattr(element.element_info, 'control_type'):
                        control_type = element.element_info.control_type
                        if "ScrollBar" in control_type or "scroll" in control_type.lower():
                            scrollbar = element
                            self.log_message(f"    Элемент является ScrollBar: {control_type}", "INFO")
                except:
                    pass

            # Если скролл не найден
            if not scrollbar:
                self.log_message(f"  ❌ ScrollBar не найден в элементе", "ERROR")
                return False

            # Выполняем скроллинг в зависимости от направления
            for i in range(scroll_count):
                try:
                    if direction.lower() == "up":
                        # Прокрутка вверх
                        scrollbar.type_keys("{PGUP}")  # Page Up
                        # Альтернативный способ: scrollbar.scroll_up() если доступно
                        time.sleep(SMALL_DELAY)
                    elif direction.lower() == "down":
                        # Прокрутка вниз
                        scrollbar.type_keys("{PGDN}")  # Page Down
                        # Альтернативный способ: scrollbar.scroll_down() если доступно
                        time.sleep(SMALL_DELAY)
                    else:
                        self.log_message(f"  ❌ Неизвестное направление: {direction}", "ERROR")
                        return False
                except Exception as e:
                    # Если не сработал type_keys, пробуем альтернативные методы
                    try:
                        if direction.lower() == "up":
                            # Пробуем через клик по верхней части
                            scrollbar.click_input(button='left', coords=(0, 10))
                            time.sleep(SMALL_DELAY)
                        elif direction.lower() == "down":
                            # Пробуем через клик по нижней части
                            scrollbar.click_input(button='left', coords=(0, 90))
                            time.sleep(SMALL_DELAY)
                    except Exception as e2:
                        self.log_message(f"  ❌ Ошибка при скроллинге: {e2}", "ERROR")
                        return False

            self.log_message(f"  ✅ Скролл выполнен: {direction} ({scroll_count} раз)", "SUCCESS")
            return True

        except Exception as e:
            self.log_message(f"  ❌ Ошибка при скроллинге: {e}", "ERROR")
            return False

    def scroll_by_key(self, window: Any, key: str, direction: str = "Down", scroll_count: int = 1,
                      timeout: int = TIMEOUT) -> bool:
        """
        Находит элемент по ключу из AUTO_IDS и выполняет скроллинг.

        Args:
            window: Объект окна из pywinauto
            key: Ключ в словаре AUTO_IDS для поиска элемента со скроллом
            direction: Направление скроллинга ("Up" или "Down")
            scroll_count: Количество шагов скроллинга (по умолчанию 1)
            timeout: Время ожидания в секундах

        Returns:
            True при успешном скроллинге, False при ошибке

        Пример:
            # Найти элемент по ключу и прокрутить вниз
            helper.scroll_by_key(window, "scroll_view", "Down", 3)
        """
        auto_id = self.get_auto_id(key)
        if not auto_id:
            return False

        self.log_message(f"Поиск элемента с прокруткой по ключу: '{key}'", "INFO")

        element = self.find_element_by_auto_id(window, auto_id, timeout)
        if not element:
            self.log_message(f"❌ Не удалось найти элемент по ключу '{key}'", "ERROR")
            return False

        return self.scroll_element(element, direction, scroll_count)

    def scroll_by_key_main(self, key: str, direction: str = "Down", scroll_count: int = 1,
                           timeout: int = TIMEOUT) -> bool:
        """
        Находит элемент по ключу из AUTO_IDS в главном окне и выполняет скроллинг.

        Args:
            key: Ключ в словаре AUTO_IDS для поиска элемента со скроллом
            direction: Направление скроллинга ("Up" или "Down")
            scroll_count: Количество шагов скроллинга (по умолчанию 1)
            timeout: Время ожидания в секундах

        Returns:
            True при успешном скроллинге, False при ошибке
        """
        if not self.main_window:
            self.log_message("❌ Главное окно не установлено", "ERROR")
            return False

        return self.scroll_by_key(self.main_window, key, direction, scroll_count, timeout)

    def scroll_to_element(self, window: Any, target_key: str, container_key: Optional[str] = None,
                          max_scrolls: int = 10) -> bool:
        """
        Прокручивает контейнер до появления целевого элемента.

        Args:
            window: Объект окна из pywinauto
            target_key: Ключ элемента, который нужно найти (из AUTO_IDS)
            container_key: Ключ контейнера с прокруткой (из AUTO_IDS),
                          если None - ищет скролл в родительском окне
            max_scrolls: Максимальное количество попыток прокрутки

        Returns:
            True если элемент найден и виден, False если не найден

        Пример:
            # Прокрутить список до появления нужного элемента
            helper.scroll_to_element(window, "target_item", "scroll_container")
        """
        self.log_message(f"Прокрутка до элемента: '{target_key}'", "INFO")

        # Если указан контейнер, находим его
        if container_key:
            container_auto_id = self.get_auto_id(container_key)
            if not container_auto_id:
                return False

            container = self.find_element_by_auto_id(window, container_auto_id)
            if not container:
                self.log_message(f"❌ Контейнер не найден: '{container_key}'", "ERROR")
                return False
        else:
            container = window

        # Ищем целевой элемент
        target_auto_id = self.get_auto_id(target_key)
        if not target_auto_id:
            return False

        # Пробуем найти элемент с прокруткой
        for i in range(max_scrolls):
            # Проверяем, виден ли целевой элемент
            target_element = self.find_element_by_auto_id(window, target_auto_id, timeout=2)
            if target_element:
                self.log_message(f"  ✅ Элемент '{target_key}' найден после {i} прокруток", "SUCCESS")
                return True

            # Если элемент не найден, скроллим вниз
            self.log_message(f"  Прокрутка {i + 1}/{max_scrolls}...", "INFO")
            if not self.scroll_element(container, "Down", 1):
                self.log_message(f"  ❌ Не удалось выполнить прокрутку", "ERROR")
                return False

        self.log_message(f"  ❌ Элемент '{target_key}' не найден после {max_scrolls} прокруток", "ERROR")
        return False

    def scroll_to_element_main(self, target_key: str, container_key: Optional[str] = None,
                               max_scrolls: int = 10) -> bool:
        """
        Прокручивает контейнер в главном окне до появления целевого элемента.

        Args:
            target_key: Ключ элемента, который нужно найти (из AUTO_IDS)
            container_key: Ключ контейнера с прокруткой (из AUTO_IDS)
            max_scrolls: Максимальное количество попыток прокрутки

        Returns:
            True если элемент найден и виден, False если не найден
        """
        if not self.main_window:
            self.log_message("❌ Главное окно не установлено", "ERROR")
            return False

        return self.scroll_to_element(self.main_window, target_key, container_key, max_scrolls)

    def state_check_box(self, window: Any, key: str, state: bool, timeout: int = TIMEOUT) -> bool:
        """
        Устанавливает состояние чек-бокса (включен/выключен) по ключу из AUTO_IDS.

        Args:
            window: Объект окна из pywinauto
            key: Ключ чек-бокса в словаре AUTO_IDS
            state: Требуемое состояние (True - включить/отметить, False - выключить/снять отметку)
            timeout: Время ожидания в секундах

        Returns:
            True при успешной установке состояния, False при ошибке

        Пример:
            # Включить чек-бокс
            helper.state_check_box(window, "enable_feature", True)

            # Выключить чек-бокс
            helper.state_check_box(window, "enable_feature", False)
        """
        self.log_message(f"Установка состояния чек-бокса по ключу: '{key}'", "INFO")
        self.log_message(f"  Требуемое состояние: {'Включить' if state else 'Выключить'}", "INFO")

        # Получаем AutomationId по ключу
        auto_id = self.get_auto_id(key)
        if not auto_id:
            return False

        # Находим элемент чек-бокса
        check_box = self.find_element_by_auto_id(window, auto_id, timeout)
        if not check_box:
            self.log_message(f"  ❌ Чек-бокс не найден по ключу '{key}'", "ERROR")
            return False

        try:
            # Получаем текущее состояние чек-бокса
            current_state = False

            # Пробуем получить состояние через toggle_state
            if hasattr(check_box, 'get_toggle_state'):
                try:
                    toggle_state = check_box.get_toggle_state()
                    current_state = toggle_state == 1  # 1 - включен, 0 - выключен
                    self.log_message(
                        f"  Текущее состояние (get_toggle_state): {'Включен' if current_state else 'Выключен'}", "INFO")
                except:
                    pass

            # Альтернативный способ: проверка через element_info
            if not current_state and hasattr(check_box, 'element_info'):
                try:
                    if hasattr(check_box.element_info, 'toggle_state'):
                        toggle_state = check_box.element_info.toggle_state
                        current_state = toggle_state == 1
                        self.log_message(
                            f"  Текущее состояние (element_info): {'Включен' if current_state else 'Выключен'}", "INFO")
                except:
                    pass

            # Альтернативный способ: проверка атрибута IsChecked
            if not current_state and hasattr(check_box, 'is_checked'):
                try:
                    current_state = check_box.is_checked()
                    self.log_message(f"  Текущее состояние (is_checked): {'Включен' if current_state else 'Выключен'}",
                                     "INFO")
                except:
                    pass

            # Если состояние уже соответствует требуемому, ничего не делаем
            if current_state == state:
                self.log_message(f"  ✅ Чек-бокс уже в требуемом состоянии: {'Включен' if state else 'Выключен'}",
                                 "SUCCESS")
                return True

            # Выполняем клик для изменения состояния
            self.log_message(f"  Изменение состояния чек-бокса...", "INFO")

            try:
                # Пробуем кликнуть через click_input()
                check_box.click_input()
                time.sleep(SMALL_DELAY)
            except:
                try:
                    # Если click_input не работает, пробуем click()
                    check_box.click()
                    time.sleep(SMALL_DELAY)
                except Exception as e:
                    self.log_message(f"  ❌ Ошибка при клике: {e}", "ERROR")
                    return False

            # Проверяем, изменилось ли состояние
            time.sleep(SMALL_DELAY)

            # Проверяем новое состояние
            new_state = False

            if hasattr(check_box, 'get_toggle_state'):
                try:
                    toggle_state = check_box.get_toggle_state()
                    new_state = toggle_state == 1
                except:
                    pass

            if not new_state and hasattr(check_box, 'element_info'):
                try:
                    if hasattr(check_box.element_info, 'toggle_state'):
                        toggle_state = check_box.element_info.toggle_state
                        new_state = toggle_state == 1
                except:
                    pass

            if not new_state and hasattr(check_box, 'is_checked'):
                try:
                    new_state = check_box.is_checked()
                except:
                    pass

            # Проверяем, достигнуто ли требуемое состояние
            if new_state == state:
                self.log_message(f"  ✅ Состояние успешно изменено: {'Включен' if state else 'Выключен'}", "SUCCESS")
                return True
            else:
                self.log_message(
                    f"  ⚠️ Состояние не изменилось после клика. Текущее: {'Включен' if new_state else 'Выключен'}",
                    "WARNING")
                return False

        except Exception as e:
            self.log_message(f"  ❌ Ошибка при установке состояния чек-бокса: {e}", "ERROR")
            return False

    def get_check_box_state(self, window: Any, key: str, timeout: int = TIMEOUT) -> Optional[bool]:
        """
        Получает текущее состояние чек-бокса по ключу из AUTO_IDS.

        Args:
            window: Объект окна из pywinauto
            key: Ключ чек-бокса в словаре AUTO_IDS
            timeout: Время ожидания в секундах

        Returns:
            True если включен, False если выключен, None при ошибке

        Пример:
            # Получить состояние чек-бокса
            is_checked = helper.get_check_box_state(window, "enable_feature")
            if is_checked is not None:
                print(f"Чек-бокс {'включен' if is_checked else 'выключен'}")
        """
        self.log_message(f"Получение состояния чек-бокса по ключу: '{key}'", "INFO")

        # Получаем AutomationId по ключу
        auto_id = self.get_auto_id(key)
        if not auto_id:
            return None

        # Находим элемент чек-бокса
        check_box = self.find_element_by_auto_id(window, auto_id, timeout)
        if not check_box:
            self.log_message(f"  ❌ Чек-бокс не найден по ключу '{key}'", "ERROR")
            return None

        try:
            # Пробуем получить состояние через toggle_state
            if hasattr(check_box, 'get_toggle_state'):
                try:
                    toggle_state = check_box.get_toggle_state()
                    state = toggle_state == 1
                    self.log_message(f"  ✅ Состояние (get_toggle_state): {'Включен' if state else 'Выключен'}",
                                     "SUCCESS")
                    return state
                except:
                    pass

            # Альтернативный способ: проверка через element_info
            if hasattr(check_box, 'element_info'):
                try:
                    if hasattr(check_box.element_info, 'toggle_state'):
                        toggle_state = check_box.element_info.toggle_state
                        state = toggle_state == 1
                        self.log_message(f"  ✅ Состояние (element_info): {'Включен' if state else 'Выключен'}",
                                         "SUCCESS")
                        return state
                except:
                    pass

            # Альтернативный способ: проверка атрибута IsChecked
            if hasattr(check_box, 'is_checked'):
                try:
                    state = check_box.is_checked()
                    self.log_message(f"  ✅ Состояние (is_checked): {'Включен' if state else 'Выключен'}", "SUCCESS")
                    return state
                except:
                    pass

            # Альтернативный способ: проверка через window_text() (может содержать статус)
            try:
                text = check_box.window_text()
                # Проверяем, содержит ли текст индикатор состояния
                if "checked" in text.lower():
                    state = True
                    self.log_message(f"  ✅ Состояние (window_text): {'Включен' if state else 'Выключен'}", "SUCCESS")
                    return state
                elif "unchecked" in text.lower():
                    state = False
                    self.log_message(f"  ✅ Состояние (window_text): {'Включен' if state else 'Выключен'}", "SUCCESS")
                    return state
            except:
                pass

            self.log_message(f"  ❌ Не удалось определить состояние чек-бокса", "ERROR")
            return None

        except Exception as e:
            self.log_message(f"  ❌ Ошибка при получении состояния чек-бокса: {e}", "ERROR")
            return None

    def set_text(self, window: Any, key: str, value: str, timeout: int = TIMEOUT, clear_first: bool = True) -> bool:
        """
        Вводит текст в текстовое поле по ключу из AUTO_IDS.

        Args:
            window: Объект окна из pywinauto
            key: Ключ текстового поля в словаре AUTO_IDS
            value: Текст для ввода
            timeout: Время ожидания в секундах
            clear_first: Очистить поле перед вводом (по умолчанию True)

        Returns:
            True при успешном вводе текста, False при ошибке

        Пример:
            # Ввести текст в поле
            helper.set_text(window, "username_field", "admin")

            # Ввести текст без очистки поля
            helper.set_text(window, "username_field", "admin", clear_first=False)
        """
        auto_id = self.get_auto_id(key)
        if not auto_id:
            return False

        self.log_message(f"Поиск текстового поля по ключу: '{key}'", "INFO")
        self.log_message(f"  Вводим значение: '{value}'", "INFO")

        text_field = self.find_element_by_auto_id(window, auto_id, timeout)
        if not text_field:
            self.log_message(f"  ❌ Текстовое поле не найдено", "ERROR")
            return False

        try:
            # Кликаем по полю, чтобы установить фокус
            try:
                text_field.click_input()
                time.sleep(SMALL_DELAY)
            except:
                try:
                    text_field.click()
                    time.sleep(SMALL_DELAY)
                except Exception as e:
                    self.log_message(f"  ⚠️ Не удалось кликнуть по полю: {e}", "WARNING")

            # Очищаем поле, если требуется
            if clear_first:
                try:
                    # Ctrl+A - выделить всё
                    text_field.type_keys("^a")
                    time.sleep(SMALL_DELAY)
                    # Delete - удалить выделенное
                    text_field.type_keys("{DEL}")
                    time.sleep(SMALL_DELAY)
                    self.log_message(f"  Поле очищено", "INFO")
                except Exception as e:
                    self.log_message(f"  ⚠️ Не удалось очистить поле: {e}", "WARNING")

            # Вводим текст
            try:
                # Пробуем ввести через type_keys
                text_field.type_keys(value)
                time.sleep(SMALL_DELAY)
            except Exception as e:
                self.log_message(f"  ⚠️ Ошибка при вводе через type_keys: {e}", "WARNING")

                # Альтернативный метод: через set_text (если доступен)
                try:
                    if hasattr(text_field, 'set_text'):
                        text_field.set_text(value)
                        time.sleep(SMALL_DELAY)
                    else:
                        raise Exception("set_text не доступен")
                except:
                    # Еще один альтернативный метод: через клик и вставку
                    try:
                        # Копируем значение в буфер обмена (Windows)
                        import subprocess
                        subprocess.run(['powershell', '-command', f'Set-Clipboard -Value "{value}"'])
                        time.sleep(SMALL_DELAY)
                        # Вставляем из буфера
                        text_field.type_keys("^v")
                        time.sleep(SMALL_DELAY)
                    except Exception as e2:
                        self.log_message(f"  ❌ Ошибка при вводе текста: {e2}", "ERROR")
                        return False

            # Нажимаем Tab для подтверждения ввода (опционально)
            try:
                text_field.type_keys("{TAB}")
                time.sleep(SMALL_DELAY)
            except:
                pass

            self.log_message(f"  ✅ Текст '{value}' введен", "SUCCESS")
            return True

        except Exception as e:
            self.log_message(f"  ❌ Ошибка при вводе текста: {e}", "ERROR")
            return False

    def set_text_main(self, key: str, value: str, timeout: int = TIMEOUT, clear_first: bool = True) -> bool:
        """
        Вводит текст в текстовое поле в главном окне по ключу из AUTO_IDS.

        Args:
            key: Ключ текстового поля в словаре AUTO_IDS
            value: Текст для ввода
            timeout: Время ожидания в секундах
            clear_first: Очистить поле перед вводом (по умолчанию True)

        Returns:
            True при успешном вводе текста, False при ошибке

        Пример:
            # Ввести текст в поле в главном окне
            helper.set_text_main("username_field", "admin")
        """
        if not self.main_window:
            self.log_message("❌ Главное окно не установлено", "ERROR")
            return False

        return self.set_text(self.main_window, key, value, timeout, clear_first)

    def get_text(self, window: Any, key: str, timeout: int = TIMEOUT) -> Optional[str]:
        """
        Получает текст из текстового поля по ключу из AUTO_IDS.

        Args:
            window: Объект окна из pywinauto
            key: Ключ текстового поля в словаре AUTO_IDS
            timeout: Время ожидания в секундах

        Returns:
            Текст из поля или None при ошибке

        Пример:
            # Получить текст из поля
            text = helper.get_text(window, "username_field")
            if text:
                print(f"Текст в поле: {text}")
        """
        auto_id = self.get_auto_id(key)
        if not auto_id:
            return None

        self.log_message(f"Получение текста из поля по ключу: '{key}'", "INFO")

        text_field = self.find_element_by_auto_id(window, auto_id, timeout)
        if not text_field:
            self.log_message(f"  ❌ Текстовое поле не найдено", "ERROR")
            return None

        try:
            # Пробуем получить текст через window_text()
            text = text_field.window_text()
            if text:
                self.log_message(f"  ✅ Получен текст: '{text}'", "SUCCESS")
                return text

            # Альтернативный метод: через get_text (если доступен)
            if hasattr(text_field, 'get_text'):
                try:
                    text = text_field.get_text()
                    if text:
                        self.log_message(f"  ✅ Получен текст: '{text}'", "SUCCESS")
                        return text
                except:
                    pass

            # Альтернативный метод: через element_info
            if hasattr(text_field, 'element_info'):
                try:
                    if hasattr(text_field.element_info, 'name'):
                        text = text_field.element_info.name
                        if text:
                            self.log_message(f"  ✅ Получен текст: '{text}'", "SUCCESS")
                            return text
                except:
                    pass

            self.log_message(f"  ❌ Не удалось получить текст из поля", "ERROR")
            return None

        except Exception as e:
            self.log_message(f"  ❌ Ошибка при получении текста: {e}", "ERROR")
            return None

    def get_text_main(self, key: str, timeout: int = TIMEOUT) -> Optional[str]:
        """
        Получает текст из текстового поля в главном окне по ключу из AUTO_IDS.

        Args:
            key: Ключ текстового поля в словаре AUTO_IDS
            timeout: Время ожидания в секундах

        Returns:
            Текст из поля или None при ошибке
        """
        if not self.main_window:
            self.log_message("❌ Главное окно не установлено", "ERROR")
            return None

        return self.get_text(self.main_window, key, timeout)

    def clear_text(self, window: Any, key: str, timeout: int = TIMEOUT) -> bool:
        """
        Очищает текстовое поле по ключу из AUTO_IDS.

        Args:
            window: Объект окна из pywinauto
            key: Ключ текстового поля в словаре AUTO_IDS
            timeout: Время ожидания в секундах

        Returns:
            True при успешной очистке, False при ошибке

        Пример:
            # Очистить поле
            helper.clear_text(window, "username_field")
        """
        return self.set_text(window, key, "", timeout, clear_first=True)

    def clear_text_main(self, key: str, timeout: int = TIMEOUT) -> bool:
        """
        Очищает текстовое поле в главном окне по ключу из AUTO_IDS.

        Args:
            key: Ключ текстового поля в словаре AUTO_IDS
            timeout: Время ожидания в секундах

        Returns:
            True при успешной очистке, False при ошибке
        """
        if not self.main_window:
            self.log_message("❌ Главное окно не установлено", "ERROR")
            return False

        return self.clear_text(self.main_window, key, timeout)

# =========================================================================
# НОВЫЕ МЕТОДЫ ДЛЯ РАБОТЫ СО СКРИНШОТАМИ И ЦВЕТОМ
# =========================================================================

    def take_screenshot(self, window: Any, save_path: str, mask_areas: Optional[List[dict]] = None,
                        mask_enabled: bool = True) -> bool:
        """
        Делает скриншот указанного окна с возможностью маскирования областей.

        Args:
            window: Объект окна из pywinauto
            save_path: Путь для сохранения скриншота
            mask_areas: Список областей для маскирования (каждая область - словарь с ключами left, top, right, bottom)
            mask_enabled: Включить маскирование (по умолчанию True)

        Returns:
            True при успешном сохранении скриншота, False при ошибке

        Пример:
            mask_areas = [
                {"left": 1733, "top": 127, "right": 1914, "bottom": 193},
                {"left": 263, "top": 838, "right": 1924, "bottom": 984}
            ]
            helper.take_screenshot(window, "screenshot.png", mask_areas)
        """
        self.log_message(f"Создание скриншота: {save_path}", "INFO")

        try:
            rect = window.rectangle()
            left = rect.left
            top = rect.top
            right = rect.right
            bottom = rect.bottom

            self.log_message(f"  Размер окна: {right - left}x{bottom - top}", "INFO")

            screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))

            # Применяем маскирование, если включено и есть области
            if mask_enabled and mask_areas:
                screenshot = self._apply_masks(screenshot, mask_areas)
                self.log_message(f"  Маскирование применено к {len(mask_areas)} областям", "INFO")

            screenshot.save(save_path)
            self.log_message(f"  ✅ Скриншот сохранён: {save_path}", "SUCCESS")
            return True

        except Exception as e:
            self.log_message(f"  ❌ Ошибка при создании скриншота: {e}", "ERROR")
            return False

    def _apply_masks(self, image: Image.Image, mask_areas: List[dict]) -> Image.Image:
        """
        Закрашивает указанные области белым цветом.

        Args:
            image: Изображение PIL
            mask_areas: Список областей для маскирования

        Returns:
            Изображение с замаскированными областями
        """
        width, height = image.size
        masked = image.copy()
        draw = ImageDraw.Draw(masked)

        for area in mask_areas:
            mask_area = (
                area.get("left", 0),
                area.get("top", 0),
                area.get("right", width),
                area.get("bottom", height)
            )
            draw.rectangle(mask_area, fill="white")

        return masked

    def compare_images(self, expected_path: str, actual_path: str, diff_path: str,
                       mask_areas: Optional[List[dict]] = None,
                       mask_enabled: bool = True,
                       diff_threshold_percent: float = 0.5,
                       min_cluster_pixels: int = 50) -> Tuple[bool, float]:
        """
        Сравнивает два изображения с маскированием областей.

        Args:
            expected_path: Путь к эталонному изображению
            actual_path: Путь к фактическому изображению
            diff_path: Путь для сохранения изображения с отличиями
            mask_areas: Список областей для маскирования
            mask_enabled: Включить маскирование (по умолчанию True)
            diff_threshold_percent: Минимальный процент отличий для считания изображений разными
            min_cluster_pixels: Минимальное количество пикселей в кластере отличий

        Returns:
            Кортеж (has_diff, diff_percent): есть ли значимые отличия и процент отличий

        Пример:
            has_diff, percent = helper.compare_images("expected.png", "actual.png", "diff.png")
        """
        self.log_message(f"Сравнение изображений...", "INFO")

        try:
            expected = Image.open(expected_path)
            actual = Image.open(actual_path)

            if expected.size != actual.size:
                self.log_message(f"  Размеры изображений не совпадают: {expected.size} vs {actual.size}", "WARNING")
                actual = actual.resize(expected.size)

            # Применяем маскирование к ОБОИМ изображениям
            if mask_enabled and mask_areas:
                expected_masked = self._apply_masks(expected, mask_areas)
                actual_masked = self._apply_masks(actual, mask_areas)
            else:
                expected_masked = expected
                actual_masked = actual

            diff = ImageChops.difference(expected_masked, actual_masked)

            bbox = diff.getbbox()
            if not bbox:
                self.log_message(f"  ✅ Изображения идентичны", "SUCCESS")
                return False, 0.0

            # Используем numpy для подсчёта отличий
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

            self.log_message(f"  Процент отличий: {diff_percent:.4f}%", "INFO")

            if diff_percent < diff_threshold_percent:
                self.log_message(f"  ✅ Отличия меньше порога ({diff_threshold_percent}%), считаем идентичными", "SUCCESS")
                return False, diff_percent

            self.log_message(f"  ⚠️ Найдены значимые отличия: {diff_percent:.2f}%", "WARNING")

            # Создаём изображение с выделенными отличиями
            result = actual.copy()
            draw = ImageDraw.Draw(result)

            clusters = self._find_diff_clusters(diff, min_cluster_pixels)

            if clusters:
                for i, cluster_bbox in enumerate(clusters, 1):
                    draw.rectangle(cluster_bbox, outline="red", width=3)
                    center_x = (cluster_bbox[0] + cluster_bbox[2]) // 2
                    center_y = (cluster_bbox[1] + cluster_bbox[3]) // 2
                    draw.text((center_x + 5, center_y - 10), f"#{i}", fill="red")

                self.log_message(f"  Обведено кластеров отличий: {len(clusters)}", "INFO")
            else:
                draw.rectangle(bbox, outline="red", width=3)
                self.log_message(f"  ⚠️ Кластеры не найдены, обведён общий bbox", "WARNING")

            result.save(diff_path)
            self.log_message(f"  ✅ Изображение с отличиями сохранено: {diff_path}", "SUCCESS")

            return True, diff_percent

        except Exception as e:
            self.log_message(f"  ❌ Ошибка при сравнении изображений: {e}", "ERROR")
            return False, -1.0

    def _find_diff_clusters(self, diff_image: Image.Image, min_pixels: int = 50) -> List[Tuple[int, int, int, int]]:
        """
        Находит кластеры отличающихся пикселей.

        Args:
            diff_image: Изображение разницы
            min_pixels: Минимальное количество пикселей в кластере

        Returns:
            Список кортежей (left, top, right, bottom) для каждого кластера
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

    def get_color(self, key: str, timeout: int = TIMEOUT) -> Optional[str]:
        """
        Получает цвет элемента по ключу из AUTO_IDS.
        Определяет область элемента, делает скриншот, получает цвет пикселя с небольшим отступом от края.
        Ищет цвет в словаре COLORS и возвращает соответствующее значение.

        Args:
            key: Ключ элемента в словаре AUTO_IDS
            timeout: Время ожидания в секундах

        Returns:
            Название цвета из словаря COLORS или None при ошибке

        Пример:
            # Получить цвет индикатора статуса
            color_name = helper.get_color("status_indicator")
            if color_name:
                print(f"Цвет индикатора: {color_name}")
        """
        self.log_message(f"Получение цвета элемента по ключу: '{key}'", "INFO")

        # Проверяем, что импортирован словарь COLORS
        try:
            from core.config_auto_ids import COLORS
        except ImportError:
            self.log_message("❌ Словарь COLORS не найден в core.config_auto_ids", "ERROR")
            return None

        # Получаем AutomationId по ключу
        auto_id = self.get_auto_id(key)
        if not auto_id:
            return None

        # Проверяем, что main_window существует
        if not self.main_window:
            self.log_message("❌ Главное окно не установлено", "ERROR")
            return None

        # Находим элемент
        element = self.find_element_by_auto_id(self.main_window, auto_id, timeout)
        if not element:
            self.log_message(f"❌ Элемент не найден по ключу '{key}'", "ERROR")
            return None

        try:
            # Получаем координаты элемента
            rect = element.rectangle()

            # Вычисляем область для получения цвета (с отступом от края)
            # Отступ составляет 5% от ширины и высоты, но не менее 2 пикселей
            padding_x = max(2, int(rect.width() * 0.05))
            padding_y = max(2, int(rect.height() * 0.05))

            # Координаты точки для снятия цвета (левый верхний угол с отступом)
            x = rect.left + padding_x
            y = rect.top + padding_y

            self.log_message(f"  Координаты элемента: ({rect.left}, {rect.top}) - ({rect.right}, {rect.bottom})",
                             "INFO")
            self.log_message(f"  Точка для снятия цвета: ({x}, {y})", "INFO")
            self.log_message(f"  Размер элемента: {rect.width()}x{rect.height()}", "INFO")

            # Получаем скриншот области элемента
            from PIL import ImageGrab
            import pyautogui

            # Делаем скриншот области элемента
            screenshot = pyautogui.screenshot(region=(rect.left, rect.top, rect.width(), rect.height()))

            # Получаем цвет пикселя с отступом
            # Координаты внутри скриншота (относительные)
            pixel_x = padding_x
            pixel_y = padding_y

            # Получаем RGB значения
            rgb = screenshot.getpixel((pixel_x, pixel_y))

            # Конвертируем RGB в HEX
            hex_color = '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])

            self.log_message(f"  Получен RGB цвет: {rgb}", "INFO")
            self.log_message(f"  HEX цвет: {hex_color}", "INFO")

            # Ищем цвет в словаре COLORS (поддержка списка значений)
            for color_name, color_values in COLORS.items():
                # Если значение НЕ является списком - преобразуем в список для единообразия
                if not isinstance(color_values, list):
                    color_values = [color_values]

                # Проверяем каждый вариант цвета в списке
                for color_value in color_values:
                    # Проверка HEX строк
                    if isinstance(color_value, str):
                        # Сравниваем HEX значения (игнорируем регистр)
                        if color_value.lower() == hex_color.lower():
                            self.log_message(f"  ✅ Найден цвет: '{color_name}' = {color_value}", "SUCCESS")
                            return color_name

                        # Пробуем сравнить без символа #
                        if color_value.lower().replace('#', '') == hex_color.lower().replace('#', ''):
                            self.log_message(f"  ✅ Найден цвет: '{color_name}' = {color_value}", "SUCCESS")
                            return color_name

                    # Проверка RGB кортежей
                    elif isinstance(color_value, tuple) and len(color_value) == 3:
                        if color_value == rgb:
                            self.log_message(f"  ✅ Найден цвет: '{color_name}' = {color_value}", "SUCCESS")
                            return color_name

            # Если цвет не найден в словаре
            self.log_message(f"  ❌ Цвет {hex_color} не найден в словаре COLORS", "WARNING")
            return None

        except ImportError as e:
            self.log_message(f"❌ Ошибка импорта необходимых библиотек: {e}", "ERROR")
            self.log_message("  Убедитесь, что установлены pillow и pyautogui", "ERROR")
            self.log_message("  pip install pillow pyautogui", "INFO")
            return None
        except Exception as e:
            self.log_message(f"  ❌ Ошибка при получении цвета: {e}", "ERROR")
            return None

    def get_color_from_point(self, x: int, y: int) -> Optional[str]:
        """
        Получает цвет пикселя по абсолютным координатам и ищет его в словаре COLORS.

        Args:
            x: Абсолютная координата X на экране
            y: Абсолютная координата Y на экране

        Returns:
            Название цвета из словаря COLORS или None при ошибке

        Пример:
            # Получить цвет по координатам
            color_name = helper.get_color_from_point(100, 200)
        """
        self.log_message(f"Получение цвета по координатам: ({x}, {y})", "INFO")

        try:
            from core.config_auto_ids import COLORS
            import pyautogui

            # Получаем цвет пикселя
            rgb = pyautogui.pixel(x, y)

            # Конвертируем RGB в HEX
            hex_color = '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])

            self.log_message(f"  RGB цвет: {rgb}", "INFO")
            self.log_message(f"  HEX цвет: {hex_color}", "INFO")

            # Ищем цвет в словаре COLORS (поддержка списка значений)
            for color_name, color_values in COLORS.items():
                # Если значение НЕ является списком - преобразуем в список для единообразия
                if not isinstance(color_values, list):
                    color_values = [color_values]

                # Проверяем каждый вариант цвета в списке
                for color_value in color_values:
                    # Проверка HEX строк
                    if isinstance(color_value, str):
                        # Сравниваем HEX значения (игнорируем регистр)
                        if color_value.lower() == hex_color.lower():
                            self.log_message(f"  ✅ Найден цвет: '{color_name}' = {color_value}", "SUCCESS")
                            return color_name

                        # Пробуем сравнить без символа #
                        if color_value.lower().replace('#', '') == hex_color.lower().replace('#', ''):
                            self.log_message(f"  ✅ Найден цвет: '{color_name}' = {color_value}", "SUCCESS")
                            return color_name

                    # Проверка RGB кортежей
                    elif isinstance(color_value, tuple) and len(color_value) == 3:
                        if color_value == rgb:
                            self.log_message(f"  ✅ Найден цвет: '{color_name}' = {color_value}", "SUCCESS")
                            return color_name

            self.log_message(f"  ❌ Цвет {hex_color} не найден в словаре COLORS", "WARNING")
            return None

        except ImportError as e:
            self.log_message(f"❌ Ошибка импорта: {e}", "ERROR")
            return None
        except Exception as e:
            self.log_message(f"  ❌ Ошибка при получении цвета: {e}", "ERROR")
            return None

    def get_element_color_center(self, key: str, timeout: int = TIMEOUT) -> Optional[str]:
        """
        Получает цвет элемента по ключу из AUTO_IDS (цвет из центра элемента).

        Args:
            key: Ключ элемента в словаре AUTO_IDS
            timeout: Время ожидания в секундах

        Returns:
            Название цвета из словаря COLORS или None при ошибке
        """
        self.log_message(f"Получение цвета из центра элемента по ключу: '{key}'", "INFO")

        try:
            from core.config_auto_ids import COLORS

            auto_id = self.get_auto_id(key)
            if not auto_id:
                return None

            if not self.main_window:
                self.log_message("❌ Главное окно не установлено", "ERROR")
                return None

            element = self.find_element_by_auto_id(self.main_window, auto_id, timeout)
            if not element:
                self.log_message(f"❌ Элемент не найден по ключу '{key}'", "ERROR")
                return None

            # Получаем координаты центра элемента
            rect = element.rectangle()
            center_x = rect.left + rect.width() // 2
            center_y = rect.top + rect.height() // 2

            self.log_message(f"  Центр элемента: ({center_x}, {center_y})", "INFO")

            # Используем get_color_from_point
            return self.get_color_from_point(center_x, center_y)

        except Exception as e:
            self.log_message(f"  ❌ Ошибка при получении цвета: {e}", "ERROR")
            return None

    def get_color_by_percentage(self, key: str, x_percent: float = 10, y_percent: float = 10, timeout: int = TIMEOUT) -> \
    Optional[str]:
        """
        Получает цвет элемента по ключу из AUTO_IDS с указанием процента отступа от края.

        Args:
            key: Ключ элемента в словаре AUTO_IDS
            x_percent: Процент отступа по горизонтали от левого края (0-100)
            y_percent: Процент отступа по вертикали от верхнего края (0-100)
            timeout: Время ожидания в секундах

        Returns:
            Название цвета из словаря COLORS или None при ошибке

        Пример:
            # Получить цвет в точке 20% от левого и 30% от верхнего края
            color_name = helper.get_color_by_percentage("status_indicator", 20, 30)
        """
        self.log_message(f"Получение цвета элемента по ключу: '{key}' с отступом {x_percent}% x {y_percent}%", "INFO")

        try:
            from core.config_auto_ids import COLORS

            auto_id = self.get_auto_id(key)
            if not auto_id:
                return None

            if not self.main_window:
                self.log_message("❌ Главное окно не установлено", "ERROR")
                return None

            element = self.find_element_by_auto_id(self.main_window, auto_id, timeout)
            if not element:
                self.log_message(f"❌ Элемент не найден по ключу '{key}'", "ERROR")
                return None

            # Получаем координаты элемента
            rect = element.rectangle()

            # Вычисляем отступ в пикселях
            padding_x = int(rect.width() * x_percent / 100)
            padding_y = int(rect.height() * y_percent / 100)

            # Координаты точки
            x = rect.left + padding_x
            y = rect.top + padding_y

            self.log_message(f"  Точка для снятия цвета: ({x}, {y})", "INFO")

            # Используем get_color_from_point
            return self.get_color_from_point(x, y)

        except Exception as e:
            self.log_message(f"  ❌ Ошибка при получении цвета: {e}", "ERROR")
            return None

    def get_color_from_element(self, element: Any, timeout: int = TIMEOUT) -> Optional[str]:
        """
        Получает цвет из указанного элемента по координатам.
        Определяет область элемента, делает скриншот, получает цвет пикселя с небольшим отступом от края.
        Ищет цвет в словаре COLORS и возвращает соответствующее значение.

        Args:
            element: Объект элемента из pywinauto
            timeout: Время ожидания в секундах

        Returns:
            Название цвета из словаря COLORS или None при ошибке

        Пример:
            # Получить цвет элемента
            color_name = helper.get_color_from_element(element)
            if color_name:
                print(f"Цвет элемента: {color_name}")
        """
        self.log_message(f"Получение цвета из элемента", "INFO")

        # Проверяем, что импортирован словарь COLORS
        try:
            from core.config_auto_ids import COLORS
        except ImportError:
            self.log_message("❌ Словарь COLORS не найден в core.config_auto_ids", "ERROR")
            return None

        if not element:
            self.log_message("❌ Элемент не передан", "ERROR")
            return None

        try:
            # Получаем координаты элемента
            rect = element.rectangle()

            # Вычисляем координаты точки для снятия цвета:
            # По оси X - ровно половина области (50%)
            # По оси Y - 1/3 области (33.33%)
            x = rect.left + int(rect.width() * 0.5)  # 50% от ширины
            y = rect.top + int(rect.height() * 0.333)  # 1/3 от высоты (33.33%)

            self.log_message(f"  Координаты элемента: ({rect.left}, {rect.top}) - ({rect.right}, {rect.bottom})",
                             "INFO")
            self.log_message(f"  Размер элемента: {rect.width()}x{rect.height()}", "INFO")
            self.log_message(f"  Точка для снятия цвета (50%, 33.3%): ({x}, {y})", "INFO")

            # Получаем скриншот области элемента


            # Делаем скриншот области элемента
            screenshot = pyautogui.screenshot(region=(rect.left, rect.top, rect.width(), rect.height()))

            # Получаем цвет пикселя с отступом
            # Координаты внутри скриншота (относительные)
            pixel_x = int(rect.width() * 0.5)  # 50% от ширины
            pixel_y = int(rect.height() * 0.333)  # 1/3 от высоты

            # Получаем RGB значения
            rgb = screenshot.getpixel((pixel_x, pixel_y))

            # Конвертируем RGB в HEX
            hex_color = '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])

            self.log_message(f"  Получен RGB цвет: {rgb}", "INFO")
            self.log_message(f"  HEX цвет: {hex_color}", "INFO")

            # Ищем цвет в словаре COLORS (поддержка списка значений)
            for color_name, color_values in COLORS.items():
                # Если значение НЕ является списком - преобразуем в список для единообразия
                if not isinstance(color_values, list):
                    color_values = [color_values]

                # Проверяем каждый вариант цвета в списке
                for color_value in color_values:
                    # Проверка HEX строк
                    if isinstance(color_value, str):
                        # Сравниваем HEX значения (игнорируем регистр)
                        if color_value.lower() == hex_color.lower():
                            self.log_message(f"  ✅ Найден цвет: '{color_name}' = {color_value}", "SUCCESS")
                            return color_name

                        # Пробуем сравнить без символа #
                        if color_value.lower().replace('#', '') == hex_color.lower().replace('#', ''):
                            self.log_message(f"  ✅ Найден цвет: '{color_name}' = {color_value}", "SUCCESS")
                            return color_name

                    # Проверка RGB кортежей
                    elif isinstance(color_value, tuple) and len(color_value) == 3:
                        if color_value == rgb:
                            self.log_message(f"  ✅ Найден цвет: '{color_name}' = {color_value}", "SUCCESS")
                            return color_name

            # Если цвет не найден в словаре
            self.log_message(f"  ❌ Цвет {hex_color} не найден в словаре COLORS", "WARNING")
            return None

        except ImportError as e:
            self.log_message(f"❌ Ошибка импорта необходимых библиотек: {e}", "ERROR")
            self.log_message("  Убедитесь, что установлены pillow и pyautogui", "ERROR")
            self.log_message("  pip install pillow pyautogui", "INFO")
            return None
        except Exception as e:
            self.log_message(f"  ❌ Ошибка при получении цвета: {e}", "ERROR")
            return None

# =========================================================================
# НОВЫЕ МЕТОДЫ ДЛЯ РАБОТЫ С ПАНЕЛЯМИ
# =========================================================================

    def find_panel_with_children(self, window: Any, panel_key: str,
                                  child_conditions: List[Tuple[str, str]],
                                  timeout: int = TIMEOUT) -> Optional[Any]:
        """
        Находит панель по ключу из AUTO_IDS, у которой есть дочерние элементы с указанными условиями.

        Args:
            window: Объект окна из pywinauto
            panel_key: Ключ панели в словаре AUTO_IDS
            child_conditions: Список кортежей (ключ, ожидаемый_текст) для проверки дочерних элементов
            timeout: Время ожидания в секундах

        Returns:
            Найденная панель или None при ошибке

        Пример:
            child_conditions = [
                ("lbl_radio_name", "Intercom"),
                ("cbx_recipients", "All Call")
            ]
            panel = helper.find_panel_with_children(window, "panel_voice_ip", child_conditions)
        """
        self.log_message(f"Поиск панели по ключу: '{panel_key}'", "INFO")

        # Получаем AutomationId панели
        panel_auto_id = self.get_auto_id(panel_key)
        if not panel_auto_id:
            return None

        panel = self.find_element_by_auto_id(window, panel_auto_id, timeout)
        if not panel:
            self.log_message(f"  ❌ Панель '{panel_key}' не найдена", "ERROR")
            return None

        self.log_message(f"  ✅ Панель найдена, проверяем дочерние элементы...", "SUCCESS")

        children = panel.descendants()
        all_found = True

        for key, expected_name in child_conditions:
            found = False
            auto_id = self.get_auto_id(key)
            if not auto_id:
                all_found = False
                continue

            for child in children:
                try:
                    child_auto_id = child.element_info.automation_id if hasattr(child, 'element_info') else None
                    child_name = child.window_text() if hasattr(child, 'window_text') else ""
                    if child_auto_id == auto_id and child_name == expected_name:
                        self.log_message(f"    ✅ Найден дочерний элемент: '{key}' -> '{expected_name}'", "SUCCESS")
                        found = True
                        break
                except:
                    continue

            if not found:
                self.log_message(f"    ❌ Не найден дочерний элемент: '{key}' -> '{expected_name}'", "ERROR")
                all_found = False

        if all_found:
            self.log_message(f"  ✅ Все дочерние элементы найдены", "SUCCESS")
            return panel
        else:
            self.log_message(f"  ❌ Не все дочерние элементы найдены", "ERROR")
            return None

    def find_panel_with_children_main(self, panel_key: str,
                                       child_conditions: List[Tuple[str, str]],
                                       timeout: int = TIMEOUT) -> Optional[Any]:
        """
        Находит панель в главном окне по ключу из AUTO_IDS, у которой есть дочерние элементы.

        Args:
            panel_key: Ключ панели в словаре AUTO_IDS
            child_conditions: Список кортежей (ключ, ожидаемый_текст) для проверки дочерних элементов
            timeout: Время ожидания в секундах

        Returns:
            Найденная панель или None при ошибке
        """
        if not self.main_window:
            self.log_message("❌ Главное окно не установлено", "ERROR")
            return None

        return self.find_panel_with_children(self.main_window, panel_key, child_conditions, timeout)

# =========================================================================
# НОВЫЕ МЕТОДЫ ДЛЯ РАБОТЫ С ПРОЦЕССАМИ
# =========================================================================

    def get_process_count(self, process_name: str) -> Tuple[int, List[int]]:
        """
        Возвращает количество запущенных процессов с указанным именем и их PID.

        Args:
            process_name: Имя процесса (например, "TRBOnet.Console.exe")

        Returns:
            Кортеж (количество_процессов, список_PID)

        Пример:
            count, pids = helper.get_process_count("TRBOnet.Console.exe")
            print(f"Найдено процессов: {count}, PID: {pids}")
        """
        self.log_message(f"Поиск процессов с именем: '{process_name}'", "INFO")

        pids = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] == process_name:
                    pids.append(proc.info['pid'])
            except:
                pass

        count = len(pids)
        self.log_message(f"  Найдено процессов: {count}", "INFO")
        if count > 0:
            self.log_message(f"  PID: {pids}", "INFO")

        return count, pids

    def wait_for_process(self, process_name: str, timeout: int = TIMEOUT,
                         check_interval: float = 0.5) -> bool:
        """
        Ожидает появления процесса с указанным именем.

        Args:
            process_name: Имя процесса
            timeout: Время ожидания в секундах
            check_interval: Интервал проверки в секундах

        Returns:
            True если процесс появился, False при превышении таймаута
        """
        self.log_message(f"Ожидание процесса: '{process_name}'...", "INFO")

        start_time = time.time()
        while time.time() - start_time < timeout:
            count, _ = self.get_process_count(process_name)
            if count > 0:
                self.log_message(f"  ✅ Процесс '{process_name}' найден", "SUCCESS")
                return True
            time.sleep(check_interval)

        self.log_message(f"  ❌ Процесс '{process_name}' не появился за {timeout} секунд", "ERROR")
        return False

    def wait_for_process_exit(self, process_name: str, timeout: int = TIMEOUT,
                              check_interval: float = 0.5) -> bool:
        """
        Ожидает завершения процесса с указанным именем.

        Args:
            process_name: Имя процесса
            timeout: Время ожидания в секундах
            check_interval: Интервал проверки в секундах

        Returns:
            True если процесс завершился, False при превышении таймаута
        """
        self.log_message(f"Ожидание завершения процесса: '{process_name}'...", "INFO")

        start_time = time.time()
        while time.time() - start_time < timeout:
            count, _ = self.get_process_count(process_name)
            if count == 0:
                self.log_message(f"  ✅ Процесс '{process_name}' завершился", "SUCCESS")
                return True
            time.sleep(check_interval)

        self.log_message(f"  ❌ Процесс '{process_name}' не завершился за {timeout} секунд", "ERROR")
        return False

    def get_main_window_pid(self) -> Optional[int]:
        """
        Получает PID процесса главного окна.

        Returns:
            PID процесса или None при ошибке
        """
        if not self.main_window:
            self.log_message("❌ Главное окно не установлено", "ERROR")
            return None

        try:
            pid = self.main_window.process_id()
            self.log_message(f"  PID главного окна: {pid}", "INFO")
            return pid
        except Exception as e:
            self.log_message(f"  ❌ Ошибка при получении PID: {e}", "ERROR")
            return None

# =========================================================================
# НОВЫЕ МЕТОДЫ ДЛЯ РАБОТЫ С ОКНАМИ И PTT
# =========================================================================

    def wait_for_window_ready(self, window: Any, key_elements: List[str], timeout: int = TIMEOUT) -> bool:
        """
        Ожидает, пока окно полностью загрузится.
        Проверяет наличие ключевых элементов по AutomationId.

        Args:
            window: Объект окна из pywinauto
            key_elements: Список AutomationId для проверки
            timeout: Время ожидания в секундах

        Returns:
            True если все элементы найдены, False при превышении таймаута

        Пример:
            helper.wait_for_window_ready(window, ["ConsoleTypeCb", "btnConnect"])
        """
        self.log_message(f"  Ожидание полной загрузки окна...", "INFO")

        start_time = time.time()

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
                                    break
                        except:
                            continue

                if found_count == len(key_elements):
                    self.log_message(f"  ✅ Окно полностью загружено (найдено {found_count} элементов)", "SUCCESS")
                    return True

            except Exception as e:
                self.log_message(f"  Ошибка при проверке загрузки: {e}", "WARNING")

            time.sleep(0.3)

        self.log_message(f"  ❌ Окно не загрузилось за {timeout} секунд", "ERROR")
        return False

    def wait_for_window_ready_by_text(self, window: Any, text: str, timeout: int = TIMEOUT) -> bool:
        """
        Ожидает, пока окно полностью загрузится.
        Проверяет наличие элемента с указанным текстом.

        Args:
            window: Объект окна из pywinauto
            text: Текст для поиска (например, "PTT")
            timeout: Время ожидания в секундах

        Returns:
            True если элемент найден, False при превышении таймаута
        """
        self.log_message(f"  Ожидание появления текста '{text}'...", "INFO")

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                all_elements = window.descendants()

                for elem in all_elements:
                    try:
                        elem_name = elem.window_text() if hasattr(elem, 'window_text') else ""
                        if elem_name == text:
                            self.log_message(f"  ✅ Элемент с текстом '{text}' найден", "SUCCESS")
                            return True
                    except:
                        continue

            except Exception as e:
                self.log_message(f"  Ошибка при проверке загрузки: {e}", "WARNING")

            time.sleep(0.3)

        self.log_message(f"  ❌ Элемент с текстом '{text}' не найден за {timeout} секунд", "ERROR")
        return False

    def find_elements_by_text(self, window: Any, text: str, timeout: int = TIMEOUT) -> List[Any]:
        """
        Находит все элементы с указанным текстом в окне.

        Args:
            window: Объект окна из pywinauto
            text: Текст для поиска
            timeout: Время ожидания в секундах

        Returns:
            Список найденных элементов
        """
        self.log_message(f"  Поиск элементов по тексту: '{text}'", "INFO")

        elements = []
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                all_elements = window.descendants()
                for elem in all_elements:
                    try:
                        elem_name = elem.window_text() if hasattr(elem, 'window_text') else ""
                        if elem_name == text:
                            elements.append(elem)
                    except:
                        continue

                if elements:
                    self.log_message(f"  ✅ Найдено {len(elements)} элементов с текстом '{text}'", "SUCCESS")
                    return elements

            except Exception as e:
                self.log_message(f"  Ошибка при поиске: {e}", "WARNING")

            time.sleep(0.3)

        self.log_message(f"  ❌ Элементы с текстом '{text}' не найдены", "ERROR")
        return elements

    def find_active_button_by_text(self, window: Any, text: str, timeout: int = TIMEOUT) -> Optional[Any]:
        """
        Находит активную (включенную) кнопку с указанным текстом.

        Args:
            window: Объект окна из pywinauto
            text: Текст на кнопке
            timeout: Время ожидания в секундах

        Returns:
            Найденная кнопка или None при ошибке
        """
        self.log_message(f"  Поиск активной кнопки с текстом: '{text}'", "INFO")

        start_time = time.time()

        while time.time() - start_time < timeout:
            all_elements = window.descendants()
            buttons = []

            for elem in all_elements:
                try:
                    elem_name = elem.window_text() if hasattr(elem, 'window_text') else ""
                    elem_type = elem.element_info.control_type if hasattr(elem, 'element_info') else ""

                    if elem_name == text and "Button" in elem_type:
                        buttons.append(elem)
                except:
                    continue

            if not buttons:
                self.log_message(f"  ⚠️ Кнопки с текстом '{text}' не найдены", "WARNING")
                time.sleep(0.5)
                continue

            self.log_message(f"  Найдено кнопок с текстом '{text}': {len(buttons)}", "INFO")

            for idx, btn in enumerate(buttons, 1):
                try:
                    is_enabled = btn.is_enabled() if hasattr(btn, 'is_enabled') else False
                    if is_enabled:
                        self.log_message(f"  ✅ Найдена активная кнопка с текстом '{text}' #{idx}", "SUCCESS")
                        return btn
                    else:
                        self.log_message(f"  ℹ️ Кнопка #{idx} с текстом '{text}' неактивна", "DEBUG")
                except:
                    continue

            time.sleep(0.5)

        self.log_message(f"  ❌ Активная кнопка с текстом '{text}' не найдена за {timeout} секунд", "ERROR")
        return None

