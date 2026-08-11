"""
conftest.py - Конфигурация для pytest и allure
"""

import os
import sys
import pytest
from typing import Dict, Any, Generator

# Добавляем корневую папку в PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(current_dir)
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from tests.utils.test_helpers import TestHelper, test_helper


# ============================================================================
# КОНФИГУРАЦИЯ ПО УМОЛЧАНИЮ ДЛЯ ПОДГОТОВКИ ОКРУЖЕНИЯ
# ============================================================================

DEFAULT_ENV_CONFIG = {
    "build_version": "6.5.0.9140",
    "old_version": "6.5.0.9138",
    "uninstall_mode": "auto",
    "zip_path": "C:/TRBOnet/backup.zip",
    "db_name": "TRBOnet_Enterprise",
    "data_path": "C:/Database_Backups",
    "sql_server": "localhost",
    "auth_type": "sql",
    "sql_user": "sa",
    "sql_password": "trbonet.com",
    "db_restore_timeout": 3600,
    "db_upgrade_timeout": 1800,
}


# ============================================================================
# Pytest ADDOPTIONS (РАСШИРЯЕМ СУЩЕСТВУЮЩИЕ ОПЦИИ)
# ============================================================================

def pytest_addoption(parser):
    """Добавляет кастомные опции командной строки."""
    # Существующие опции
    parser.addoption(
        "--build-version",
        action="store",
        default="6.5.0.9140",
        help="Версия TRBOnet для установки"
    )
    parser.addoption(
        "--db-name",
        action="store",
        default="TRBOnet_Enterprise",
        help="Имя базы данных"
    )
    parser.addoption(
        "--zip-path",
        action="store",
        default=r"\\server\backups\TRBOnet_Enterprise_6.5.0.9140.zip",
        help="Путь к ZIP архиву с бэкапом"
    )
    parser.addoption(
        "--sql-server",
        action="store",
        default="localhost",
        help="SQL Server"
    )
    parser.addoption(
        "--sql-user",
        action="store",
        default="sa",
        help="SQL пользователь"
    )
    parser.addoption(
        "--sql-password",
        action="store",
        default="trbonet.com",
        help="SQL пароль"
    )
    parser.addoption(
        "--data-path",
        action="store",
        default="C:\\Database_Backups",
        help="Путь для MDF/LDF файлов"
    )
    parser.addoption(
        "--auth-type",
        action="store",
        default="sql",
        choices=["sql", "windows"],
        help="Тип аутентификации SQL"
    )
    parser.addoption(
        "--uninstall-mode",
        action="store",
        default="auto",
        choices=["auto", "version", "force"],
        help="Режим удаления: auto (автоматический), version (по версии), force (принудительный)"
    )
    parser.addoption(
        "--db-restore-timeout",
        action="store",
        default=3600,
        type=int,
        help="Таймаут для восстановления БД в секундах (по умолчанию 3600 = 1 час)"
    )
    parser.addoption(
        "--db-upgrade-timeout",
        action="store",
        default=1800,
        type=int,
        help="Таймаут для обновления БД в секундах (по умолчанию 1800 = 30 мин)"
    )

    # НОВЫЕ ОПЦИИ для подготовки окружения
    parser.addoption(
        "--old-version",
        action="store",
        default="6.5.0.9138",
        help="Версия TRBOnet для удаления (старая версия)"
    )
    parser.addoption(
        "--skip-env-setup",
        action="store_true",
        default=False,
        help="Пропустить подготовку окружения (использовать уже подготовленное)"
    )


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def test_config(request) -> Dict[str, Any]:
    """Фикстура с конфигурацией из командной строки."""
    config = {
        "build_version": request.config.getoption("--build-version"),
        "db_name": request.config.getoption("--db-name"),
        "zip_path": request.config.getoption("--zip-path"),
        "sql_server": request.config.getoption("--sql-server"),
        "sql_user": request.config.getoption("--sql-user"),
        "sql_password": request.config.getoption("--sql-password"),
        "data_path": request.config.getoption("--data-path"),
        "auth_type": request.config.getoption("--auth-type"),
        "uninstall_mode": request.config.getoption("--uninstall-mode"),
        "db_restore_timeout": request.config.getoption("--db-restore-timeout"),
        "db_upgrade_timeout": request.config.getoption("--db-upgrade-timeout"),
    }

    # Добавляем старую версию из новой опции
    config["old_version"] = request.config.getoption("--old-version")
    config["skip_env_setup"] = request.config.getoption("--skip-env-setup")

    return config


