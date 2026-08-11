"""
test_smoke_build.py - Smoke-тесты для проверки сборки TRBOnet

Структура:
1. Подготовка окружения выполняется в conftest.py (фикстура prepared_environment)
2. Тест 1: Настройка конфигуратора сервера и запуск
3. Тест 2: Smoke-тест Dispatch Console (зависит от Теста 1)
4. Тест 3: Smoke-тест TRBOnet One (зависит от Теста 1)

Тесты 2 и 3 НЕ зависят друг от друга.
"""

import time
import pytest
import allure
from typing import Dict, Any

from tests.utils.test_helpers import test_helper


# ============================================================================
# ТЕСТ 1: НАСТРОЙКА КОНФИГУРАТОРА СЕРВЕРА (SMOKE)
# ============================================================================

@allure.epic("Smoke-тестирование сборки")
@allure.feature("Настройка сервера")
@allure.story("Базовая настройка после установки")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.smoke
@pytest.mark.installation
@pytest.mark.timeout(600)
@pytest.mark.dependency(name="configure_server")
class TestConfigureServer:
    """
    Smoke-тест настройки конфигуратора сервера.
    Если этот тест падает, тесты Dispatch и One НЕ запускаются.
    """

    # ========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ - ШАГИ
    # ========================================================================

    def step_open_application(self, configurator, helper) -> None:
        """Шаг 1: Открытие приложения."""
        with allure.step("Открытие приложения"):
            assert configurator.open(), "Не удалось открыть приложение"
            helper.take_screenshot("Приложение_открыто")

    def step_go_to_database_tab(self, configurator, helper) -> None:
        """Шаг 2: Переход на вкладку Database."""
        with allure.step("Переход на вкладку Database"):
            assert configurator.go_to_tab("Database"), "Не удалось перейти на вкладку Database"
            helper.take_screenshot("Вкладка_Database")

    def step_create_database(self, configurator, test_config: Dict[str, Any], helper) -> None:
        """Шаг 3: Настройка подключения к базе данных."""
        with allure.step("Создание базы данных"):

            with allure.step("Введение имени базы данных"):
                db_name = f"TRBOnet_{test_config['build_version']}_autotest"
                assert configurator.set_value_drop_down_list(
                    "dd_list_database", db_name
                ), "Не удалось ввести имя базы данных"
                helper.take_screenshot("Ввод_имени_базы_данных")

            with allure.step("Нажатие кнопки создания баз данных"):
                assert configurator.click_to("btn_create_database"), "Не удалось нажать кнопку создания"
                helper.take_screenshot("Нажата_кнопка_создания")

            with allure.step("Ожидание диалогового окна подтверждения"):
                assert configurator.wait_dialog_window("creation_dialog"), "Не появилось подтверждение создания"
                helper.take_screenshot("Диалоговое_окно_успешного_создания")

            with allure.step("Закрытие диалогового окна"):
                assert configurator.close_dialog_window(), "Не удалось закрыть диалоговое окно"
                helper.take_screenshot("Диалог_закрыт")

    def step_start_server(self, configurator, helper) -> None:
        """Шаг 4: Запуск сервера."""
        with allure.step("Запуск сервера"):
            with allure.step("Переход на вкладку Service"):
                assert configurator.go_to_tab("Service"), "Не удалось перейти на вкладку Service"
                helper.take_screenshot("Вкладка_Service")

            with allure.step("Установка сервиса"):
                assert configurator.click_to("btn_install_service"), "Не удалось нажать Install Service"
                helper.take_screenshot("Установка_Service")

            with allure.step("Сохранение изменений и рестарт"):
                assert configurator.click_to("lk_save_and_apply"), "Не удалось нажать Save and restart"
                helper.take_screenshot("Сохранения_и_рестарт")

    def step_verify_server_ready(self, configurator, helper) -> None:
        """Шаг 6: Проверка готовности сервера."""
        with allure.step("Проверка готовности сервера"):

            with allure.step("Проверка состояния сервиса"):
                state = configurator.get_service_state()
                assert state is not False, "Сервис TRBOnet.Server не найден"
                assert state == "running", f"Сервис не запущен. Текущее состояние: {state}"
                helper.take_screenshot("Сервис_запущен")

            with allure.step("Закрытие конфигуратора"):
                assert configurator.close_by_OK(), "Не удалось закрыть конфигуратор"
                helper.take_screenshot("Закрытие_конфигуратора")

    # ========================================================================
    # ТЕСТ
    # ========================================================================

    @allure.title("Smoke: Настройка конфигуратора сервера")
    def test_configure_server(
            self,
            migration_prepared: Dict[str, Any],
            test_config: Dict[str, Any],
            configurator,
            helper
    ):
        """
        Smoke-тест настройки конфигуратора сервера.

        Зависимости:
        - Подготовленное окружение (фикстура migration_prepared)
        """
        allure.dynamic.title(f"Smoke: Настройка сервера {test_config['build_version']}")
        helper.attach_json(test_config, "Параметры теста")

        test_passed = False
        error_message = None

        try:
            # Выполнение шагов (каждый шаг сам выбрасывает исключение при ошибке)
            self.step_open_application(configurator, helper)
            self.step_go_to_database_tab(configurator, helper)
            self.step_create_database(configurator, test_config, helper)
            self.step_start_server(configurator, helper)
            self.step_verify_server_ready(configurator, helper)

            test_passed = True

        except Exception as e:
            error_message = str(e)
            helper.take_screenshot("Ошибка_настройки_сервера")
            raise  # ← Пробрасываем исключение дальше, чтобы pytest зафиксировал падение

        finally:
            helper.log_step(
                f"📊 ИТОГИ ТЕСТА: {'✅ УСПЕШНО' if test_passed else f'❌ ПАДЕНИЕ: {error_message}'}",
                f"""
                Статус: {'УСПЕШНО' if test_passed else 'ПАДЕНИЕ'}
                Версия: {test_config['build_version']}
                База данных: {test_config['db_name']}
                SQL Server: {test_config['sql_server']}
                """
            )


