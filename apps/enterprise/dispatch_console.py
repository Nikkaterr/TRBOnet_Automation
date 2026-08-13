"""
dispatch_console.py - Классы для автоматизации работы с Dispatch Console

Назначение: Содержит классы ConnectionManager и EnterpriseConsole для
автоматизации работы с приложением TRBOnet Dispatch Console.
Использует apps.apps_helpers.py как библиотеку утилит.
"""

import time
from typing import Optional, List, Tuple
from pywinauto.application import Application

from apps.apps_helpers import AppsHelper
from core_desktop.config import TIMEOUT, SMALL_DELAY, LARGE_DELAY, CONSOLE_EXE_PATH, WINDOW_CONSOLE_PATTERN, \
    WINDOW_CONNECT_MANAGER_ENTERPRISE_PATTERN
from core_desktop.config_auto_ids import PROCESS_NAMES


class ConnectionManager:
    """
    Класс для автоматизации работы с окном подключения к серверу TRBOnet.

    Атрибуты:
        helper: Экземпляр AppsHelper
        window: Окно подключения
        is_connected: Флаг подключения к серверу
    """

    def __init__(self, exe_path: Optional[str] = None,
                 window_title: Optional[str] = None,
                 timeout: Optional[int] = None):
        """
        Инициализация ConnectionManager.

        Args:
            helper: Экземпляр AppsHelper для работы с UI
        """
        self.helper = AppsHelper()
        self.exe_path = exe_path or CONSOLE_EXE_PATH
        self.window = None
        self.is_connected = False

    def open(self, timeout: int = TIMEOUT) -> bool:
        """
        Открывает окно подключения к серверу.

        Returns:
            True при успешном открытии окна, False при ошибке
        """
        self.helper.log_message("Открытие окна подключения к серверу", "INFO")

        app = self.helper.launch_app(self.exe_path)
        if app is None:
            self.helper.log_message("Не удалось запустить приложение", "ERROR")
            return False

        self.window = self.helper.find_window(WINDOW_CONNECT_MANAGER_ENTERPRISE_PATTERN, timeout)
        if not self.window:
            self.helper.log_message("❌ Окно подключения не найдено", "ERROR")
            return False

        self.helper.log_message("✅ Окно подключения открыто", "SUCCESS")
        return True

    def get_state_cm_window(self, timeout: Optional[int] = None) -> bool:
        """
        Проверяет, открыто ли окно Connection Manager.

        Args:
            timeout: Время ожидания появления окна в секундах (если None, используется TIMEOUT из конфига)

        Returns:
            True если окно открыто, False в противном случае
        """
        # Если timeout не указан, используем значение из конфига
        if timeout is None:
            timeout = TIMEOUT

        self.helper.log_message(f"Проверка состояния окна Connection Manager (таймаут: {timeout}с)", "INFO")

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # Ищем окно по паттерну из конфига
                desktop = self.helper.desktop
                windows = desktop.windows(title_re=WINDOW_CONNECT_MANAGER_ENTERPRISE_PATTERN)

                if windows:
                    # Окно найдено, обновляем ссылку
                    self.window = windows[0]

                    # Проверяем, существует ли окно и видимо ли оно
                    try:
                        if self.window.exists() and self.window.is_visible():
                            self.helper.log_message("✅ Окно Connection Manager открыто", "SUCCESS")
                            return True
                        else:
                            self.helper.log_message("⚠️ Окно Connection Manager закрыто или не видимо", "WARNING")
                            time.sleep(0.5)
                            continue
                    except:
                        # Если методы exists/is_visible недоступны, проверяем через window_text
                        try:
                            text = self.window.window_text()
                            if text and "Connect" in text:
                                self.helper.log_message("✅ Окно Connection Manager открыто", "SUCCESS")
                                return True
                        except:
                            pass
                        # Если окно найдено - считаем его открытым
                        self.helper.log_message("✅ Окно Connection Manager открыто", "SUCCESS")
                        return True

                # Окно не найдено, ждём
                remaining = timeout - (time.time() - start_time)
                if remaining > 0:
                    self.helper.log_message(f"  Ожидание окна... (осталось {remaining:.1f}с)", "INFO")
                    time.sleep(0.5)
                else:
                    break

            except Exception as e:
                self.helper.log_message(f"  Ошибка при проверке состояния окна: {e}", "WARNING")
                time.sleep(0.5)

        # Если вышли из цикла, значит окно не появилось за отведённое время
        self.helper.log_message(f"⚠️ Окно Connection Manager не найдено за {timeout} секунд", "WARNING")
        self.window = None
        return False

    def set_address(self, address: str, timeout: int = TIMEOUT) -> bool:
        """
        Устанавливает адрес сервера в поле ввода.

        Args:
            address: Адрес сервера
            timeout: Время ожидания в секундах

        Returns:
            True при успешной установке, False при ошибке
        """
        self.helper.log_message(f"Установка адреса сервера: '{address}'", "INFO")

        if not self.window:
            self.helper.log_message("❌ Окно не инициализировано", "ERROR")
            return False

        return self.helper.set_text(self.window, "dd_address", address, timeout)

    def set_port(self, port: str, timeout: int = TIMEOUT) -> bool:
        """
        Устанавливает порт сервера в поле ввода.

        Args:
            port: Номер порта
            timeout: Время ожидания в секундах

        Returns:
            True при успешной установке, False при ошибке
        """
        self.helper.log_message(f"Установка порта: '{port}'", "INFO")

        if not self.window:
            self.helper.log_message("❌ Окно не инициализировано", "ERROR")
            return False

        return self.helper.set_text(self.window, "field_port", port, timeout)

    def set_method(self, method: str, timeout: int = TIMEOUT) -> bool:
        """
        Устанавливает метод авторизации в ComboBox.

        Args:
            method: Метод авторизации
            timeout: Время ожидания в секундах

        Returns:
            True при успешной установке, False при ошибке
        """
        self.helper.log_message(f"Установка метода авторизации: '{method}'", "INFO")

        if not self.window:
            self.helper.log_message("❌ Окно не инициализировано", "ERROR")
            return False

        return self.helper.set_combo_text_by_key(self.window, "dd_method", method, timeout)

    def set_username(self, username: str, timeout: int = TIMEOUT) -> bool:
        """
        Устанавливает имя пользователя в поле ввода.

        Args:
            username: Имя пользователя
            timeout: Время ожидания в секундах

        Returns:
            True при успешной установке, False при ошибке
        """
        self.helper.log_message(f"Установка имени пользователя: '{username}'", "INFO")

        if not self.window:
            self.helper.log_message("❌ Окно не инициализировано", "ERROR")
            return False

        return self.helper.set_text(self.window, "field_username", username, timeout)

    def set_password(self, password: str, timeout: int = TIMEOUT) -> bool:
        """
        Устанавливает пароль в поле ввода.

        Args:
            password: Пароль
            timeout: Время ожидания в секундах

        Returns:
            True при успешной установке, False при ошибке
        """
        self.helper.log_message(f"Установка пароля", "INFO")

        if not self.window:
            self.helper.log_message("❌ Окно не инициализировано", "ERROR")
            return False

        return self.helper.set_text(self.window, "field_password", password, timeout)

    def connect_to_server(self, timeout: int = TIMEOUT) -> bool:
        """
        Нажимает кнопку Connect для подключения к серверу.

        Returns:
            True при успешном нажатии кнопки, False при ошибке
        """
        self.helper.log_message("Подключение к серверу", "INFO")

        if not self.window:
            self.helper.log_message("❌ Окно не инициализировано", "ERROR")
            return False

        result = self.helper.click_by_key(self.window, "btn_connect", timeout)

        if result:
            self.is_connected = True
            self.helper.log_message("✅ Кнопка Connect нажата", "SUCCESS")
        else:
            self.helper.log_message("❌ Не удалось нажать кнопку Connect", "ERROR")

        return result

    def go_to_configure(self, timeout: int = TIMEOUT) -> bool:
        """
        Переходит в режим настройки (если доступно).

        Returns:
            True при успешном переходе, False при ошибке
        """
        self.helper.log_message("Переход в режим настройки", "INFO")

        if not self.window:
            self.helper.log_message("❌ Окно не инициализировано", "ERROR")
            return False

        # Ищем кнопку Configure или Settings
        # Пока используем кнопку Connect как заглушку
        # TODO: Добавить реальную кнопку настройки
        self.helper.log_message("⚠️ Функция go_to_configure ещё не реализована", "WARNING")
        return False

    def close(self) -> bool:
        """
        Закрывает окно подключения.

        Returns:
            True при успешном закрытии, False при ошибке
        """
        self.helper.log_message("Закрытие окна подключения", "INFO")

        if not self.window:
            self.helper.log_message("❌ Окно не инициализировано", "ERROR")
            return False

        try:
            self.window.close()
            self.helper.log_message("✅ Окно подключения закрыто", "SUCCESS")
            self.window = None
            self.is_connected = False
            return True
        except Exception as e:
            self.helper.log_message(f"❌ Ошибка при закрытии окна: {e}", "ERROR")
            return False