@pytest.fixture(scope="session")
def helper() -> TestHelper:
    """
    Фикстура для доступа к TestHelper.

    Изменена на session scope, чтобы использоваться в prepared_environment.
    """
    return test_helper


@pytest.fixture(scope="function")
def configurator():
    """Фикстура для создания экземпляра ServerConfigurator."""
    from apps.server.configurator import ServerConfigurator
    return ServerConfigurator()


@pytest.fixture(scope="function")
def connection_manager():
    """Фикстура для создания экземпляра ConnectionManager."""
    from apps.enterprise.dispatch_console import ConnectionManager
    return ConnectionManager()


@pytest.fixture(scope="function")
def console():
    """Фикстура для создания экземпляра EnterpriseConsole."""
    from apps.enterprise.dispatch_console import EnterpriseConsole
    return EnterpriseConsole()

@pytest.fixture(scope="function")
def connection_manager_one():
    """Фикстура для создания экземпляра ConnectionManager для TRBOnet One."""
    from apps.one.one_console import ConnectionManager
    return ConnectionManager()


@pytest.fixture(scope="function")
def one_console():
    """Фикстура для создания экземпляра OneConsole."""
    from apps.one.one_console import OneConsole
    return OneConsole()


# ============================================================================
# НОВЫЕ FIXTURES - ПОДГОТОВКА ОКРУЖЕНИЯ (SESSION SCOPE)
# ============================================================================

@pytest.fixture(scope="session")
def prepared_environment(
    test_config: Dict[str, Any],
    helper: TestHelper
) -> Dict[str, Any]:
    """
    ФИКСТУРА ДЛЯ ПОДГОТОВКИ ОКРУЖЕНИЯ (SESSION SCOPE).

    Выполняет:
    1. Удаление старой версии (deinstall.py)
    2. Скачивание новой версии (download_build.py)
    3. Установка новой версии (install.py)

    Это подготовка к тестам, а не сами тесты.
    Результат кешируется на всю сессию.

    Можно пропустить через --skip-env-setup
    """
    # Если пропуск включён - возвращаем заглушку
    if test_config.get("skip_env_setup", False):
        return {
            "success": True,
            "skipped": True,
            "steps": [],
            "error": None,
            "config": test_config,
            "message": "Подготовка окружения пропущена (--skip-env-setup)"
        }

    import allure

    # Используем динамическую установку suite
    allure.dynamic.suite("Подготовка окружения")
    allure.dynamic.epic("Подготовка окружения")
    allure.dynamic.feature("Установка TRBOnet")

    result = {
        "success": False,
        "skipped": False,
        "steps": [],
        "error": None,
        "config": test_config
    }

    try:
        # ================================================================
        # ШАГ 1: УДАЛЕНИЕ СТАРОЙ ВЕРСИИ
        # ================================================================
        with allure.step("🗑️ Шаг 1: Удаление старой версии"):
            uninstall_mode = test_config.get("uninstall_mode", "auto")
            args = []

            if uninstall_mode == "version":
                args = [test_config.get("old_version", "")]
            elif uninstall_mode == "force":
                args = ["--force"]

            allure.attach(
                f"Режим удаления: {uninstall_mode}\nАргументы: {args}\nВерсия: {test_config.get('old_version', 'не указана')}",
                name="Параметры удаления",
                attachment_type=allure.attachment_type.TEXT
            )

            returncode, stdout, stderr = helper.run_script(
                "deinstall.py",
                args=args,
                timeout=300,
                step_name="Удаление TRBOnet"
            )

            allure.attach(stdout, name="stdout удаления", attachment_type=allure.attachment_type.TEXT)
            allure.attach(stderr, name="stderr удаления", attachment_type=allure.attachment_type.TEXT)

            assert returncode == 0, f"Удаление завершилось с ошибкой. stdout: {stdout}, stderr: {stderr}"

            result["steps"].append({"name": "uninstall", "status": "success"})
            helper.take_screenshot("После_удаления")

        # ================================================================
        # ШАГ 2: СКАЧИВАНИЕ НОВОЙ ВЕРСИИ
        # ================================================================
        with allure.step("📥 Шаг 2: Скачивание новой версии"):
            allure.attach(
                f"Версия для скачивания: {test_config['build_version']}",
                name="Параметры скачивания",
                attachment_type=allure.attachment_type.TEXT
            )

            returncode, stdout, stderr = helper.run_script(
                "download_build.py",
                config=test_config,
                timeout=900,
                step_name=f"Скачивание версии {test_config['build_version']}"
            )

            allure.attach(stdout, name="stdout скачивания", attachment_type=allure.attachment_type.TEXT)
            allure.attach(stderr, name="stderr скачивания", attachment_type=allure.attachment_type.TEXT)

            assert returncode == 0, f"Скачивание завершилось с ошибкой. stdout: {stdout}, stderr: {stderr}"

            result["steps"].append({"name": "download", "status": "success"})
            helper.take_screenshot("После_скачивания")

        # ================================================================
        # ШАГ 3: УСТАНОВКА НОВОЙ ВЕРСИИ
        # ================================================================
        with allure.step("⚙️ Шаг 3: Установка новой версии"):
            allure.attach(
                f"Версия для установки: {test_config['build_version']}",
                name="Параметры установки",
                attachment_type=allure.attachment_type.TEXT
            )

            returncode, stdout, stderr = helper.run_script(
                "install.py",
                config=test_config,
                timeout=900,
                step_name=f"Установка версии {test_config['build_version']}"
            )

            allure.attach(stdout, name="stdout установки", attachment_type=allure.attachment_type.TEXT)
            allure.attach(stderr, name="stderr установки", attachment_type=allure.attachment_type.TEXT)

            assert returncode == 0, f"Установка завершилась с ошибкой. stdout: {stdout}, stderr: {stderr}"

            result["steps"].append({"name": "install", "status": "success"})
            helper.take_screenshot("После_установки")

        # ================================================================
        # ВСЁ УСПЕШНО
        # ================================================================
        result["success"] = True

        allure.attach(
            f"""
✅ Подготовка окружения завершена успешно!

Выполненные шаги:
{chr(10).join(f"  - {step['name']}: {step['status']}" for step in result['steps'])}

Версия: {test_config['build_version']}
База данных: {test_config['db_name']}
SQL Server: {test_config['sql_server']}
            """,
            name="Результат подготовки окружения",
            attachment_type=allure.attachment_type.TEXT
        )

        return result

    except Exception as e:
        result["error"] = str(e)
        result["success"] = False

        allure.attach(
            f"""
❌ Ошибка при подготовке окружения!

Ошибка: {e}
Выполненные шаги:
{chr(10).join(f"  - {step['name']}: {step['status']}" for step in result['steps'])}
            """,
            name="Ошибка подготовки окружения",
            attachment_type=allure.attachment_type.TEXT
        )

        helper.take_screenshot("Ошибка_подготовки_окружения")
        pytest.fail(f"Подготовка окружения провалена: {e}")