# ============================================================================
# ТЕСТ 2: SMOKE-ТЕСТ DISPATCH CONSOLE
# ============================================================================

@allure.epic("Smoke-тестирование сборки")
@allure.feature("Тестирование приложений")
@allure.story("Dispatch Console")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.smoke
@pytest.mark.timeout(300)
@pytest.mark.dependency(depends=["configure_server"])
class TestDispatchConsoleSmoke:
    """
    Smoke-тест Dispatch Console приложения.
    Запускается только если Тест 1 (настройка сервера) прошёл успешно.
    """

    # ========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ - ШАГИ
    # ========================================================================

    def step_open_connection_manager(self, connection_manager, helper) -> None:

        with allure.step("Открытие Dispatch Console"):
            assert connection_manager.open(), "Не удалось запустить connection manager Enterprise"
            helper.take_screenshot("Connection_manager_открытие")

    def step_check_connection_to_server(self, connection_manager, helper) -> None:

        with allure.step("Подключение к серверу"):
            connection_manager.set_username("admin")
            connection_manager.set_password("admin")
            connection_manager.connect_to_server()
            time.sleep(5)
            assert not connection_manager.get_state_cm_window(), "Окно Connection manager не закрылось"
            helper.take_screenshot("Connection_manager_закрытие")

    def step_open_dispatch_console(self, console, helper) -> None:

        with allure.step("Открытие Dispatch Console"):
            assert console.get_state_console_window(), "Окно консоли Enterprise не появилось"
            helper.take_screenshot("Enterprise_открытие")

    def step_find_voice_box(self, console, helper) -> None:

        with allure.step("Поиск бокса Intercom"):
            assert console.find_voice_box("Intercom", "All Call"), "Бокс Intercom не найден"

    def step_make_call(self, console, helper) -> None:

        with allure.step("Вызов All Call"):
            assert console.press_ptt(), "Не удалось нажать PTT"
            helper.take_screenshot("Нажатие_PTT")

    def step_check_box_state(self, console, helper) -> None:

        with allure.step("Проверка состояния бокса"):
            success_info, data = console.get_voice_box_info(call_type="All Call", call_info="All", call_sender="Administrator")
            success_color = (console.get_voice_box_color() == "GREEN")
            assert success_info and success_color, "Состояние бокса отображается неверно"
            helper.take_screenshot("Состояние_бокса")

    def step_call_end(self, console, helper) -> None:

        with allure.step("Завершаем вызов All Call"):
            assert console.unpress_ptt(), "Не удалось отжать PTT"
            helper.take_screenshot("Отжатие_PTT")

    def step_close_console(self, console, helper) -> None:

        with allure.step("Закрываем консоль"):
            assert console.close(), "Консоль не закрылась"
            helper.take_screenshot("Консоль_закрытие")

    # ========================================================================
    # ТЕСТ
    # ========================================================================

    @allure.title("Smoke: Тестирование Dispatch Console")
    def test_dispatch_console_smoke(
            self,
            migration_prepared: Dict[str, Any],
            test_config: Dict[str, Any],
            connection_manager,
            console,
            helper
    ):
        """
        Smoke-тест Dispatch Console приложения.

        Зависимости:
        - Подготовленное окружение (фикстура migration_prepared)
        - Успешный тест configure_server (pytest-dependency)
        """
        allure.dynamic.title(f"Smoke: Dispatch Console {test_config['build_version']}")
        helper.attach_json(test_config, "Параметры теста")

        test_passed = False
        error_message = None

        try:
            # Выполнение шагов
            self.step_open_connection_manager(connection_manager, helper)
            self.step_check_connection_to_server(connection_manager, helper)
            self.step_open_dispatch_console(console,  helper)
            self.step_find_voice_box(console,  helper)
            self.step_make_call(console,  helper)
            self.step_check_box_state(console,  helper)
            self.step_call_end(console,  helper)
            self.step_close_console(console,  helper)

            test_passed = True

        except Exception as e:
            error_message = str(e)
            helper.take_screenshot("Ошибка_Dispatch_Smoke")
            raise

        finally:
            helper.log_step(
                f"📊 ИТОГИ ТЕСТА: {'✅ УСПЕШНО' if test_passed else f'❌ ПАДЕНИЕ: {error_message}'}",
                f"Статус: {'УСПЕШНО' if test_passed else 'ПАДЕНИЕ'}\nВерсия: {test_config['build_version']}"
            )


