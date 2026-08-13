"""
one_console.py - Классы для автоматизации работы с TRBOnet One Console

Назначение: Содержит классы ConnectionManager и OneConsole для
автоматизации работы с приложением TRBOnet One Console.
Использует apps.apps_helpers.py как библиотеку утилит.
"""

import time
from typing import Optional, List, Tuple, Dict, Any
from pywinauto.application import Application

from apps.apps_helpers import AppsHelper
from core_desktop.config import TIMEOUT, SMALL_DELAY, LARGE_DELAY, ONE_EXE_PATH, WINDOW_CONNECT_MANAGER_ONE_PATTERN, WINDOW_ONE_PATTERN
from core_desktop.config_auto_ids import AUTO_IDS, DIALOG_TEXTS, PROCESS_NAMES



class ConnectionManager:
    """
    Класс для автоматизации работы с окном подключения к серверу TRBOnet One.

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
            exe_path: Путь к исполняемому файлу (опционально)
            window_title: Заголовок окна подключения (опционально)
            timeout: Таймаут по умолчанию (опционально)
        """
        self.helper = AppsHelper()
        self.exe_path = exe_path or ONE_EXE_PATH
        self.window_title = window_title or "TRBOnet Connection Manager"
        self.window = None
        self.is_connected = False
        self.timeout = timeout or TIMEOUT

    def open(self, timeout: int = TIMEOUT) -> bool:
        """
        Открывает окно подключения к серверу.

        Args:
            timeout: Время ожидания в секундах

        Returns:
            True при успешном открытии окна, False при ошибке
        """
        self.helper.log_message("Открытие окна подключения к серверу TRBOnet One", "INFO")

        app = self.helper.launch_app(self.exe_path)
        if app is None:
            self.helper.log_message("Не удалось запустить приложение", "ERROR")
            return False

        self.window = self.helper.find_window(WINDOW_CONNECT_MANAGER_ONE_PATTERN, timeout)
        if not self.window:
            self.helper.log_message("❌ Окно подключения не найдено", "ERROR")
            return False

        # Ожидаем полной загрузки окна
        key_elements = ["ConsoleTypeCb", "btnConnect"]
        if not self.helper.wait_for_window_ready(self.window, key_elements, timeout):
            self.helper.log_message("❌ Окно подключения не загрузилось полностью", "ERROR")
            return False

        self.helper.log_message("✅ Окно подключения открыто и загружено", "SUCCESS")
        return True

    def get_state_cm_window(self, timeout: Optional[int] = None) -> bool:
        """
        Проверяет, открыто ли окно Connection Manager.

        Args:
            timeout: Время ожидания появления окна в секундах

        Returns:
            True если окно открыто, False в противном случае
        """
        if timeout is None:
            timeout = self.timeout

        self.helper.log_message(f"Проверка состояния окна Connection Manager (таймаут: {timeout}с)", "INFO")

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                desktop = self.helper.desktop
                windows = desktop.windows(title_re=WINDOW_CONNECT_MANAGER_ONE_PATTERN)

                if windows:
                    self.window = windows[0]

                    try:
                        if self.window.exists() and self.window.is_visible():
                            self.helper.log_message("✅ Окно Connection Manager открыто", "SUCCESS")
                            return True
                    except:
                        try:
                            text = self.window.window_text()
                            if text and "Connect" in text:
                                self.helper.log_message("✅ Окно Connection Manager открыто", "SUCCESS")
                                return True
                        except:
                            pass
                        self.helper.log_message("✅ Окно Connection Manager открыто", "SUCCESS")
                        return True

                remaining = timeout - (time.time() - start_time)
                if remaining > 0:
                    self.helper.log_message(f"  Ожидание окна... (осталось {remaining:.1f}с)", "INFO")
                    time.sleep(0.5)
                else:
                    break

            except Exception as e:
                self.helper.log_message(f"  Ошибка при проверке состояния окна: {e}", "WARNING")
                time.sleep(0.5)

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

        return self.helper.set_combo_text_by_key(self.window, "cm_address_one", address, timeout)

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

        return self.helper.set_text(self.window, "cm_port_one", port, timeout)

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

        return self.helper.select_combo_item_by_key(self.window, "cm_auth_method_one", method, timeout)

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

        return self.helper.set_text(self.window, "cm_user_name_one", username, timeout)

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

        return self.helper.set_text(self.window, "cm_password_one", password, timeout)

    def set_console_type(self, console_type: str, timeout: int = TIMEOUT) -> bool:
        """
        Устанавливает тип консоли в ComboBox.

        Args:
            console_type: Тип консоли (например, "TRBOnetOne")
            timeout: Время ожидания в секундах

        Returns:
            True при успешной установке, False при ошибке
        """
        self.helper.log_message(f"Установка типа консоли: '{console_type}'", "INFO")

        if not self.window:
            self.helper.log_message("❌ Окно не инициализировано", "ERROR")
            return False

        return self.helper.select_combo_item_by_key(self.window, "combo_console_type", console_type, timeout)

    def set_console_type_one(self, timeout: int = TIMEOUT) -> bool:
        """
        Устанавливает тип консоли "TRBOnetOne".

        Args:
            timeout: Время ожидания в секундах

        Returns:
            True при успешной установке, False при ошибке
        """
        console_type = DIALOG_TEXTS.get("console_type_one", "TRBOnetOne")
        return self.set_console_type(console_type, timeout)

    def connect_to_server(self, timeout: int = TIMEOUT) -> bool:
        """
        Нажимает кнопку Connect для подключения к серверу.

        Args:
            timeout: Время ожидания в секундах

        Returns:
            True при успешном нажатии кнопки, False при ошибке
        """
        self.helper.log_message("Подключение к серверу TRBOnet One", "INFO")

        if not self.window:
            self.helper.log_message("❌ Окно не инициализировано", "ERROR")
            return False

        # Находим кнопку Connect
        btn_connect = self.helper.find_element_by_key(self.window, "btn_connect_one", timeout)
        if not btn_connect:
            self.helper.log_message("❌ Кнопка Connect не найдена", "ERROR")
            return False

        result = self.helper.click_element_safe(btn_connect, "Connect")

        if result:
            self.is_connected = True
            self.helper.log_message("✅ Кнопка Connect нажата", "SUCCESS")
        else:
            self.helper.log_message("❌ Не удалось нажать кнопку Connect", "ERROR")

        return result

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