@pytest.fixture(scope="function")
def migration_prepared(prepared_environment: Dict[str, Any]) -> Dict[str, Any]:
    """
    Фикстура-маркер, указывающая, что окружение подготовлено.
    Используется для тестов, которым нужно подготовленное окружение.

    Если подготовка была пропущена (--skip-env-setup), то просто возвращает
    словарь с prepared_environment, но без проверки успешности.
    """
    if prepared_environment.get("skipped", False):
        return prepared_environment

    assert prepared_environment["success"], "Окружение не было подготовлено"
    return prepared_environment


# ============================================================================
# РЕГИСТРАЦИЯ МАРКЕРОВ
# ============================================================================

def pytest_configure(config):
    """Регистрируем кастомные маркеры."""
    config.addinivalue_line("markers", "smoke: Тесты для проверки основных функций")
    config.addinivalue_line("markers", "regression: Регрессионные тесты")
    config.addinivalue_line("markers", "installation: Тесты установки")
    config.addinivalue_line("markers", "migration: Тесты миграции")
    config.addinivalue_line("markers", "slow: Медленные тесты")
    config.addinivalue_line("markers", "timeout: Тесты с ограничением по времени выполнения")
    config.addinivalue_line("markers", "dependency: Тесты с зависимостями между собой")


# ============================================================================
# СУЩЕСТВУЮЩИЙ ХУК (НЕ ИЗМЕНЯЕМ)
# ============================================================================

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Хук для обработки результатов теста."""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        try:
            from tests.utils.test_helpers import test_helper
            test_helper.take_screenshot("Скриншот_при_падении")
        except:
            pass