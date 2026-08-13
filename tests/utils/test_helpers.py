"""
test/utils/test_helpers.py - Утилиты для тестов

Содержит общие функции для:
- Запуска внешних скриптов
- Работы со скриншотами
- Форматирования отчетов
- Универсального экранирования путей
"""

import os
import sys
import subprocess
import time
import json
import tempfile
import io
from typing import Optional, Tuple, Dict, Any, Callable, List
from datetime import datetime

import allure


class TestHelper:
    """
    Класс-помощник для тестов.
    Содержит общие методы для запуска скриптов, создания скриншотов и т.д.
    """
    __test__ = False

    def __init__(self):
        # Исправляем путь к корню проекта
        # test_helpers.py находится в tests/utils/
        # Поднимаемся на два уровня вверх до корня проекта
        self.project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.core_dir = os.path.join(self.project_dir, "core_desktop")
        self.logs_dir = os.path.join(self.project_dir, "logs")
        self.screenshots_dir = os.path.join(self.project_dir, "screenshots")

        # Создаем папки если их нет
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.screenshots_dir, exist_ok=True)

        # Логируем пути для отладки
        allure.attach(
            f"""
            Пути TestHelper:
            - project_dir: {self.project_dir}
            - core_dir: {self.core_dir}
            - logs_dir: {self.logs_dir}
            - screenshots_dir: {self.screenshots_dir}
            """,
            name="Пути TestHelper",
            attachment_type=allure.attachment_type.TEXT
        )

    # ========================================================================
    # УНИВЕРСАЛЬНОЕ ЭКРАНИРОВАНИЕ ПУТЕЙ
    # ========================================================================

    def _is_path_arg(self, arg: str) -> bool:
        """
        Проверяет, является ли аргумент путем (содержит обратные слеши или начинается с \\)
        """
        if not isinstance(arg, str):
            return False
        return "\\" in arg or arg.startswith("\\\\") or "/" in arg

    def _escape_arg(self, arg: str) -> str:
        """
        Универсальное экранирование аргумента.
        - Экранирует обратные слеши для Windows
        - Добавляет кавычки если есть пробелы или спецсимволы
        """
        if not isinstance(arg, str):
            return str(arg)

            # Добавляем кавычки только если есть пробелы или спецсимволы
        if " " in arg or "&" in arg or "(" in arg or ")" in arg:
            return f'"{arg}"'

        return arg

    def _escape_args(self, args: List[str]) -> List[str]:
        """
        Экранирует все аргументы, которые являются путями.
        """
        return [self._escape_arg(arg) for arg in args]

    # ========================================================================
    # ФОРМИРОВАНИЕ АРГУМЕНТОВ ДЛЯ СКРИПТОВ
    # ========================================================================

    def get_script_args(self, script_name: str, config: dict = None) -> list:
        """
        Возвращает аргументы для скрипта на основе конфига.
        """
        if not config:
            return []

        version = config.get("build_version", "")

        args_map = {
            "deinstall.py": [version] if version else [],
            "download_build.py": [version] if version else [],
            "install.py": [version] if version else [],
            "db_restore_network.py": [
                "--zip", config.get("zip_path", ""),
                "--db", config.get("db_name", ""),
                "--data-path", config.get("data_path", "C:\\Database_Backups"),
                "--server", config.get("sql_server", "localhost"),
                "--auth", config.get("auth_type", "sql"),
                "--user", config.get("sql_user", "sa"),
                "--password", config.get("sql_password", "trbonet.com")
            ] if config.get("zip_path") and config.get("db_name") else []
        }

        return args_map.get(script_name, [])

    # ========================================================================
    # УНИВЕРСАЛЬНЫЙ ЗАПУСК СКРИПТОВ
    # ========================================================================

    def run_script(self, script_name: str, config: dict = None,
                   args: list = None, timeout: int = 600,
                   step_name: str = None) -> Tuple[int, str, str]:
        """
        Универсальный запуск Python скрипта с автоматическим экранированием путей.

        Args:
            script_name: Имя скрипта (deinstall.py, download_build.py и т.д.)
            config: Конфигурация теста для автоматической подстановки аргументов
            args: Список аргументов (если указан, переопределяет автоматические)
            timeout: Таймаут в секундах
            step_name: Название шага для Allure

        Returns:
            Tuple[int, str, str]: (returncode, stdout, stderr)
        """
        script_path = os.path.join(self.core_dir, script_name)

        # Проверяем, что скрипт существует
        if not os.path.exists(script_path):
            error_msg = f"❌ Скрипт не найден: {script_path}"
            allure.attach(error_msg, name="Ошибка", attachment_type=allure.attachment_type.TEXT)
            raise FileNotFoundError(error_msg)

        # Если args не переданы, пытаемся получить из конфига
        if args is None and config is not None:
            args = self.get_script_args(script_name, config)
        elif args is None:
            args = []

        # УНИВЕРСАЛЬНОЕ ЭКРАНИРОВАНИЕ: обрабатываем все аргументы
        escaped_args = self._escape_args(args)

        # Формируем команду как строку для shell=True
        cmd_parts = [sys.executable, script_path] + escaped_args
        cmd = cmd_parts

        step_name = step_name or f"Запуск {script_name}"

        with allure.step(step_name):
            # Логируем ДО и ПОСЛЕ экранирования для отладки
            allure.attach(
                f"""
                Путь к скрипту: {script_path}
                Существует: {os.path.exists(script_path)}
                Исходные аргументы: {args}
                Экранированные аргументы: {escaped_args}
                Полная команда: {cmd}
                """,
                name="Экранирование аргументов",
                attachment_type=allure.attachment_type.TEXT
            )

            allure.attach(
                f"Таймаут: {timeout} сек. ({timeout//60} мин.)",
                name="Параметры запуска",
                attachment_type=allure.attachment_type.TEXT
            )

            try:
                start_time = time.time()

                # Используем shell=True для правильной обработки Windows путей
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    encoding='utf-8',
                    errors='replace',
                    #shell=True
                )

                elapsed = time.time() - start_time

                # Логируем вывод
                if result.stdout:
                    stdout_preview = result.stdout[:5000] + ("..." if len(result.stdout) > 5000 else "")
                    allure.attach(
                        stdout_preview,
                        name=f"stdout ({elapsed:.1f} сек.)",
                        attachment_type=allure.attachment_type.TEXT
                    )
                if result.stderr:
                    stderr_preview = result.stderr[:5000] + ("..." if len(result.stderr) > 5000 else "")
                    allure.attach(
                        stderr_preview,
                        name="stderr",
                        attachment_type=allure.attachment_type.TEXT
                    )

                if result.returncode == 0:
                    allure.attach(
                        f"✅ Скрипт выполнен успешно за {elapsed:.1f} сек.",
                        name="Результат",
                        attachment_type=allure.attachment_type.TEXT
                    )
                else:
                    allure.attach(
                        f"❌ Скрипт завершился с кодом {result.returncode}",
                        name="Результат",
                        attachment_type=allure.attachment_type.TEXT
                    )
                    self.take_screenshot(f"Ошибка_{script_name}")

                return result.returncode, result.stdout, result.stderr

            except subprocess.TimeoutExpired:
                error_msg = f"⏱️ Таймаут {timeout} сек. превышен"
                allure.attach(error_msg, name="Ошибка", attachment_type=allure.attachment_type.TEXT)
                self.take_screenshot(f"Таймаут_{script_name}")
                raise TimeoutError(error_msg)

            except Exception as e:
                error_msg = f"❌ Ошибка: {e}"
                allure.attach(error_msg, name="Ошибка", attachment_type=allure.attachment_type.TEXT)
                self.take_screenshot(f"Исключение_{script_name}")
                raise

    # ========================================================================
    # ОЖИДАНИЕ УСЛОВИЙ С ПРОГРЕССОМ
    # ========================================================================

    def wait_for_condition(self,
                          condition_func: Callable[[], bool],
                          timeout: int = 3600,
                          check_interval: int = 30,
                          step_name: str = "Ожидание условия",
                          progress_message: str = "Ожидание завершения...") -> bool:
        """
        Универсальная функция ожидания с прогрессом.

        Args:
            condition_func: Функция, которая возвращает True когда условие выполнено
            timeout: Максимальное время ожидания в секундах
            check_interval: Интервал проверки в секундах
            step_name: Название шага для Allure
            progress_message: Сообщение о прогрессе

        Returns:
            bool: True если условие выполнено в течение таймаута
        """
        with allure.step(step_name):
            allure.attach(
                f"Максимальное время: {timeout} сек. ({timeout//60} мин.)",
                name="Параметры ожидания",
                attachment_type=allure.attachment_type.TEXT
            )
            allure.attach(
                f"Интервал проверки: {check_interval} сек.",
                name="Интервал",
                attachment_type=allure.attachment_type.TEXT
            )

            start_time = time.time()
            elapsed = 0
            last_log_time = 0

            while elapsed < timeout:
                try:
                    if condition_func():
                        elapsed_time = time.time() - start_time
                        allure.attach(
                            f"✅ Условие выполнено за {elapsed_time:.1f} сек.",
                            name="Результат",
                            attachment_type=allure.attachment_type.TEXT
                        )
                        return True
                except Exception as e:
                    allure.attach(
                        f"Ошибка при проверке условия: {e}",
                        name="Предупреждение",
                        attachment_type=allure.attachment_type.TEXT
                    )

                # Логируем прогресс каждые 30 секунд
                current_time = time.time()
                if current_time - last_log_time >= 30:
                    elapsed = current_time - start_time
                    remaining = timeout - elapsed
                    allure.attach(
                        f"{progress_message}\n"
                        f"  Прошло: {elapsed:.0f} сек. ({elapsed//60:.0f} мин.)\n"
                        f"  Осталось: {remaining:.0f} сек. ({remaining//60:.0f} мин.)",
                        name=f"Прогресс {elapsed//60:.0f} мин.",
                        attachment_type=allure.attachment_type.TEXT
                    )
                    last_log_time = current_time
                    self.take_screenshot(f"Ожидание_{elapsed//60}мин")

                time.sleep(check_interval)
                elapsed = time.time() - start_time

            allure.attach(
                f"❌ Таймаут {timeout} сек. ({timeout//60} мин.) истек",
                name="Результат",
                attachment_type=allure.attachment_type.TEXT
            )
            self.take_screenshot("Таймаут_ожидания")
            return False

    # ========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ========================================================================

    def take_screenshot(self, name: str = "screenshot") -> None:
        """
        Делает скриншот экрана и прикрепляет к Allure отчету.

        Фикс: сохраняет скриншот как валидный PNG файл.
        """
        try:
            import pyautogui
            from PIL import Image
            import io

            # Делаем скриншот
            screenshot = pyautogui.screenshot()

            # Сохраняем в буфер как PNG
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            png_data = buffer.getvalue()

            # Прикрепляем к Allure как PNG
            allure.attach(
                png_data,
                name=name,
                attachment_type=allure.attachment_type.PNG
            )

            # Дополнительно сохраняем в папку screenshots для ручного просмотра
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{name.replace(' ', '_')}.png"
            filepath = os.path.join(self.screenshots_dir, filename)

            # Сохраняем в файл
            screenshot.save(filepath, format='PNG')

            # Прикрепляем путь к файлу в Allure
            allure.attach(
                f"Скриншот сохранён: {filepath}",
                name=f"Путь к {name}",
                attachment_type=allure.attachment_type.TEXT
            )

        except ImportError as e:
            allure.attach(
                f"Библиотека не установлена: {e}\n"
                "Установите: pip install pyautogui pillow",
                name="Ошибка скриншота",
                attachment_type=allure.attachment_type.TEXT
            )
        except Exception as e:
            allure.attach(
                f"Ошибка при создании скриншота: {e}",
                name="Ошибка скриншота",
                attachment_type=allure.attachment_type.TEXT
            )

    @staticmethod
    def take_screenshot_of_element(element, name: str = "screenshot_element") -> None:
        """
        Делает скриншот конкретного элемента (из pywinauto) и прикрепляет к Allure.

        Args:
            element: Элемент pywinauto (window, control и т.д.)
            name: Имя скриншота для Allure
        """
        try:
            from PIL import ImageGrab
            import io

            # Получаем координаты элемента
            rect = element.rectangle()

            # Делаем скриншот области
            screenshot = ImageGrab.grab(bbox=(
                rect.left,
                rect.top,
                rect.right,
                rect.bottom
            ))

            # Сохраняем в буфер как PNG
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            png_data = buffer.getvalue()

            # Прикрепляем к Allure
            allure.attach(
                png_data,
                name=name,
                attachment_type=allure.attachment_type.PNG
            )

        except Exception as e:
            allure.attach(
                f"Ошибка при создании скриншота элемента: {e}",
                name="Ошибка скриншота элемента",
                attachment_type=allure.attachment_type.TEXT
            )

    @staticmethod
    def log_step(title: str, content: str, attachment_type=allure.attachment_type.TEXT):
        """Логирует шаг в Allure отчет."""
        with allure.step(title):
            allure.attach(content, name=title, attachment_type=attachment_type)

    @staticmethod
    def attach_json(data: Dict[str, Any], name: str = "Данные"):
        """Прикрепляет JSON данные к отчету."""
        allure.attach(
            json.dumps(data, indent=2, ensure_ascii=False),
            name=name,
            attachment_type=allure.attachment_type.JSON
        )


# Создаем глобальный экземпляр для удобства
test_helper = TestHelper()