# ============================================================================
# ТЕСТ 3: SMOKE-ТЕСТ TRBONET ONE
# ============================================================================

@allure.epic("Smoke-тестирование сборки")
@allure.feature("Тестирование приложений")
@allure.story("TRBOnet One")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.smoke
@pytest.mark.timeout(300)
@pytest.mark.dependency(depends=["configure_server"])
class TestTRBOnetOneSmoke:
    """
    Smoke-тест TRBOnet One приложения.
    Запускается только если Тест 1 (настройка сервера) прошёл успешно.
    НЕ зависит от Теста 2 (Dispatch Console).
    """

    # ========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ - ШАГИ (заполнишь сама)
    # ========================================================================

    def step_open_connection_manager(self, connection_manager_one) -> None:
        """Шаг 1: Открытие Connection Manager для TRBOnet One."""
        with allure.step("Открытие Connection Manager TRBOnet One"):
            assert connection_manager_one.open(), "Не удалось запустить Connection Manager TRBOnet One"
            test_helper.take_screenshot("Connection_Manager_One_открыт")

    def step_configure_connection(self, connection_manager_one, test_config: Dict[str, Any]) -> None:
        """Шаг 2: Настройка параметров подключения к серверу."""
        with allure.step("Настройка параметров подключения к серверу"):

            with allure.step("Установка имени пользователя"):
                assert connection_manager_one.set_username("admin"), "Не удалось установить имя пользователя"
                test_helper.take_screenshot("One_установка_пользователя")

            with allure.step("Установка пароля"):
                assert connection_manager_one.set_password("admin"), "Не удалось установить пароль"
                test_helper.take_screenshot("One_установка_пароля")

            with allure.step("Установка типа консоли TRBOnetOne"):
                assert connection_manager_one.set_console_type_one(), "Не удалось установить тип консоли TRBOnetOne"
                test_helper.take_screenshot("One_установка_типа_консоли")

    def step_connect_to_server(self, connection_manager_one) -> None:
        """Шаг 3: Подключение к серверу."""
        with allure.step("Подключение к серверу TRBOnet One"):
            assert connection_manager_one.connect_to_server(), "Не удалось подключиться к серверу"
            test_helper.take_screenshot("One_подключение_к_серверу")

    def step_wait_console_ready(self, one_console) -> None:
        """Шаг 4: Ожидание загрузки главного окна TRBOnet One."""
        with allure.step("Ожидание загрузки главного окна TRBOnet One"):
            assert one_console.get_state_console_window(), "Главное окно TRBOnet One не появилось"
            test_helper.take_screenshot("One_главное_окно_появилось")

            assert one_console.wait_for_ready(), "TRBOnet One не загрузилась полностью"
            test_helper.take_screenshot("One_загружена")

    def step_find_ptt_button(self, one_console) -> None:
        """Шаг 5: Поиск активной кнопки PTT."""
        with allure.step("Поиск активной кнопки PTT"):
            assert one_console.find_ptt_button(), "Активная кнопка PTT не найдена"
            test_helper.take_screenshot("One_PTT_найдена")

    def step_press_ptt(self, one_console) -> None:
        """Шаг 6: Нажатие кнопки PTT."""
        with allure.step("Нажатие кнопки PTT"):
            assert one_console.press_ptt(), "Не удалось нажать кнопку PTT"
            test_helper.take_screenshot("One_PTT_нажата")

    def step_check_voice_box_color(self, one_console) -> None:
        """Шаг 7: Проверка цвета Voice Box."""
        with allure.step("Проверка цвета Voice Box"):
            # Ожидаем изменение с BLUE на GREEN (таймаут 10 секунд)
            result = one_console.wait_for_color_change(
                from_color="BLUE",
                to_color="GREEN",
                timeout=10
            )

            assert result and result["success"], \
                f"Цвет не изменился с BLUE на GREEN за 10 секунд. " \
                f"Начальный: {result['initial_color'] if result else 'None'}, " \
                f"Конечный: {result['current_color'] if result else 'None'}"

            test_helper.attach_json(result, "Результат проверки цвета")
            test_helper.take_screenshot("One_цвет_изменился_на_GREEN")

    def step_press_ptt_again(self, one_console) -> None:
        """Шаг 8: Повторное нажатие PTT для завершения вызова."""
        with allure.step("Повторное нажатие PTT для завершения вызова"):
            with allure.step("Повторное нажатие PTT для завершения вызова"):
                assert one_console.press_ptt(), "Не удалось повторно нажать PTT"
                test_helper.take_screenshot("One_PTT_повторно_нажата")

                # Проверяем, что цвет вернулся на BLUE
                result = one_console.wait_for_color_change(
                    from_color="GREEN",
                    to_color="BLUE",
                    timeout=10
                )

                assert result and result["success"], \
                    f"Цвет не изменился с GREEN на BLUE за 10 секунд. " \
                    f"Начальный: {result['initial_color'] if result else 'None'}, " \
                    f"Конечный: {result['current_color'] if result else 'None'}"

                test_helper.attach_json(result, "Результат проверки возврата цвета")
                test_helper.take_screenshot("One_цвет_вернулся_на_BLUE")

    def step_close_console(self, one_console) -> None:
        """Шаг 9: Закрытие TRBOnet One."""
        with allure.step("Закрытие TRBOnet One"):
            assert one_console.close(), "Не удалось закрыть TRBOnet One"
            test_helper.take_screenshot("One_закрыта")

    # ========================================================================
    # ТЕСТ
    # ========================================================================

    @allure.title("Smoke: Тестирование TRBOnet One")
    def test_trbonet_one_smoke(
            self,
            migration_prepared: Dict[str, Any],
            test_config: Dict[str, Any],
            connection_manager_one,  # ← Фикстура из conftest.py (экземпляр ConnectionManager)
            one_console             # ← Фикстура из conftest.py (экземпляр OneConsole)
    ):
        """
        Smoke-тест TRBOnet One приложения.

        Зависимости:
        - Подготовленное окружение (фикстура migration_prepared)
        - Успешный тест configure_server (pytest-dependency)
        - НЕ зависит от теста Dispatch Console
        """
        allure.dynamic.title(f"Smoke: TRBOnet One {test_config['build_version']}")
        test_helper.attach_json(test_config, "Параметры теста")

        test_passed = False
        error_message = None

        try:
            # Выполнение шагов
            self.step_open_connection_manager(connection_manager_one)
            self.step_configure_connection(connection_manager_one, test_config)
            self.step_connect_to_server(connection_manager_one)
            self.step_wait_console_ready(one_console)
            self.step_find_ptt_button(one_console)
            self.step_press_ptt(one_console)
            self.step_check_voice_box_color(one_console)
            self.step_press_ptt_again(one_console)
            self.step_close_console(one_console)

            test_passed = True

        except Exception as e:
            error_message = str(e)
            test_helper.take_screenshot("Ошибка_One_Smoke")
            raise

        finally:
            test_helper.log_step(
                f"📊 ИТОГИ ТЕСТА: {'✅ УСПЕШНО' if test_passed else f'❌ ПАДЕНИЕ: {error_message}'}",
                f"Статус: {'УСПЕШНО' if test_passed else 'ПАДЕНИЕ'}\nВерсия: {test_config['build_version']}"
            )
