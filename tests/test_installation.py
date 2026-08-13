"""
test_installation.py - Тест миграции к релиз-кандидату
"""

import time
import pytest
import allure
from typing import Dict, Any
from core_desktop.config_auto_ids import DIALOG_TEXTS

from tests.utils.test_helpers import test_helper


@allure.epic("Миграция к релиз-кандидату")
@allure.feature("Полный цикл установки и настройки")
@allure.story("Миграция TRBOnet")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.timeout(1800)
class TestMigration:
    """Тесты миграции TRBOnet."""

    # ========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ - ШАГИ
    # ========================================================================

    def step_uninstall(self, test_config: Dict[str, Any], helper) -> bool:
        """Шаг 1: Удаление существующей версии."""
        with allure.step("🗑️ Удаление существующей версии"):
            uninstall_mode = test_config.get("uninstall_mode", "auto")
            args = []

            if uninstall_mode == "version":
                args = [test_config.get("build_version", "")]
            elif uninstall_mode == "force":
                args = ["--force"]

            returncode, _, _ = helper.run_script(
                "deinstall.py",
                args=args,
                timeout=300,
                step_name="Удаление TRBOnet"
            )
            assert returncode == 0, "Удаление завершилось с ошибкой"
            return True

    def step_download(self, test_config: Dict[str, Any], helper) -> bool:
        """Шаг 2: Скачивание сборки."""
        with allure.step("📥 Скачивание сборки"):
            returncode, _, _ = helper.run_script(
                "download_build.py",
                config=test_config,
                timeout=900,
                step_name=f"Скачивание версии {test_config['build_version']}"
            )
            assert returncode == 0, "Скачивание завершилось с ошибкой"
            return True

    def step_install(self, test_config: Dict[str, Any], helper) -> bool:
        """Шаг 3: Установка TRBOnet."""
        with allure.step("⚙️ Установка TRBOnet"):
            returncode, _, _ = helper.run_script(
                "install.py",
                config=test_config,
                timeout=900,
                step_name=f"Установка версии {test_config['build_version']}"
            )
            assert returncode == 0, "Установка завершилась с ошибкой"
            return True

    def step_restore_database(self, test_config: Dict[str, Any], helper) -> bool:
        """Шаг 4: Восстановление базы данных."""
        restore_timeout = test_config.get("db_restore_timeout", 3600)

        with allure.step(f"💾 Восстановление базы данных (таймаут {restore_timeout // 60} мин.)"):
            # Логируем аргументы для отладки
            allure.attach(
                f"""
                Аргументы для db_restore_network.py:
                --zip: {test_config['zip_path']}
                --db: {test_config['db_name']}
                --data-path: {test_config['data_path']}
                --server: {test_config['sql_server']}
                --auth: {test_config['auth_type']}
                --user: {test_config['sql_user']}
                --password: {test_config['sql_password']}
                """,
                name="Параметры восстановления БД",
                attachment_type=allure.attachment_type.TEXT
            )

            returncode, stdout, stderr = helper.run_script(
                "db_restore_network.py",
                config=test_config,
                timeout=restore_timeout,
                step_name=f"Восстановление БД {test_config['db_name']}"
            )

            # Дополнительное логирование вывода
            allure.attach(stdout, name="stdout восстановления", attachment_type=allure.attachment_type.TEXT)
            allure.attach(stderr, name="stderr восстановления", attachment_type=allure.attachment_type.TEXT)

            assert returncode == 0, f"Восстановление БД завершилось с ошибкой. stdout: {stdout}, stderr: {stderr}"
            return True

    def step_configure_server(self, test_config: Dict[str, Any], configurator, helper) -> bool:
        """Шаг 5: Настройка конфигурации сервера."""
        with allure.step("🔧 Настройка конфигурации сервера"):
            # 5.1 Открытие приложения
            with allure.step("Открытие приложения"):
                assert configurator.open(), "Не удалось открыть приложение"
                helper.take_screenshot("Приложение_открыто")

            # 5.2 Переход на вкладку Database
            with allure.step("Переход на вкладку Database"):
                assert configurator.go_to_tab("Database"), "Не удалось перейти на вкладку Database"
                helper.take_screenshot("Вкладка_Database")

            # 5.3 Выбор SQL сервера
            with allure.step("Выбор SQL сервера"):
                assert configurator.set_value_drop_down_list("dd_list_server", test_config['sql_server']), "Не удалось выбрать SQL сервер"
                helper.take_screenshot("Выбор_SQL_сервера")

            # 5.4 Выбор базы данных
            with allure.step("Выбор базы данных"):
                assert configurator.set_value_drop_down_list("dd_list_database", test_config['db_name']), "Не удалось выбрать базу данных"
                helper.take_screenshot("Выбор_базы_данных")

            # 5.5 Выбор типа аутентификации
            with allure.step("Выбор типа аутентификации"):
                assert configurator.set_value_drop_down_list("dd_list_authorization", "SQL Server"), "Не удалось выбрать тип аутентификации"
                helper.take_screenshot("Выбор_типа_аутентификации")

            # 5.6 Ввод логина и пароля
            with allure.step("Ввод логина и пароля"):
                assert configurator.bulk_set_text({"edit_login": test_config['sql_user'], "edit_password": test_config['sql_password']}), "Не удалось ввести логин или пароль"
                helper.take_screenshot("Ввод_логина_и_пароля")

            return True

    def step_upgrade_database(self, test_config: Dict[str, Any], configurator, helper) -> bool:
        """Шаг 6: Обновление базы данных."""
        upgrade_timeout = test_config.get("db_upgrade_timeout", 1800)

        with allure.step(f"🔄 Обновление базы данных (таймаут {upgrade_timeout // 60} мин.)"):
            # 6.1 Нажатие кнопки обновления
            with allure.step("Нажатие кнопки обновления"):
                assert configurator.click_to("btn_upgrade_database"), "Не удалось нажать кнопку обновления базы данных"
                helper.take_screenshot("Нажата_кнопка_обновления")

            # 6.2 Ожидание обновления базы данных
            with allure.step("Ожидание обновления базы данных"):
                assert configurator.check_progress_upgrade_database(upgrade_timeout), "Не удалось обновить базу данных"
                helper.take_screenshot("Процесс_обновления_базы_данных")

            # 6.3 Ожидание диалогового окна
            with allure.step("Ожидание диалогового окна"):
                assert configurator.wait_dialog_window("upgrade_db_success"), "Не появилось подтверждение обновления базы данных"
                helper.take_screenshot("Диалоговое_окно_успешного_обновления")

            # 6.4 Закрытие диалогового окна
            with allure.step("Закрытие диалогового окна"):
                assert configurator.close_dialog_window(), "Не удалось закрыть диалоговое окно"
                helper.take_screenshot("Диалог_закрыт")

            return True

    def step_start_server(self, test_config: Dict[str, Any], configurator, helper) -> bool:
        """Шаг 7: Запуск сервера."""
        with allure.step("🚀 Запуск сервера"):
            # 7.1 Переход на вкладку Service
            with allure.step("Переход на вкладку Service"):
                assert configurator.go_to_tab("Service"), "Не удалось перейти на вкладку Service"
                helper.take_screenshot("Вкладка_Service")

            # 7.2 Устанавливаем сервис
            with allure.step("Устанавливаем сервис"):
                assert configurator.click_to("btn_install_service"), "Не удалось нажать на кнопку Install Service"
                helper.take_screenshot("Установка_Service")

            # 7.3 Сохраняем изменения и делаем рестарт
            with allure.step("Сохраняем изменения и делаем рестарт"):
                assert configurator.click_to("lk_save_and_apply"), "Не удалось нажать на ссылку Save changes and restart service"
                helper.take_screenshot("Сохранения_и_рестарт")

            # 7.4 Проверка состояния сервиса
            with allure.step("Проверка состояния сервиса"):
                state = configurator.get_service_state()
                assert state is not False, "Сервис TRBOnet.Server не найден"
                assert state == "running", f"Сервис не запущен. Текущее состояние: {state}"

            return True

    def log_final_results(self, test_passed: bool, error_message: str, test_config: Dict[str, Any], configurator, helper):
        """Логирует итоговые результаты теста."""
        status = "✅ УСПЕШНО" if test_passed else f"❌ ПАДЕНИЕ: {error_message}"

        helper.log_step(
            f"📊 ИТОГИ ТЕСТА: {status}",
            f"""
            Статус: {status}
            Версия: {test_config['build_version']}
            База данных: {test_config["db_name"]}
            Режим удаления: {test_config.get("uninstall_mode", "auto")}
            Конфигуратор: {"открыт" if configurator.is_running() else "закрыт"}
            Время восстановления: {test_config.get("db_restore_timeout", 3600) // 60} мин.
            Время обновления: {test_config.get("db_upgrade_timeout", 1800) // 60} мин.
            """
        )

    # ========================================================================
    # ТЕСТЫ - ПОЛНЫЙ ЦИКЛ
    # ========================================================================

    @allure.title("Миграция к релиз-кандидату")
    def test_migration_to_release_candidate(self, test_config: Dict[str, Any], configurator, helper):
        """Полный цикл миграции TRBOnet."""
        allure.dynamic.title(f"Миграция к релиз-кандидату {test_config['build_version']}")
        helper.attach_json(test_config, "Параметры теста")

        test_passed = False
        error_message = None

        try:
            self.step_uninstall(test_config, helper)
            self.step_download(test_config, helper)
            self.step_install(test_config, helper)
            self.step_restore_database(test_config, helper)
            self.step_configure_server(test_config, configurator, helper)
            self.step_upgrade_database(test_config, configurator, helper)
            self.step_start_server(test_config, configurator, helper)

            test_passed = True

        except Exception as e:
            error_message = str(e)
            helper.take_screenshot("Ошибка_в_тесте")
            raise

        finally:
            self.log_final_results(test_passed, error_message, test_config, configurator, helper)

    # ========================================================================
    # ТЕСТЫ - ОТДЕЛЬНЫЕ ШАГИ
    # ========================================================================

    @allure.title("Шаг 1: Удаление TRBOnet")
    def test_step_uninstall(self, test_config: Dict[str, Any], helper):
        """Тест только удаления."""
        self.step_uninstall(test_config, helper)

    @allure.title("Шаг 2: Скачивание сборки")
    def test_step_download(self, test_config: Dict[str, Any], helper):
        """Тест только скачивания."""
        self.step_download(test_config, helper)

    @allure.title("Шаг 3: Установка TRBOnet")
    def test_step_install(self, test_config: Dict[str, Any], helper):
        """Тест только установки."""
        self.step_install(test_config, helper)

    @allure.title("Шаг 4: Восстановление базы данных")
    def test_step_restore_database(self, test_config: Dict[str, Any], helper):
        """Тест только восстановления БД."""
        self.step_restore_database(test_config, helper)

    @allure.title("Шаг 5: Настройка конфигурации сервера")
    def test_step_configure_server(self, test_config: Dict[str, Any], configurator, helper):
        """Тест только настройки конфигуратора."""
        self.step_configure_server(test_config, configurator, helper)

    @allure.title("Шаг 6: Обновление базы данных")
    def test_step_upgrade_database(self, test_config: Dict[str, Any], configurator, helper):
        """Тест только обновления БД."""
        # Предварительно нужно открыть приложение и перейти на вкладку Database
        with allure.step("Подготовка: открытие приложения"):
            assert configurator.open(), "Не удалось открыть приложение"
            helper.take_screenshot("Приложение_открыто")

        with allure.step("Подготовка: переход на вкладку Database"):
            assert configurator.go_to_tab("Database"), "Не удалось перейти на вкладку Database"
            helper.take_screenshot("Вкладка_Database")

        self.step_upgrade_database(test_config, configurator, helper)

    @allure.title("Шаг 7: Запуск сервера")
    def test_step_start_server(self, test_config: Dict[str, Any], configurator, helper):
        """Тест только запуска сервера."""
        # Предварительно нужно открыть приложение
        with allure.step("Подготовка: открытие приложения"):
            assert configurator.open(), "Не удалось открыть приложение"
            helper.take_screenshot("Приложение_открыто")

        self.step_start_server(test_config, configurator, helper)

    # ========================================================================
    # ТЕСТЫ - ГРУППЫ ШАГОВ
    # ========================================================================

    @allure.title("Миграция (удаление + скачивание + установка)")
    def test_install_flow(self, test_config: Dict[str, Any], helper):
        """Тест только установки (удаление + скачивание + установка)."""
        self.step_uninstall(test_config, helper)
        self.step_download(test_config, helper)
        self.step_install(test_config, helper)

    @allure.title("Миграция (восстановление БД + настройка)")
    def test_restore_and_configure(self, test_config: Dict[str, Any], configurator, helper):
        """Тест восстановления БД и настройки конфигуратора."""
        self.step_restore_database(test_config, helper)
        self.step_configure_server(test_config, configurator, helper)

    @allure.title("Миграция (восстановление БД + настройка + обновление БД + запуск сервера)")
    def test_configure_upgrade_start(self, test_config: Dict[str, Any], configurator, helper):
        """Тест настройки, обновления БД и запуска сервера."""
        self.step_restore_database(test_config, helper)
        self.step_configure_server(test_config, configurator, helper)
        self.step_upgrade_database(test_config, configurator, helper)
        self.step_start_server(test_config, configurator, helper)