"""
configurator.py - Класс ServerConfigurator для высокоуровневой автоматизации приложения

Назначение: Реализует три высокоуровневых шага для управления приложением:
открытие, применение изменений, закрытие. Использует AppsHelper как библиотеку утилит.
"""

import os
import sys
import time
from typing import Optional

# Добавляем текущую папку в путь поиска модулей
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from apps.apps_helpers import AppsHelper
from core_desktop.config import SERVER_EXE_PATH, SERVER_WINDOW_TITLE, TIMEOUT, MEDIUM_DELAY
from core_desktop.config_auto_ids import DIALOG_TEXTS


class ServerConfigurator:
    """
    Класс-конфигуратор для автоматизации работы с приложением сервера.
    Предоставляет высокоуровневые методы для управления приложением:
    открытие, применение изменений, закрытие.

    Использует AppsHelper для выполнения низкоуровневых операций.
    """

    def __init__(self, exe_path: Optional[str] = None,
                 window_title: Optional[str] = None,
                 timeout: Optional[int] = None):
        """
        Инициализация конфигуратора.

        Args:
            exe_path (str, optional): Путь к исполняемому файлу.
                                      По умолчанию из core_desktop.config
            window_title (str, optional): Заголовок окна приложения.
                                          По умолчанию из core_desktop.config
            timeout (int, optional): Таймаут ожидания в секундах.
                                     По умолчанию из core_desktop.config
        """
        self.exe_path = exe_path or SERVER_EXE_PATH
        self.window_title = window_title or SERVER_WINDOW_TITLE
        self.timeout = timeout or TIMEOUT

        # Инициализация помощника
        self.helper = AppsHelper()
        self.helper.set_main_window(SERVER_WINDOW_TITLE)

        self.helper.log_message(f"Инициализация ServerConfigurator", "INFO")
        self.helper.log_message(f"  Путь к приложению: {self.exe_path}", "DEBUG")
        self.helper.log_message(f"  Заголовок окна: {self.window_title}", "DEBUG")
        self.helper.log_message(f"  Таймаут: {self.timeout} сек.", "DEBUG")

    def open(self) -> bool:
        """
        Запускает приложение и проверяет, что окно появилось.

        Returns:
            bool: True если окно найдено, иначе False
        """
        self.helper.log_message("Открытие приложения...", "INFO")

        # Запуск приложения
        app = self.helper.launch_app(self.exe_path)
        if app is None:
            self.helper.log_message("Не удалось запустить приложение", "ERROR")
            return False

        # Поиск главного окна
        window = self.helper.find_window(self.window_title, self.timeout)
        if window is None:
            self.helper.log_message(f"Окно '{self.window_title}' не найдено", "ERROR")
            return False

        # Устанавливаем главное окно в helper
        self.helper.main_window = window

        self.helper.log_message(f"Приложение успешно открыто, окно '{self.window_title}' найдено", "INFO")
        return True

    def open_with_admin(self) -> bool:
        """
        Запускает приложение с правами администратора и проверяет, что окно появилось.

        Returns:
            bool: True если окно найдено, иначе False
        """
        import ctypes

        self.helper.log_message("Открытие приложения с правами администратора...", "INFO")

        try:
            # Используем ShellExecuteW для запуска с правами администратора
            ctypes.windll.shell32.ShellExecuteW(
                None,  # hwnd
                "runas",  # операция (runas = администратор)
                self.exe_path,  # файл
                None,  # параметры
                None,  # рабочая директория
                1  # показать окно (SW_SHOWNORMAL)
            )
            # Даем время на запуск
            time.sleep(3)
        except Exception as e:
            self.helper.log_message(f"Ошибка при запуске приложения: {e}", "ERROR")
            return False

        # Поиск главного окна через Desktop
        try:
            from pywinauto import Application
            temp_app = Application(backend="uia").connect(title_re=self.window_title)
            window = temp_app.window(title_re=self.window_title)
            if window is None:
                self.helper.log_message(f"Окно '{self.window_title}' не найдено", "ERROR")
                return False

            # Устанавливаем приложение и окно в helper
            self.helper.app = temp_app
            self.helper.main_window = window

            self.helper.log_message(f"Приложение успешно открыто с правами администратора", "INFO")
            return True
        except Exception as e:
            self.helper.log_message(f"Ошибка при поиске главного окна: {e}", "ERROR")
            return False

    def connect_to_running(self) -> bool:
        """
        Подключается к уже запущенному приложению.

        Returns:
            bool: True если подключение успешно, иначе False
        """
        self.helper.log_message("Подключение к запущенному приложению...", "INFO")

        try:
            from pywinauto import Application
            app = Application(backend="uia").connect(title_re=self.window_title)
            window = app.window(title_re=self.window_title)

            if window is None:
                self.helper.log_message(f"Окно '{self.window_title}' не найдено", "ERROR")
                return False

            self.helper.app = app
            self.helper.main_window = window
            self.helper.log_message(f"Подключено к приложению '{self.window_title}'", "SUCCESS")
            return True
        except Exception as e:
            self.helper.log_message(f"Ошибка при подключении: {e}", "ERROR")
            return False

    def apply_and_save(self) -> bool:
        """
        Применяет изменения: клик по Apply, ожидание диалога, клик Yes.

        Returns:
            bool: True если все шаги успешны, иначе False
        """
        self.helper.log_message("Применение изменений...", "INFO")

        # Проверяем наличие главного окна
        if self.helper.main_window is None:
            self.helper.log_message("Главное окно не найдено. Попытка подключиться...", "WARNING")
            if not self.connect_to_running():
                self.helper.log_message("Не удалось найти главное окно", "ERROR")
                return False

        # Клик по кнопке Apply
        if not self.helper.click_by_key_main("btn_apply", self.timeout):
            self.helper.log_message("Не удалось кликнуть по кнопке Apply", "ERROR")
            return False

        # Ожидание текста диалога перезагрузки
        dialog_text = DIALOG_TEXTS.get("restart_dialog")
        if not dialog_text:
            self.helper.log_message("❌ Ключ 'restart_dialog' не найден в DIALOG_TEXTS", "ERROR")
            return False

        if not self.helper.wait_for_dialog_text(dialog_text, self.timeout):
            self.helper.log_message("Диалог перезагрузки не появился или текст не найден", "ERROR")
            return False

        # Клик по кнопке Yes в диалоге
        if not self.helper.click_dialog_button("Yes", self.timeout):
            self.helper.log_message("Не удалось кликнуть по кнопке Yes в диалоге", "ERROR")
            return False

        self.helper.log_message("Изменения успешно применены", "INFO")
        return True

    def close_by_OK(self) -> bool:
        """
        Закрывает приложение через кнопку OK и проверяет, что окно исчезло.

        Returns:
            bool: True если окно закрылось, иначе False
        """
        self.helper.log_message("Закрытие приложения...", "INFO")

        # Проверяем наличие главного окна
        if self.helper.main_window is None:
            self.helper.log_message("Главное окно не найдено. Попытка подключиться...", "WARNING")
            if not self.connect_to_running():
                self.helper.log_message("Не удалось найти главное окно", "ERROR")
                return False

        # Поиск кнопки OK
        ok_button = self.helper.find_element_by_text_main("OK", self.timeout)
        if ok_button is None:
            self.helper.log_message("Кнопка OK не найдена", "ERROR")
            return False

        # Клик по кнопке OK
        try:
            ok_button.click_input()
            time.sleep(0.5)
            self.helper.log_message("Клик по кнопке OK выполнен", "INFO")
        except Exception as e:
            self.helper.log_message(f"Ошибка при клике по кнопке OK: {e}", "ERROR")
            return False

        # Проверка, что окно исчезло
        time.sleep(1)  # Небольшая задержка для закрытия окна

        try:
            from pywinauto import Desktop
            desktop = Desktop(backend="uia")
            windows = desktop.windows(title_re=self.window_title)

            if not windows:
                self.helper.log_message(f"Окно '{self.window_title}' успешно закрылось", "INFO")
                self.helper.app = None
                self.helper.main_window = None
                return True
            else:
                self.helper.log_message(f"Окно '{self.window_title}' все еще открыто", "ERROR")
                return False
        except Exception as e:
            self.helper.log_message(f"Ошибка при проверке закрытия окна: {e}", "ERROR")
            return False

    def close_by_process(self) -> bool:
        """
        Закрывает приложение через завершение процесса.

        Returns:
            bool: True если процесс завершен, иначе False
        """
        self.helper.log_message("Закрытие приложения через процесс...", "INFO")

        try:
            import psutil
            import os

            # Получаем имя процесса из пути
            process_name = os.path.basename(self.exe_path)

            # Ищем и завершаем процесс
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    if proc.info['exe'] == self.exe_path:
                        proc.terminate()
                        proc.wait(timeout=3)
                        self.helper.log_message(f"Процесс {process_name} завершен", "INFO")
                        self.helper.app = None
                        self.helper.main_window = None
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                    continue

            self.helper.log_message(f"Процесс {process_name} не найден", "WARNING")
            return False
        except ImportError:
            self.helper.log_message("Модуль psutil не установлен", "ERROR")
            return False
        except Exception as e:
            self.helper.log_message(f"Ошибка при закрытии процесса: {e}", "ERROR")
            return False

    def is_running(self) -> bool:
        """
        Проверяет, запущено ли приложение.

        Returns:
            bool: True если окно найдено, иначе False
        """
        try:
            from pywinauto import Desktop
            desktop = Desktop(backend="uia")
            windows = desktop.windows(title_re=self.window_title)
            return len(windows) > 0
        except Exception:
            return False

    def get_status(self) -> dict:
        """
        Возвращает статус приложения в виде словаря.

        Returns:
            dict: Словарь с информацией о состоянии приложения
        """
        status = {
            "is_running": self.is_running(),
            "window_title": self.window_title,
            "exe_path": self.exe_path,
            "has_main_window": self.helper.main_window is not None,
            "has_app": self.helper.app is not None
        }
        return status

    def get_service_state(self) -> str:
        """
        Определяет состояние сервиса Windows 'TRBOnet.Server'.

        Returns:
            str: Состояние сервиса ('running', 'stopped', 'starting', 'stopping', 'paused')
                 или False, если сервис не найден
        """
        self.helper.log_message(f"Проверка состояния сервиса TRBOnet.Server...", "INFO")

        try:
            import win32serviceutil
            import win32service
            import win32api

            service_name = "TRBOnet.Server"

            # Пытаемся получить статус сервиса
            status = win32serviceutil.QueryServiceStatus(service_name)
            state_code = status[1]  # Индекс 1 содержит состояние сервиса

            # Преобразуем числовое состояние в строку
            state_map = {
                win32service.SERVICE_STOPPED: "stopped",
                win32service.SERVICE_START_PENDING: "starting",
                win32service.SERVICE_STOP_PENDING: "stopping",
                win32service.SERVICE_RUNNING: "running",
                win32service.SERVICE_CONTINUE_PENDING: "continuing",
                win32service.SERVICE_PAUSE_PENDING: "pausing",
                win32service.SERVICE_PAUSED: "paused"
            }

            state_text = state_map.get(state_code, f"unknown ({state_code})")
            self.helper.log_message(f"✅ Сервис '{service_name}' найден. Состояние: {state_text}", "SUCCESS")
            return state_text

        except win32api.error as e:
            # Ошибка 1060 означает, что сервис не существует
            if e.winerror == 1060:
                self.helper.log_message(f"❌ Сервис 'TRBOnet.Server' не найден в системе", "ERROR")
                return False
            else:
                self.helper.log_message(f"❌ Ошибка при проверке сервиса: {e}", "ERROR")
                return False

        except ImportError:
            self.helper.log_message("⚠️ Модуль pywin32 не установлен. Используем резервный метод через sc...",
                                    "WARNING")
            return self._get_service_state_fallback()

        except Exception as e:
            self.helper.log_message(f"❌ Непредвиденная ошибка при проверке сервиса: {e}", "ERROR")
            return False