class OneConsole:
    """
    Класс для автоматизации работы с главным окном TRBOnet One Console.

    Атрибуты:
        helper: Экземпляр AppsHelper
        window: Главное окно консоли
        ptt_button: Кнопка PTT
        process_name: Имя процесса
    """

    def __init__(self):
        """
        Инициализация OneConsole.
        """
        self.helper = AppsHelper()
        self.window = None
        self.ptt_button = None
        self.process_name = PROCESS_NAMES.get("one", "TRBOnet.One.exe")

    def get_state_console_window(self, timeout: int = TIMEOUT) -> bool:
        """
        Проверяет, открыто ли главное окно TRBOnet One Console.

        Args:
            timeout: Время ожидания появления окна в секундах

        Returns:
            True если окно открыто, False в противном случае
        """
        self.helper.log_message(f"Проверка состояния окна TRBOnet One (таймаут: {timeout}с)", "INFO")

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                desktop = self.helper.desktop
                windows = desktop.windows(title_re=WINDOW_ONE_PATTERN)

                if windows:
                    self.window = windows[0]

                    try:
                        if self.window.exists() and self.window.is_visible():
                            self.helper.log_message("✅ Окно TRBOnet One открыто", "SUCCESS")
                            return True
                    except:
                        try:
                            text = self.window.window_text()
                            if text and "TRBOnet One" in text:
                                self.helper.log_message("✅ Окно TRBOnet One открыто", "SUCCESS")
                                return True
                        except:
                            pass
                        self.helper.log_message("✅ Окно TRBOnet One открыто", "SUCCESS")
                        return True

                remaining = timeout - (time.time() - start_time)
                if remaining > 0:
                    self.helper.log_message(f"  Ожидание окна... (осталось {remaining:.1f}с)", "INFO")
                    time.sleep(0.5)
                else:
                    break

            except Exception as e:
                self.helper.log_message(f"  Ошибка при проверке состояния окна: {e}", "WARNING")
                time.sleep(0.5)

        self.helper.log_message(f"⚠️ Окно TRBOnet One не найдено за {timeout} секунд", "WARNING")
        self.window = None
        return False

    def wait_for_ready(self, timeout: int = TIMEOUT) -> bool:
        """
        Ожидает полной загрузки окна TRBOnet One.
        Проверяет наличие кнопки PTT.

        Args:
            timeout: Время ожидания в секундах

        Returns:
            True если окно загружено, False при ошибке
        """
        self.helper.log_message("Ожидание полной загрузки TRBOnet One...", "INFO")

        if not self.window:
            self.helper.log_message("❌ Окно не инициализировано", "ERROR")
            return False

        result = self.helper.wait_for_window_ready_by_text(self.window, "PTT", timeout)

        if result:
            self.helper.log_message("✅ TRBOnet One полностью загружена", "SUCCESS")
        else:
            self.helper.log_message("❌ TRBOnet One не загрузилась полностью", "ERROR")

        return result

    def find_ptt_button(self, timeout: int = TIMEOUT) -> bool:
        """
        Находит активную кнопку PTT.

        Args:
            timeout: Время ожидания в секундах

        Returns:
            True если кнопка найдена, False при ошибке
        """
        self.helper.log_message("Поиск активной кнопки PTT", "INFO")

        if not self.window:
            self.helper.log_message("❌ Окно не инициализировано", "ERROR")
            return False

        self.ptt_button = self.helper.find_active_button_by_text(self.window, "PTT", timeout)

        if self.ptt_button:
            self.helper.log_message("✅ Активная кнопка PTT найдена", "SUCCESS")
            return True
        else:
            self.helper.log_message("❌ Активная кнопка PTT не найдена", "ERROR")
            return False

    def press_ptt(self, timeout: int = TIMEOUT) -> bool:
        """
        Нажимает кнопку PTT (Push-To-Talk).

        Args:
            timeout: Время ожидания в секундах

        Returns:
            True при успешном нажатии, False при ошибке
        """
        self.helper.log_message("Нажатие кнопки PTT", "INFO")

        if not self.ptt_button:
            self.helper.log_message("❌ Кнопка PTT не найдена. Выполняем поиск...", "WARNING")
            if not self.find_ptt_button(timeout):
                return False

        result = self.helper.click_element_safe(self.ptt_button, "PTT")

        if result:
            self.helper.log_message("✅ Кнопка PTT нажата", "SUCCESS")
        else:
            self.helper.log_message("❌ Не удалось нажать кнопку PTT", "ERROR")

        return result

    def press_ptt_after_delay(self, delay_seconds: int, timeout: int = TIMEOUT) -> bool:
        """
        Ожидает указанное время и нажимает кнопку PTT.

        Args:
            delay_seconds: Время ожидания в секундах перед нажатием
            timeout: Время ожидания для поиска кнопки

        Returns:
            True при успешном нажатии, False при ошибке
        """
        self.helper.log_message(f"Ожидание {delay_seconds} секунд перед нажатием PTT", "INFO")

        time.sleep(delay_seconds)

        # После ожидания ищем кнопку заново
        if not self.find_ptt_button(timeout):
            self.helper.log_message("❌ Кнопка PTT не найдена после ожидания", "ERROR")
            return False

        return self.press_ptt(timeout)

    def press_ptt_twice(self, delay_between: int = 15, timeout: int = TIMEOUT) -> bool:
        """
        Нажимает PTT, ждёт указанное время и нажимает снова.

        Args:
            delay_between: Время ожидания между нажатиями в секундах
            timeout: Время ожидания для поиска кнопки

        Returns:
            True если оба нажатия успешны, False при ошибке
        """
        self.helper.log_message(f"Двойное нажатие PTT с задержкой {delay_between} секунд", "INFO")

        # Первое нажатие
        if not self.find_ptt_button(timeout):
            return False

        if not self.press_ptt(timeout):
            self.helper.log_message("❌ Первое нажатие PTT не удалось", "ERROR")
            return False

        # Ожидание
        self.helper.log_message(f"  ⏳ Ожидание {delay_between} секунд...", "INFO")
        time.sleep(delay_between)

        # Второе нажатие - ищем кнопку заново
        if not self.find_ptt_button(timeout):
            self.helper.log_message("❌ Кнопка PTT не найдена при повторном поиске", "ERROR")
            return False

        if not self.press_ptt(timeout):
            self.helper.log_message("❌ Второе нажатие PTT не удалось", "ERROR")
            return False

        self.helper.log_message("✅ Двойное нажатие PTT выполнено успешно", "SUCCESS")
        return True

    def take_screenshot(self, save_path: str, mask_areas: Optional[List[dict]] = None) -> bool:
        """
        Делает скриншот главного окна TRBOnet One.

        Args:
            save_path: Путь для сохранения скриншота
            mask_areas: Список областей для маскирования

        Returns:
            True при успешном сохранении, False при ошибке
        """
        self.helper.log_message(f"Создание скриншота TRBOnet One: {save_path}", "INFO")

        if not self.window:
            self.helper.log_message("❌ Окно не инициализировано", "ERROR")
            return False

        return self.helper.take_screenshot(self.window, save_path, mask_areas)

    def compare_screenshot(self, expected_path: str, actual_path: str, diff_path: str,
                          mask_areas: Optional[List[dict]] = None) -> Tuple[bool, float]:
        """
        Сравнивает скриншот с эталоном.

        Args:
            expected_path: Путь к эталонному изображению
            actual_path: Путь к фактическому изображению
            diff_path: Путь для сохранения изображения с отличиями
            mask_areas: Список областей для маскирования

        Returns:
            Кортеж (has_diff, diff_percent)
        """
        self.helper.log_message("Сравнение скриншотов TRBOnet One", "INFO")

        return self.helper.compare_images(expected_path, actual_path, diff_path,
                                          mask_areas=mask_areas,
                                          mask_enabled=True)

    def get_process_info(self) -> Tuple[int, List[int]]:
        """
        Получает информацию о процессе TRBOnet One.

        Returns:
            Кортеж (количество_процессов, список_PID)
        """
        return self.helper.get_process_count(self.process_name)

    def is_process_running(self) -> bool:
        """
        Проверяет, запущен ли процесс TRBOnet One.

        Returns:
            True если процесс запущен, False в противном случае
        """
        count, _ = self.get_process_info()
        return count > 0

    def close(self, timeout: int = TIMEOUT, wait_for_process: bool = True) -> bool:
        """
        Закрывает главное окно TRBOnet One.

        Args:
            timeout: Время ожидания для закрытия окна и завершения процесса
            wait_for_process: Если True, ожидает завершения процесса

        Returns:
            True при успешном закрытии, False при ошибке
        """
        self.helper.log_message("Закрытие TRBOnet One", "INFO")

        if not self.window:
            self.helper.log_message("❌ Окно не инициализировано", "ERROR")
            return False

        try:
            self.window.close()
            self.helper.log_message("  ✅ Команда закрытия отправлена", "SUCCESS")

            self.window = None
            self.ptt_button = None

            if wait_for_process:
                self.helper.log_message(f"  Ожидание завершения процесса '{self.process_name}'...", "INFO")

                if self.helper.wait_for_process_exit(self.process_name, timeout):
                    self.helper.log_message("✅ TRBOnet One закрыта (процесс завершён)", "SUCCESS")
                    return True
                else:
                    self.helper.log_message(f"⚠️ Процесс '{self.process_name}' не завершился за {timeout} секунд",
                                            "WARNING")
                    return False
            else:
                self.helper.log_message("✅ TRBOnet One закрыта (без ожидания процесса)", "SUCCESS")
                return True

        except Exception as e:
            self.helper.log_message(f"❌ Ошибка при закрытии окна: {e}", "ERROR")
            return False

    def wait_for_color_change(self,
                              from_color: str = None,
                              to_color: str = None,
                              timeout: int = TIMEOUT) -> Dict[str, Any] | None:
        """
        Ожидает изменения цвета с одного на другой.

        Args:
            from_color: Начальный цвет (если None, любой)
            to_color: Конечный цвет (если None, любой)
            timeout: Время ожидания в секундах

        Returns:
            Словарь с информацией об изменении или None при ошибке
        """
        self.helper.log_message(f"Ожидание изменения цвета: {from_color} → {to_color}", "INFO")

        if not self.ptt_button:
            self.helper.log_message("❌ Панель VoiceIP не найдена", "ERROR")
            return None

        start_time = time.time()
        initial_color = None
        current_color = None
        colors_history = []

        # Получаем начальный цвет
        initial_color = self.helper.get_color_from_element(self.ptt_button, timeout=2)
        colors_history.append(initial_color)
        self.helper.log_message(f"  Начальный цвет: {initial_color}", "INFO")

        # Проверяем, соответствует ли начальный цвет ожидаемому
        if from_color and initial_color != from_color:
            self.helper.log_message(f"  ⚠️ Начальный цвет {initial_color} не соответствует ожидаемому {from_color}",
                                    "WARNING")

        # Ждём изменения
        while time.time() - start_time < timeout:
            current_color = self.helper.get_color_from_element(self.ptt_button, timeout=1)
            colors_history.append(current_color)

            # Проверяем, достигнут ли нужный цвет
            if to_color:
                if current_color == to_color:
                    elapsed = time.time() - start_time
                    self.helper.log_message(f"  ✅ Цвет стал {to_color} через {elapsed:.1f} сек.", "SUCCESS")
                    return {
                        "initial_color": initial_color,
                        "current_color": current_color,
                        "changed": current_color != initial_color,
                        "elapsed": elapsed,
                        "colors_history": colors_history,
                        "success": True
                    }
            else:
                # Если to_color не указан, ждём любого изменения
                if current_color != initial_color and current_color is not None:
                    elapsed = time.time() - start_time
                    self.helper.log_message(
                        f"  ✅ Цвет изменился: {initial_color} → {current_color} (через {elapsed:.1f} сек.)", "SUCCESS")
                    return {
                        "initial_color": initial_color,
                        "current_color": current_color,
                        "changed": True,
                        "elapsed": elapsed,
                        "colors_history": colors_history,
                        "success": True
                    }

            time.sleep(0.3)

        # Таймаут
        self.helper.log_message(f"  ❌ Цвет не изменился за {timeout} сек.", "ERROR")
        return {
            "initial_color": initial_color,
            "current_color": current_color,
            "changed": False,
            "elapsed": timeout,
            "colors_history": colors_history,
            "success": False
        }