class EnterpriseConsole:
    """
    Класс для автоматизации работы с главным окном Dispatch Console.

    Атрибуты:
        helper: Экземпляр AppsHelper
        window: Главное окно консоли
        voice_panel: Панель VoiceIP
    """

    def __init__(self):
        """
        Инициализация EnterpriseConsole.

        Args:
            helper: Экземпляр AppsHelper для работы с UI
        """
        self.helper = AppsHelper()
        self.window = None
        self.voice_panel = None

    def get_state_console_window(self, timeout: int = TIMEOUT) -> bool:
        """
        Проверяет, открыто ли главное окно Dispatch Console.

        Args:
            timeout: Время ожидания появления окна в секундах (если None, используется TIMEOUT из конфига)

        Returns:
            True если окно открыто, False в противном случае
        """
        # Если timeout не указан, используем значение из конфига
        if timeout is None:
            timeout = TIMEOUT

        self.helper.log_message(f"Проверка состояния окна Dispatch Console (таймаут: {timeout}с)", "INFO")

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # Ищем окно по паттерну из конфига
                desktop = self.helper.desktop
                windows = desktop.windows(title_re=WINDOW_CONSOLE_PATTERN)

                if windows:
                    # Окно найдено, обновляем ссылку
                    self.window = windows[0]

                    # Проверяем, существует ли окно и видимо ли оно
                    try:
                        if self.window.exists() and self.window.is_visible():
                            self.helper.log_message("✅ Окно Dispatch Console открыто", "SUCCESS")
                            return True
                        else:
                            self.helper.log_message("⚠️ Окно Dispatch Console закрыто или не видимо", "WARNING")
                            time.sleep(0.5)
                            continue
                    except:
                        # Если методы exists/is_visible недоступны, проверяем через window_text
                        try:
                            text = self.window.window_text()
                            if text and "TRBOnet Enterprise" in text and "Dispatch Console" in text:
                                self.helper.log_message("✅ Окно Dispatch Console открыто", "SUCCESS")
                                return True
                        except:
                            pass
                        # Если окно найдено - считаем его открытым
                        self.helper.log_message("✅ Окно Dispatch Console открыто", "SUCCESS")
                        return True

                # Окно не найдено, ждём
                remaining = timeout - (time.time() - start_time)
                if remaining > 0:
                    self.helper.log_message(f"  Ожидание окна... (осталось {remaining:.1f}с)", "INFO")
                    time.sleep(0.5)
                else:
                    break

            except Exception as e:
                self.helper.log_message(f"  Ошибка при проверке состояния окна: {e}", "WARNING")
                time.sleep(0.5)

        # Если вышли из цикла, значит окно не появилось за отведённое время
        self.helper.log_message(f"⚠️ Окно Dispatch Console не найдено за {timeout} секунд", "WARNING")
        self.window = None
        return False

    def find_voice_box(self, radio_name: str, recipient: str, timeout: int = TIMEOUT) -> bool:
        """
        Находит панель VoiceIPControlRadioLarge с указанными параметрами.
        Выполняет скроллинг родительской панели, если бокс не найден.

        Args:
            radio_name: Имя радиостанции (ожидаемый текст в lbl_radio_name)
            recipient: Получатель вызова (ожидаемый текст в cbx_recipients)
            timeout: Время ожидания в секундах

        Returns:
            True если панель найдена и содержит все необходимые элементы, False при ошибке

        Пример:
            # Поиск панели VoiceIP с конкретными параметрами
            if console.find_voice_box("Intercom", "All Call"):
                console.press_ptt()
        """
        self.helper.log_message(f"Поиск панели VoiceIP: radio_name='{radio_name}', recipient='{recipient}'", "INFO")

        if not self.window:
            self.helper.log_message("❌ Главное окно не установлено", "ERROR")
            return False

        # Определяем условия для дочерних элементов (используем переданные аргументы)
        child_conditions = [
            ("lbl_radio_name", radio_name),
            ("cbx_recipients", recipient),
        ]

        # Получаем AutomationId родительской панели для скролла
        parent_panel_auto_id = self.helper.get_auto_id("default_radio_interface")
        if not parent_panel_auto_id:
            self.helper.log_message("❌ Ключ 'default_radio_interface' не найден в AUTO_IDS", "ERROR")
            return False

        # Находим родительскую панель (контейнер со скроллом)
        parent_panel = self.helper.find_element_by_auto_id(self.window, parent_panel_auto_id, timeout)
        if not parent_panel:
            self.helper.log_message("❌ Родительская панель не найдена", "ERROR")
            return False

        # Максимальное количество попыток скролла (чтобы избежать бесконечного цикла)
        max_scroll_attempts = 20
        scroll_attempts = 0

        while scroll_attempts < max_scroll_attempts:
            # Ищем панель с дочерними элементами в текущей видимой области
            self.voice_panel = self.helper.find_panel_with_children(
                self.window,
                "panel_voice_ip",
                child_conditions,
                timeout=2  # Уменьшаем таймаут для быстрой проверки
            )

            if self.voice_panel:
                # Панель найдена - проверяем, полностью ли она видна
                try:
                    # Получаем координаты панели и родительской панели
                    panel_rect = self.voice_panel.rectangle()
                    parent_rect = parent_panel.rectangle()

                    # Проверяем, полностью ли видна панель (не обрезана скроллом)
                    is_fully_visible = (
                            panel_rect.top >= parent_rect.top and
                            panel_rect.bottom <= parent_rect.bottom
                    )

                    if is_fully_visible:
                        self.helper.log_message("✅ Панель VoiceIP найдена и полностью видна", "SUCCESS")
                        return True
                    else:
                        # Панель найдена, но не полностью видна - скроллим до неё
                        self.helper.log_message("  Панель найдена, но не полностью видна. Выполняем скролл...", "INFO")

                        # Скроллим до тех пор, пока панель не станет полностью видимой
                        scroll_steps = 0
                        while scroll_steps < 10 and not is_fully_visible:
                            # Определяем направление скролла
                            if panel_rect.top < parent_rect.top:
                                # Панель выше видимой области - скроллим вверх
                                self.helper.scroll_element(parent_panel, "Up", 1)
                            elif panel_rect.bottom > parent_rect.bottom:
                                # Панель ниже видимой области - скроллим вниз
                                self.helper.scroll_element(parent_panel, "Down", 1)

                            time.sleep(SMALL_DELAY)

                            # Обновляем координаты
                            panel_rect = self.voice_panel.rectangle()
                            parent_rect = parent_panel.rectangle()
                            is_fully_visible = (
                                    panel_rect.top >= parent_rect.top and
                                    panel_rect.bottom <= parent_rect.bottom
                            )
                            scroll_steps += 1

                        if is_fully_visible:
                            self.helper.log_message("✅ Панель VoiceIP найдена и доведена до полной видимости",
                                                    "SUCCESS")
                            return True
                        else:
                            self.helper.log_message("⚠️ Не удалось довести панель до полной видимости", "WARNING")
                            # Возвращаем True, так как панель всё же найдена
                            return True

                except Exception as e:
                    self.helper.log_message(f"⚠️ Ошибка при проверке видимости панели: {e}", "WARNING")
                    # Если не удалось проверить видимость, но панель найдена - считаем успехом
                    return True

            # Панель не найдена - скроллим родительскую панель вниз
            scroll_attempts += 1
            self.helper.log_message(f"  Панель не найдена. Скролл {scroll_attempts}/{max_scroll_attempts}...", "INFO")

            # Проверяем, можем ли мы ещё скроллить (достигнут ли конец)
            try:
                # Пробуем скроллить вниз
                if not self.helper.scroll_element(parent_panel, "Down", 1):
                    # Если не удалось скроллить вниз, пробуем вверх (если мы внизу)
                    self.helper.log_message("  Достигнут конец списка. Проверяем начало...", "INFO")
                    # Скроллим вверх, чтобы проверить начало
                    if not self.helper.scroll_element(parent_panel, "Up", 1):
                        self.helper.log_message("  ❌ Не удалось выполнить скролл. Достигнут конец.", "ERROR")
                        break
            except Exception as e:
                self.helper.log_message(f"  ❌ Ошибка при скролле: {e}", "ERROR")
                break

            time.sleep(SMALL_DELAY)

        # Если вышли из цикла, значит панель не найдена после всех попыток
        self.voice_panel = None
        self.helper.log_message(f"❌ Панель VoiceIP не найдена после {scroll_attempts} попыток скролла", "ERROR")
        return False

    def press_ptt(self, timeout: int = TIMEOUT) -> bool:
        """
        Нажимает кнопку PTT (Push-To-Talk).

        Returns:
            True при успешном нажатии, False при ошибке

        Пример:
            # Нажать PTT для начала голосовой сессии
            console.press_ptt()
        """
        self.helper.log_message("Нажатие кнопки PTT", "INFO")

        if not self.voice_panel:
            self.helper.log_message("❌ Панель VoiceIP не найдена", "ERROR")
            return False

        # Находим кнопку PTT на панели
        result = self.helper.click_by_key(self.voice_panel, "btn_ptt", timeout)

        if result:
            self.helper.log_message("✅ Кнопка PTT нажата", "SUCCESS")
        else:
            self.helper.log_message("❌ Не удалось нажать кнопку PTT", "ERROR")

        return result

    def unpress_ptt(self, timeout: int = TIMEOUT) -> bool:
        """
        Отпускает кнопку PTT (завершает голосовую сессию).

        Returns:
            True при успешном отпускании, False при ошибке

        Пример:
            # Отпустить PTT для завершения голосовой сессии
            console.unpress_ptt()
        """
        self.helper.log_message("Отпускание кнопки PTT", "INFO")

        if not self.voice_panel:
            self.helper.log_message("❌ Панель VoiceIP не найдена", "ERROR")
            return False

        # Находим кнопку PTT на панели и нажимаем (это переключит состояние)
        result = self.helper.click_by_key(self.voice_panel, "btn_ptt", timeout)

        if result:
            self.helper.log_message("✅ Кнопка PTT отпущена", "SUCCESS")
        else:
            self.helper.log_message("❌ Не удалось отпустить кнопку PTT", "ERROR")

        return result

    def long_press_ptt(self, duration: int, timeout: int = TIMEOUT) -> bool:
        """
        Удерживает кнопку PTT в течение указанного времени.

        Args:
            duration: Длительность удержания в секундах
            timeout: Время ожидания для поиска кнопки

        Returns:
            True при успешном удержании, False при ошибке

        Пример:
            # Удерживать PTT 15 секунд
            console.long_press_ptt(15)
        """
        self.helper.log_message(f"Удержание кнопки PTT {duration} секунд", "INFO")

        if not self.voice_panel:
            self.helper.log_message("❌ Панель VoiceIP не найдена", "ERROR")
            return False

        # Находим кнопку PTT на панели
        auto_id = self.helper.get_auto_id("btn_ptt")
        if not auto_id:
            return False

        ptt_button = self.helper.find_element_by_auto_id(self.voice_panel, auto_id, timeout)
        if not ptt_button:
            self.helper.log_message("❌ Кнопка PTT не найдена", "ERROR")
            return False

        try:
            # Нажимаем кнопку PTT
            ptt_button.click_input()
            self.helper.log_message("  ✅ PTT нажата", "SUCCESS")

            # Ждём указанное время
            self.helper.log_message(f"  ⏳ Удержание {duration} секунд...", "INFO")
            time.sleep(duration)

            # Отпускаем кнопку PTT
            ptt_button.click_input()
            self.helper.log_message("  ✅ PTT отпущена", "SUCCESS")

            return True

        except Exception as e:
            self.helper.log_message(f"  ❌ Ошибка при удержании PTT: {e}", "ERROR")
            return False

    def check_box_state(self, key: str) -> Optional[bool]:
        """
        Получает состояние чек-бокса по ключу.

        Args:
            key: Ключ чек-бокса в словаре AUTO_IDS

        Returns:
            True если включен, False если выключен, None при ошибке
        """
        self.helper.log_message(f"Получение состояния чек-бокса по ключу: '{key}'", "INFO")

        # TODO: Реализовать метод после добавления чек-боксов в интерфейс
        self.helper.log_message("⚠️ Функция check_box_state ещё не реализована", "WARNING")
        return None

    def close(self, timeout: int = TIMEOUT) -> bool:
        """
        Закрывает главное окно Dispatch Console.

        Returns:
            True при успешном закрытии, False при ошибке
        """
        self.helper.log_message("Закрытие Dispatch Console", "INFO")

        if not self.window:
            self.helper.log_message("❌ Окно не инициализировано", "ERROR")
            return False

        try:
            self.window.close()
            self.helper.log_message("✅ Dispatch Console закрыта", "SUCCESS")
            self.window = None
            self.voice_panel = None
            return True
        except Exception as e:
            self.helper.log_message(f"❌ Ошибка при закрытии окна: {e}", "ERROR")
            return False

    def get_voice_box_color(self, timeout: int = TIMEOUT) -> bool | str | None:
        """
        Определяет цвет внутри найденного бокса.

        Returns:
            Имя цвета из словаря COLORS или None при ошибке

        Пример:
            # Определить состояние бокса
            color = console.get_voice_box_color()
            if color == "green":
                print("Бокс активен")
            elif color == "gray":
                print("Бокс неактивен")
        """
        self.helper.log_message("Определение цвета бокса", "INFO")

        if not self.voice_panel:
            self.helper.log_message("❌ Панель VoiceIP не найдена", "ERROR")
            return None

        # Используем новый метод для получения цвета из элемента
        result = self.helper.get_color_from_element(self.voice_panel, timeout)

        if result:
            self.helper.log_message(f"✅ Цвет бокса: {result}", "SUCCESS")
        else:
            self.helper.log_message("❌ Не удалось определить цвет бокса", "ERROR")

        return result

    def get_voice_box_info(self, call_type: str, call_info: str, call_sender: str, timeout: int = TIMEOUT) -> Tuple[bool, Optional[dict]]:
        """
        Получает информацию из панели VoiceIP и проверяет соответствие переданным значениям.

        Args:
            call_type: Ожидаемый тип вызова
            call_info: Ожидаемая информация о вызове
            call_sender: Ожидаемый отправитель вызова
            timeout: Время ожидания в секундах

        Returns:
            Кортеж (success, differences):
                success: True если все значения совпадают, False в противном случае
                differences: Словарь с несовпадающими значениями или None при ошибке

        Пример:
            success, diff = console.get_voice_box_info("Group Call", "Channel 1", "Dispatcher")
            if success:
                print("Все данные совпадают")
            else:
                print(f"Несовпадения: {diff}")
        """
        self.helper.log_message(f"Получение информации из панели VoiceIP", "INFO")
        self.helper.log_message(
            f"  Ожидаемые значения: call_type='{call_type}', call_info='{call_info}', call_sender='{call_sender}'",
            "INFO")

        if not self.voice_panel:
            self.helper.log_message("❌ Панель VoiceIP не найдена", "ERROR")
            return False, None

        # Словарь для хранения полученных значений
        actual_values = {}
        differences = {}

        # Определяем соответствие ключей и ожидаемых значений
        elements_to_check = [
            ("vb_call_type", call_type, "call_type"),
            ("vb_call_info", call_info, "call_info"),
            ("vb_call_sender", call_sender, "call_sender"),
        ]

        for key, expected_value, field_name in elements_to_check:
            # Получаем AutomationId по ключу
            auto_id = self.helper.get_auto_id(key)
            if not auto_id:
                self.helper.log_message(f"❌ Ключ '{key}' не найден в AUTO_IDS", "ERROR")
                return False, None

            # Ищем дочерний элемент внутри панели
            element = None
            try:
                children = self.voice_panel.descendants()
                for child in children:
                    try:
                        child_auto_id = child.element_info.automation_id if hasattr(child, 'element_info') else None
                        if child_auto_id == auto_id:
                            element = child
                            break
                    except:
                        continue
            except Exception as e:
                self.helper.log_message(f"  Ошибка при поиске элемента '{key}': {e}", "ERROR")
                return False, None

            if not element:
                self.helper.log_message(f"  ❌ Элемент с ключом '{key}' не найден в панели", "ERROR")
                return False, None

            # Получаем текст из элемента
            try:
                # Пробуем получить текст через window_text()
                actual_text = element.window_text() if hasattr(element, 'window_text') else ""

                # Если текст пустой, пробуем другие методы
                if not actual_text:
                    if hasattr(element, 'get_text'):
                        try:
                            actual_text = element.get_text()
                        except:
                            pass

                    # Если всё ещё пусто, пробуем через element_info
                    if not actual_text and hasattr(element, 'element_info'):
                        try:
                            if hasattr(element.element_info, 'name'):
                                actual_text = element.element_info.name
                        except:
                            pass

                actual_values[field_name] = actual_text.strip()
                self.helper.log_message(f"  Элемент '{key}': '{actual_text}' (ожидалось: '{expected_value}')", "INFO")

                # Проверяем соответствие
                if actual_text.strip() != expected_value:
                    differences[field_name] = {
                        "expected": expected_value,
                        "actual": actual_text.strip()
                    }

            except Exception as e:
                self.helper.log_message(f"  ❌ Ошибка при получении текста из элемента '{key}': {e}", "ERROR")
                return False, None

        # Проверяем результат
        if not differences:
            self.helper.log_message("✅ Все значения совпадают", "SUCCESS")
            return True, None
        else:
            self.helper.log_message(f"⚠️ Найдены несовпадения: {differences}", "WARNING")
            return False, differences

    def close(self, timeout: int = TIMEOUT, wait_for_process: bool = True) -> bool:
        """
        Закрывает главное окно Dispatch Console и проверяет завершение процесса.

        Args:
            timeout: Время ожидания для закрытия окна и завершения процесса в секундах
            wait_for_process: Если True, ожидает завершения процесса после закрытия окна

        Returns:
            True при успешном закрытии и завершении процесса (если требуется), False при ошибке
        """
        self.helper.log_message("Закрытие Dispatch Console", "INFO")

        if not self.window:
            self.helper.log_message("❌ Окно не инициализировано", "ERROR")
            return False

        # Получаем имя процесса из конфига
        process_name = PROCESS_NAMES.get("console")
        if not process_name:
            self.helper.log_message("❌ Ключ 'console' не найден в PROCESS_NAMES", "ERROR")
            return False

        try:
            # Закрываем окно
            self.window.close()
            self.helper.log_message("  ✅ Команда закрытия отправлена", "SUCCESS")

            # Сбрасываем ссылки на окно и панель
            self.window = None
            self.voice_panel = None

            # Если нужно ожидать завершения процесса
            if wait_for_process:
                self.helper.log_message(f"  Ожидание завершения процесса '{process_name}'...", "INFO")

                # Используем wait_for_process_exit для ожидания завершения
                if self.helper.wait_for_process_exit(process_name, timeout):
                    self.helper.log_message("✅ Dispatch Console закрыта (процесс завершён)", "SUCCESS")
                    return True
                else:
                    self.helper.log_message(f"⚠️ Процесс '{process_name}' не завершился за {timeout} секунд", "WARNING")
                    return False
            else:
                # Не ждём завершения процесса
                self.helper.log_message("✅ Dispatch Console закрыта (без ожидания процесса)", "SUCCESS")
                return True

        except Exception as e:
            self.helper.log_message(f"❌ Ошибка при закрытии окна: {e}", "ERROR")
            return False