# ============================================================================
#   Функции для работы с элементами в конфигураторе
# ============================================================================

    def go_to_tab(self, tab_name: str) -> bool:
        """
            Переходит на указанную вкладку в дереве навигации.

            Args:
                tab_name: Название вкладки для перехода (например: "Database", "Users", "Settings")

            Returns:
                bool: True если переход выполнен успешно, иначе False
            """
        self.helper.log_message(f"Переход на вкладку '{tab_name}'...", "INFO")

        try:
            # Проверяем наличие главного окна
            if self.helper.main_window is None:
                self.helper.log_message("Главное окно не найдено. Попытка подключиться...", "WARNING")
                if not self.connect_to_running():
                    self.helper.log_message("Не удалось найти главное окно", "ERROR")
                    return False

            # Получаем AutomationId дерева
            tree_auto_id = self.helper.get_auto_id("tree")
            if not tree_auto_id:
                self.helper.log_message("  ❌ Ключ 'tree' не найден в AUTO_IDS", "ERROR")
                return False

            # Ищем дерево по AutomationId
            all_elements = self.helper.main_window.descendants()
            tree = None
            for elem in all_elements:
                try:
                    if hasattr(elem, 'element_info') and hasattr(elem.element_info, 'automation_id'):
                        if elem.element_info.automation_id == tree_auto_id:
                            tree = elem
                            self.helper.log_message("  ✅ Найдено дерево", "SUCCESS")
                            break
                except:
                    continue

            if not tree:
                self.helper.log_message("  ❌ Дерево не найдено", "ERROR")
                return False

            # Ищем элемент с указанным именем в дереве
            tree_descendants = tree.descendants()
            target_item = None

            for elem in tree_descendants:
                try:
                    elem_name = elem.window_text() if hasattr(elem, 'window_text') else ""
                    elem_type = elem.element_info.control_type if hasattr(elem, 'element_info') else ""

                    if elem_name == tab_name and "TreeItem" in elem_type:
                        target_item = elem
                        self.helper.log_message(f"  ✅ Найден элемент '{tab_name}'", "SUCCESS")
                        break
                except:
                    continue

            if not target_item:
                self.helper.log_message(f"  ❌ Элемент '{tab_name}' не найден", "ERROR")
                return False

            # Разворачиваем всех свернутых родителей
            def expand_parents(element):
                """Рекурсивно разворачивает всех свернутых родителей"""
                try:
                    parent = element.parent()
                    if parent and parent != element:
                        expand_pattern = parent.get_pattern("ExpandCollapse")
                        if expand_pattern:
                            current_state = expand_pattern.CurrentExpandCollapseState
                            if current_state == 0:  # Collapsed
                                self.helper.log_message(f"  Разворачиваем родителя...", "INFO")
                                expand_pattern.Expand()
                                time.sleep(0.3)
                                self.helper.log_message(f"  ✅ Родитель развернут", "SUCCESS")
                            # Рекурсивно проверяем родителя родителя
                            expand_parents(parent)
                except Exception as e:
                    pass

            # Разворачиваем всех родителей
            self.helper.log_message(f"  Проверка и разворачивание родителей...", "INFO")
            expand_parents(target_item)

            # Прокрутка до элемента при необходимости
            try:
                if hasattr(target_item, 'ensure_visible'):
                    target_item.ensure_visible()
                    time.sleep(0.3)
            except:
                pass

            # Клик по элементу
            target_item.click_input()
            time.sleep(MEDIUM_DELAY)
            self.helper.log_message(f"  ✅ Клик по '{tab_name}' выполнен", "SUCCESS")
            return True

        except Exception as e:
            self.helper.log_message(f"  ❌ Ошибка при переходе на вкладку: {e}", "ERROR")
            return False

    def set_value_drop_down_list(self, field_name: str, value: str) -> bool:
        """
        Устанавливает значение в выпадающем списке (ComboBox) по названию поля.

        Args:
            field_name: Название поля (ключ в AUTO_IDS, например: "server_type", "log_level" и т.д.)
            value: Значение для выбора в выпадающем списке

        Returns:
            bool: True если значение успешно установлено, иначе False
        """
        self.helper.log_message(f"Установка значения в выпадающем списке...", "INFO")
        self.helper.log_message(f"  Поле: '{field_name}'", "INFO")
        self.helper.log_message(f"  Значение: '{value}'", "INFO")

        try:
            # Проверяем наличие главного окна
            if self.helper.main_window is None:
                self.helper.log_message("Главное окно не найдено. Попытка подключиться...", "WARNING")
                if not self.connect_to_running():
                    self.helper.log_message("Не удалось найти главное окно", "ERROR")
                    return False

            # Вызываем метод из AppsHelper для установки значения в ComboBox
            result = self.helper.set_combo_text_by_key(
                self.helper.main_window,
                field_name,
                value,
                self.timeout
            )

            if result:
                self.helper.log_message(f"✅ Значение '{value}' успешно установлено в поле '{field_name}'", "SUCCESS")
            else:
                self.helper.log_message(f"❌ Не удалось установить значение '{value}' в поле '{field_name}'", "ERROR")

            return result

        except Exception as e:
            self.helper.log_message(f"❌ Ошибка при установке значения в выпадающем списке: {e}", "ERROR")
            return False

    def click_to(self, key: str) -> bool:
        """
        Выполняет клик по элементу по ключу из AUTO_IDS в главном окне.

        Args:
            key: Ключ в словаре AUTO_IDS (например: "btn_apply", "btn_ok", "btn_cancel" и т.д.)

        Returns:
            bool: True если клик выполнен успешно, иначе False
        """
        self.helper.log_message(f"Клик по элементу с ключом: '{key}'", "INFO")

        try:
            # Проверяем наличие главного окна
            if self.helper.main_window is None:
                self.helper.log_message("Главное окно не найдено. Попытка подключиться...", "WARNING")
                if not self.connect_to_running():
                    self.helper.log_message("Не удалось найти главное окно", "ERROR")
                    return False

            # Вызываем метод из AppsHelper для клика по элементу
            result = self.helper.click_by_key(self.helper.main_window, key, self.timeout)

            if result:
                self.helper.log_message(f"✅ Клик по элементу '{key}' выполнен успешно", "SUCCESS")
            else:
                self.helper.log_message(f"❌ Не удалось выполнить клик по элементу '{key}'", "ERROR")

            return result

        except Exception as e:
            self.helper.log_message(f"❌ Ошибка при клике по элементу: {e}", "ERROR")
            return False

    def wait_dialog_window(self, text: str) -> bool:
        """
        Ожидает появления диалогового окна с указанным текстом.

        Args:
            text: Текст для поиска в диалоговом окне

        Returns:
            bool: True если текст найден, иначе False
        """
        self.helper.log_message(f"Ожидание диалогового окна с текстом: '{text}'...", "INFO")

        try:
            # Проверяем наличие главного окна
            if self.helper.main_window is None:
                self.helper.log_message("Главное окно не найдено. Попытка подключиться...", "WARNING")
                if not self.connect_to_running():
                    self.helper.log_message("Не удалось найти главное окно", "ERROR")
                    return False

            # Вызываем метод из AppsHelper для ожидания текста в диалоге
            result = self.helper.wait_for_dialog_text(DIALOG_TEXTS[text], self.timeout)

            if result:
                self.helper.log_message(f"✅ Диалоговое окно с текстом '{text}' найдено", "SUCCESS")
            else:
                self.helper.log_message(f"❌ Диалоговое окно с текстом '{text}' не найдено", "ERROR")

            return result

        except Exception as e:
            self.helper.log_message(f"❌ Ошибка при ожидании диалогового окна: {e}", "ERROR")
            return False

    def close_dialog_window(self) -> bool:
        """
        Закрывает найденное диалоговое окно (клик по кнопке Close или OK).

        Returns:
            bool: True если диалог успешно закрыт, иначе False
        """
        self.helper.log_message(f"Закрытие диалогового окна...", "INFO")

        try:
            # Ищем все окна с заголовком "TRBOnet Enterprise"
            from pywinauto import Desktop
            desktop = Desktop(backend="uia")
            windows = desktop.windows(title_re=".*TRBOnet Enterprise.*")

            if not windows:
                self.helper.log_message("❌ Диалоговые окна не найдены", "ERROR")
                return False

            # Ищем диалоговое окно (не главное)
            dialog_window = None
            for win in windows:
                try:
                    # Ищем кнопку с текстом "OK" или "Ok"
                    buttons = win.descendants(control_type="Button")
                    for btn in buttons:
                        try:
                            btn_text = btn.window_text()
                            if btn_text in ["OK", "Ok", "ok"]:
                                btn.click_input()
                                time.sleep(0.5)
                                self.helper.log_message(f"  ✅ Клик по кнопке 'OK' выполнен", "SUCCESS")
                                self.helper.log_message(f"✅ Диалоговое окно закрыто", "SUCCESS")
                                return True
                        except:
                            continue
                except:
                    continue

            self.helper.log_message(f"❌ Не удалось закрыть диалоговое окно", "ERROR")
            return False

        except Exception as e:
            self.helper.log_message(f"❌ Ошибка при закрытии диалогового окна: {e}", "ERROR")
            return False

    def enable_feature(self, feature_key: str) -> bool:
        """
        Включает указанную функцию через чек-бокс.

        Args:
            feature_key: Ключ чек-бокса в AUTO_IDS

        Returns:
            True при успешном включении, False при ошибке
        """

        try:
            # Проверяем наличие главного окна
            if self.helper.main_window is None:
                self.helper.log_message("Главное окно не найдено. Попытка подключиться...", "WARNING")
                if not self.connect_to_running():
                    self.helper.log_message("Не удалось найти главное окно", "ERROR")
                    return False

            return self.helper.state_check_box(self.helper.main_window, feature_key, True)

        except Exception as e:
            self.helper.log_message(f"❌ Ошибка при установке состояния чек-бокса: {e}", "ERROR")
            return False

    def disable_feature(self, feature_key: str) -> bool:
        """
        Выключает указанную функцию через чек-бокс.

        Args:
            feature_key: Ключ чек-бокса в AUTO_IDS

        Returns:
            True при успешном выключении, False при ошибке
        """
        try:
            # Проверяем наличие главного окна
            if self.helper.main_window is None:
                self.helper.log_message("Главное окно не найдено. Попытка подключиться...", "WARNING")
                if not self.connect_to_running():
                    self.helper.log_message("Не удалось найти главное окно", "ERROR")
                    return False

            return self.helper.state_check_box(self.helper.main_window, feature_key, False)

        except Exception as e:
            self.helper.log_message(f"❌ Ошибка при установке состояния чек-бокса: {e}", "ERROR")
            return False

    def get_states_check_boxes(self, feature_keys: list) -> dict:
        """
        Получает состояния нескольких чек-боксов.

        Args:
            feature_keys: Список ключей чек-боксов

        Returns:
            Словарь {ключ: состояние}
        """
        try:
            # Проверяем наличие главного окна
            if self.helper.main_window is None:
                self.helper.log_message("Главное окно не найдено. Попытка подключиться...", "WARNING")
                if not self.connect_to_running():
                    self.helper.log_message("Не удалось найти главное окно", "ERROR")
                    return False

            states = {}

            for key in feature_keys:
                state = self.helper.get_check_box_state(self.helper.main_window, key)
                if state is not None:
                    states[key] = state
                else:
                    self.helper.log_message(f"⚠️ Не удалось получить состояние чек-бокса: {key}", "WARNING")
                    states[key] = None

            return states

        except Exception as e:
            self.helper.log_message(f"❌ Ошибка при получении состояния чек-бокса: {e}", "ERROR")
            return False

    def bulk_set_text(self, fields: dict) -> bool:
        """
        Заполняет несколько текстовых полей одновременно.

        Args:
            fields: Словарь {ключ_поля: значение}

        Returns:
            True если все поля заполнены успешно, False если хотя бы одно не заполнено
        """
        success = True

        for key, value in fields.items():
            self.helper.log_message(f"Заполнение поля: {key} -> {value}", "INFO")
            if not self.helper.set_text_main(key, value):
                self.helper.log_message(f"❌ Ошибка заполнения поля: {key}", "ERROR")
                success = False
                break

        return success

    def check_progress_upgrade_database(self, timeout: int = 60) -> bool:
        """
        Проверяет появление и автоматическое закрытие окна "Database upgrade in progress".
        Окно является дочерним для главного окна приложения.

        Args:
            timeout: Максимальное время ожидания в секундах (по умолчанию 60 сек)

        Returns:
            bool: True если окно появилось и закрылось в течение таймаута, иначе False
        """
        self.helper.log_message(f"Проверка окна обновления базы данных...", "INFO")
        self.helper.log_message(f"  Таймаут: {timeout} сек.", "INFO")

        try:
            import time

            # Проверяем наличие главного окна
            if self.helper.main_window is None:
                self.helper.log_message("Главное окно не найдено. Попытка подключиться...", "WARNING")
                if not self.connect_to_running():
                    self.helper.log_message("Не удалось найти главное окно", "ERROR")
                    return False

            start_time = time.time()

            # Шаг 1: Ожидание появления дочернего окна
            self.helper.log_message(f"  Ожидание появления окна обновления...", "INFO")
            window_found = False
            found_window = None

            while time.time() - start_time < timeout:
                try:
                    # Ищем дочернее окно внутри главного окна
                    # Получаем все дочерние окна главного окна
                    child_windows = self.helper.main_window.children(control_type="Window")

                    for child in child_windows:
                        try:
                            # Проверяем по AutomationId
                            if hasattr(child, 'element_info') and hasattr(child.element_info, 'automation_id'):
                                if child.element_info.automation_id == "DbUpdateForm":
                                    found_window = child
                                    window_found = True
                                    self.helper.log_message(f"  ✅ Окно обновления появилось (по AutomationId)", "SUCCESS")
                                    break

                            # Проверяем по имени окна
                            child_text = child.window_text()
                            if child_text == "Database upgrade in progress":
                                found_window = child
                                window_found = True
                                self.helper.log_message(f"  ✅ Окно обновления появилось (по имени)", "SUCCESS")
                                break

                        except Exception as e:
                            continue

                    if window_found:
                        break

                except Exception as e:
                    self.helper.log_message(f"  Ошибка при поиске дочернего окна: {e}", "WARNING")

                time.sleep(0.5)

            if not window_found:
                self.helper.log_message(f"  ❌ Окно обновления не появилось в течение {timeout} сек.", "ERROR")
                return False

            # Шаг 2: Ожидание закрытия окна
            self.helper.log_message(f"  Ожидание закрытия окна обновления...", "INFO")
            window_closed = False
            elapsed = time.time() - start_time
            remaining_time = timeout - elapsed

            if remaining_time <= 0:
                remaining_time = 1

            wait_start = time.time()

            while time.time() - wait_start < remaining_time:
                try:
                    # Проверяем, существует ли еще дочернее окно
                    still_exists = False
                    child_windows = self.helper.main_window.children(control_type="Window")

                    for child in child_windows:
                        try:
                            # Проверяем по AutomationId
                            if hasattr(child, 'element_info') and hasattr(child.element_info, 'automation_id'):
                                if child.element_info.automation_id == "DbUpdateForm":
                                    still_exists = True
                                    break

                            # Проверяем по имени
                            child_text = child.window_text()
                            if child_text == "Database upgrade in progress":
                                still_exists = True
                                break
                        except:
                            continue

                    if not still_exists:
                        window_closed = True
                        self.helper.log_message(f"  ✅ Окно обновления закрылось", "SUCCESS")
                        break

                except Exception as e:
                    self.helper.log_message(f"  Ошибка при проверке закрытия окна: {e}", "WARNING")

                time.sleep(0.5)

            if not window_closed:
                self.helper.log_message(f"  ❌ Окно обновления не закрылось в течение {remaining_time:.1f} сек.", "ERROR")
                return False

            self.helper.log_message(f"✅ Окно обновления базы данных успешно появилось и закрылось", "SUCCESS")
            return True

        except Exception as e:
            self.helper.log_message(f"❌ Ошибка при проверке окна обновления базы данных: {e}", "ERROR")
            return False