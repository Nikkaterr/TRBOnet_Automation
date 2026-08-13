"""
Оркестратор для автоматической установки TRBOnet
Управляет последовательным запуском 6-ти скриптов:
1. Удаление старой версии (deinstall.py)
2. Скачивание новой версии (download_build.py)
3. Установка новой версии (install.py)
4. Настройка сервера (configure_server.py)
5. Тестирование Dispatch Console (dispatch_console_test.py) - НЕЗАВИСИМЫЙ ТЕСТ
6. Тестирование TRBOnet One (trbonet_one_test.py) - НЕЗАВИСИМЫЙ ТЕСТ

Интеграция с Allure:
- Все шаги обёрнуты в allure.step()
- Скриншоты, логи и ошибки сохраняются как вложения
- Результаты сохраняются в папку allure-results/
- Автоматическая генерация HTML-отчёта после выполнения
- Очистка старых результатов перед каждым запуском
- Тесты 5-6 выполняются даже при ошибках (независимые)

Использование:
    python orchestrator.py --old-version 6.5.0.9138 --new-version 6.5.0.9140
    python orchestrator.py -o 6.5.0.9138 -n 6.5.0.9140
    python orchestrator.py  # использует значения по умолчанию
"""

import os
import sys
import time
import subprocess
import json
import argparse
import uuid
import shutil
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from enum import Enum

import fix_encoding  # noqa

# ============================================================================
# ИМПОРТ КОНФИГУРАЦИИ
# ============================================================================

from config import BUILD_PATH, SERVER_EXE_PATH, PRODUCT_CODE, APPS_TO_CHECK, INSTALL_OPTION, SILENT_INSTALL

# ============================================================================
# ALLURE ИМПОРТ И НАСТРОЙКА
# ============================================================================

try:
    import allure
    from allure_commons.types import AttachmentType
    ALLURE_AVAILABLE = True
except ImportError:
    ALLURE_AVAILABLE = False
    print("⚠️  Библиотека allure-python-commons не установлена.")
    print("   Установите: pip install allure-python-commons")
    print("   Продолжаем без Allure-отчётов...")


# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

SCRIPTS = {
    "uninstall": os.path.join(SCRIPT_DIR, "deinstall.py"),
    "download": os.path.join(SCRIPT_DIR, "download_build.py"),
    "install": os.path.join(SCRIPT_DIR, "install.py"),
    "configure": os.path.join(SCRIPT_DIR, "configure_server.py"),
    "dispatch_test": os.path.join(SCRIPT_DIR, "dispatch_console_test.py"),
    "one_test": os.path.join(SCRIPT_DIR, "trbonet_one_test.py"),
}

DEFAULT_OLD_VERSION = "6.5.0.9138"
DEFAULT_NEW_VERSION = "6.5.0.9140"

LOG_FILE = os.path.join("logs", "orchestrator.log")
ALLURE_RESULTS_DIR = os.path.join(SCRIPT_DIR, "allure-results")
ALLURE_REPORT_DIR = os.path.join(SCRIPT_DIR, "allure-report")

DELAY_BETWEEN_STEPS = 3

STEP_TIMEOUTS = {
    "uninstall": 300,
    "download": 600,
    "install": 900,
    "configure": 300,
    "dispatch_test": 180,
    "one_test": 180,
}


# ============================================================================
# СТАТУСЫ
# ============================================================================

class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepResult:
    step_name: str
    script_path: str
    status: StepStatus
    message: str = ""
    exit_code: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration: float = 0.0
    output: List[str] = field(default_factory=list)


# ============================================================================
# ОЧИСТКА СТАРЫХ РЕЗУЛЬТАТОВ
# ============================================================================

def clean_allure_dirs():
    """
    Очищает папки allure-results и allure-report перед новым запуском.
    """
    log_message("🧹 Очистка старых Allure-результатов...", "INFO")

    for dir_path in [ALLURE_RESULTS_DIR, ALLURE_REPORT_DIR]:
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
                log_message(f"  ✅ Удалена папка: {dir_path}", "INFO")
            except Exception as e:
                log_message(f"  ⚠️ Не удалось удалить {dir_path}: {e}", "WARNING")
        else:
            log_message(f"  ℹ️ Папка не существует: {dir_path}", "INFO")

    # Создаём свежую папку для результатов
    os.makedirs(ALLURE_RESULTS_DIR, exist_ok=True)
    log_message(f"  ✅ Создана свежая папка: {ALLURE_RESULTS_DIR}", "SUCCESS")


# ============================================================================
# ALLURE УТИЛИТЫ (ручное сохранение)
# ============================================================================

def save_allure_result(test_name: str, status: str, start_time: datetime,
                       end_time: datetime, attachments: List[Dict] = None):
    """
    Сохраняет результат теста в формате Allure JSON.

    Args:
        test_name: Название теста
        status: Статус (passed, failed, broken, skipped)
        start_time: Время начала
        end_time: Время окончания
        attachments: Список вложений [{"name": str, "content": bytes, "type": str}]
    """
    if not ALLURE_AVAILABLE:
        return

    try:
        os.makedirs(ALLURE_RESULTS_DIR, exist_ok=True)

        test_uuid = str(uuid.uuid4())
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        duration_sec = (end_time - start_time).total_seconds()

        # Формируем сообщение в зависимости от статуса
        if status == "passed":
            message = f"✅ Тест пройден за {duration_sec:.1f} сек"
        else:
            message = f"❌ Тест провален за {duration_sec:.1f} сек"

        result = {
            "uuid": test_uuid,
            "name": test_name,
            "status": status,
            "statusDetails": {
                "message": message
            },
            "stage": "finished",
            "start": int(start_time.timestamp() * 1000),
            "stop": int(end_time.timestamp() * 1000),
            "duration": duration_ms,
            "historyId": test_uuid,
            "fullName": test_name,
            "labels": [
                {"name": "suite", "value": "Оркестратор TRBOnet"},
                {"name": "testClass", "value": "Orchestrator"},
            ]
        }

        if attachments:
            attachment_files = []
            for att in attachments:
                # Сохраняем вложение как отдельный файл
                if att['type'] == 'image/png':
                    att_filename = f"{test_uuid}-{att['name'].replace(' ', '_')}.png"
                else:
                    att_filename = f"{test_uuid}-{att['name'].replace(' ', '_')}"
                att_filepath = os.path.join(ALLURE_RESULTS_DIR, att_filename)

                with open(att_filepath, 'wb') as f:
                    f.write(att['content'])

                attachment_files.append({
                    "name": att['name'],
                    "source": att_filename,
                    "type": att.get('type', 'text/plain')
                })

            if attachment_files:
                result["attachments"] = attachment_files

        result_file = os.path.join(ALLURE_RESULTS_DIR, f"{test_uuid}-result.json")
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        return test_uuid

    except Exception as e:
        log_message(f"⚠️ Ошибка при сохранении Allure-результата: {e}", "WARNING")
        return None


def init_allure():
    """Инициализирует Allure, создаёт папку для результатов."""
    if not ALLURE_AVAILABLE:
        return

    try:
        os.makedirs(ALLURE_RESULTS_DIR, exist_ok=True)
        log_message(f"✅ Allure инициализирован. Результаты будут сохранены в: {ALLURE_RESULTS_DIR}", "SUCCESS")

    except Exception as e:
        log_message(f"⚠️ Ошибка при инициализации Allure: {e}", "WARNING")


def allure_step(step_name: str):
    """
    Контекстный менеджер для оборачивания шагов в allure.step.
    """
    if not ALLURE_AVAILABLE:
        class DummyContext:
            def __enter__(self): return None
            def __exit__(self, *args): pass
        return DummyContext()

    return allure.step(step_name)


def attach_text(text: str, name: str = "Лог"):
    """Добавляет текстовое вложение в Allure-отчёт."""
    if not ALLURE_AVAILABLE:
        return

    try:
        allure.attach(text, name=name, attachment_type=AttachmentType.TEXT)
    except Exception as e:
        log_message(f"⚠️ Ошибка при добавлении вложения: {e}", "WARNING")


def attach_screenshot(screenshot_path: str, name: str = "Скриншот"):
    """Добавляет скриншот в Allure-отчёт."""
    if not ALLURE_AVAILABLE:
        return

    if not os.path.exists(screenshot_path):
        return

    try:
        with open(screenshot_path, 'rb') as f:
            screenshot_data = f.read()
        allure.attach(screenshot_data, name=name, attachment_type=AttachmentType.PNG)
    except Exception as e:
        log_message(f"⚠️ Ошибка при добавлении скриншота: {e}", "WARNING")


def get_screenshot_attachments(screenshot_type: str) -> List[Dict]:
    """
    Собирает скриншоты для Allure-вложений.

    Args:
        screenshot_type: "console" или "one"

    Returns:
        Список словарей с вложениями для Allure
    """
    attachments = []

    if screenshot_type == "console":
        actual_path = os.path.join(SCRIPT_DIR, "screenshots", "actual_console.png")
        diff_path = os.path.join(SCRIPT_DIR, "screenshots", "diff_console.png")
        expected_path = os.path.join(SCRIPT_DIR, "screenshots", "expected_console.png")
        prefix = "Console"
    else:
        actual_path = os.path.join(SCRIPT_DIR, "screenshots", "actual_one.png")
        diff_path = os.path.join(SCRIPT_DIR, "screenshots", "diff_one.png")
        expected_path = os.path.join(SCRIPT_DIR, "screenshots", "expected_one.png")
        prefix = "One"

    # Добавляем Actual (всегда)
    if os.path.exists(actual_path):
        with open(actual_path, 'rb') as f:
            attachments.append({
                "name": f"Actual {prefix}",
                "content": f.read(),
                "type": "image/png"
            })

    # Добавляем Expected (если есть)
    if os.path.exists(expected_path):
        with open(expected_path, 'rb') as f:
            attachments.append({
                "name": f"Expected {prefix}",
                "content": f.read(),
                "type": "image/png"
            })

    # Добавляем Diff (если есть)
    if os.path.exists(diff_path):
        with open(diff_path, 'rb') as f:
            attachments.append({
                "name": f"Diff {prefix}",
                "content": f.read(),
                "type": "image/png"
            })

    return attachments

def attach_error(error_message: str, error_trace: str = ""):
    """Добавляет ошибку в Allure-отчёт."""
    if not ALLURE_AVAILABLE:
        return

    try:
        full_error = error_message
        if error_trace:
            full_error += "\n\n" + error_trace
        allure.attach(full_error, name="Ошибка выполнения", attachment_type=AttachmentType.TEXT)
    except Exception as e:
        log_message(f"⚠️ Ошибка при добавлении ошибки: {e}", "WARNING")


# ============================================================================
# ГЕНЕРАЦИЯ ALLURE-ОТЧЁТА
# ============================================================================

def fix_allure_encoding(report_dir: str):
    """
    Исправляет кодировку в HTML-файлах Allure-отчёта.
    Добавляет мета-тег charset=UTF-8 в каждый HTML-файл.
    """
    log_message("  🔧 Исправление кодировки HTML-файлов...", "INFO")

    fixed_count = 0
    for root, dirs, files in os.walk(report_dir):
        for file in files:
            if file.endswith('.html'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Проверяем, есть ли уже meta charset
                    if '<meta charset="UTF-8"' not in content and '<meta charset="utf-8"' not in content:
                        # Добавляем meta charset после <head>
                        if '<head>' in content:
                            content = content.replace('<head>', '<head>\n    <meta charset="UTF-8">')
                            fixed_count += 1
                        elif '<html>' in content:
                            content = content.replace('<html>', '<html>\n<head>\n    <meta charset="UTF-8">\n</head>')
                            fixed_count += 1

                    # Записываем обратно
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)

                except Exception as e:
                    log_message(f"    ⚠️ Не удалось исправить {file}: {e}", "WARNING")

    if fixed_count > 0:
        log_message(f"  ✅ Исправлено HTML-файлов: {fixed_count}", "SUCCESS")
    else:
        log_message(f"  ℹ️ Все HTML-файлы уже содержат мета-тег charset", "INFO")

    # Проверяем отображение русского языка
    try:
        index_path = os.path.join(report_dir, 'index.html')
        if os.path.exists(index_path):
            with open(index_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'Оркестратор' in content or 'УДАЛЕНИЕ' in content:
                    log_message(f"  ✅ Русский язык корректно отображается", "SUCCESS")
                else:
                    log_message(f"  ⚠️ Возможно, русский язык не отображается корректно", "WARNING")
    except:
        pass


def generate_allure_report():
    """
    Генерирует HTML-отчёт из Allure-результатов.
    Выполняет ТУ ЖЕ команду, что и вручную.
    """
    log_message("\n" + "=" * 60, "INFO")
    log_message("📊 ГЕНЕРАЦИЯ ALLURE-ОТЧЁТА", "INFO")
    log_message("=" * 60, "INFO")

    # Проверяем, есть ли результаты
    if not os.path.exists(ALLURE_RESULTS_DIR):
        log_message("❌ Папка с результатами не найдена", "ERROR")
        return False

    result_files = [f for f in os.listdir(ALLURE_RESULTS_DIR) if f.endswith('.json')]
    if not result_files:
        log_message("❌ Нет JSON-файлов в папке allure-results", "ERROR")
        return False

    log_message(f"  Найдено JSON-файлов: {len(result_files)}", "INFO")

    # Удаляем старый отчёт
    if os.path.exists(ALLURE_REPORT_DIR):
        try:
            shutil.rmtree(ALLURE_REPORT_DIR)
            log_message("  ✅ Старый отчёт удалён", "INFO")
        except Exception as e:
            log_message(f"  ⚠️ Не удалось удалить старый отчёт: {e}", "WARNING")

    # Генерируем отчёт
    try:
        log_message("  ⏳ Генерация отчёта... (может занять некоторое время)", "INFO")

        # Формируем команду ТОЧНО так же, как ты выполняешь вручную
        cmd = f'cd /d "{SCRIPT_DIR}" && allure generate allure-results -o allure-report --clean'

        log_message(f"  Команда: {cmd}", "INFO")
        log_message(f"  Рабочая директория: {SCRIPT_DIR}", "INFO")

        # Используем os.system — он точно повторяет ручной ввод
        exit_code = os.system(cmd)

        if exit_code != 0:
            log_message(f"  ❌ Ошибка при генерации отчёта: код {exit_code}", "ERROR")
            return False

        log_message(f"  ✅ Отчёт сгенерирован в: {ALLURE_REPORT_DIR}", "SUCCESS")

        # Проверяем, что index.html существует
        index_path = os.path.join(ALLURE_REPORT_DIR, 'index.html')
        if os.path.exists(index_path):
            log_message(f"  ✅ index.html создан", "SUCCESS")

            # Исправляем кодировку в HTML-файлах
            fix_allure_encoding(ALLURE_REPORT_DIR)

            return True
        else:
            log_message(f"  ⚠️ index.html не найден", "WARNING")
            return False

    except Exception as e:
        log_message(f"  ❌ Ошибка при генерации отчёта: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def open_allure_report():
    """
    Открывает Allure-отчёт через команду 'allure open' (как вручную).
    """
    log_message("  📂 Открытие Allure-отчёта...", "INFO")

    # Проверяем, что отчёт существует
    if not os.path.exists(ALLURE_REPORT_DIR):
        log_message(f"  ❌ Папка с отчётом не найдена: {ALLURE_REPORT_DIR}", "ERROR")
        return False

    index_path = os.path.join(ALLURE_REPORT_DIR, 'index.html')
    if not os.path.exists(index_path):
        log_message(f"  ❌ index.html не найден", "ERROR")
        return False

    try:
        # Выполняем команду 'allure open' так же, как вручную
        cmd = f'cd /d "{SCRIPT_DIR}" && allure open allure-report'

        log_message(f"  Команда: {cmd}", "INFO")

        # Запускаем в фоновом режиме, чтобы не блокировать скрипт
        subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        log_message(f"  ✅ Отчёт открыт в браузере", "SUCCESS")
        return True

    except Exception as e:
        log_message(f"  ⚠️ Не удалось открыть отчёт автоматически: {e}", "WARNING")
        log_message(f"  Откройте вручную: cd {SCRIPT_DIR} && allure open allure-report", "INFO")
        return False


# ============================================================================
# ЛОГГИРОВАНИЕ
# ============================================================================

def log_message(message: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}"
    print(log_entry)

    try:
        # Создаём папку для логов, если её нет
        log_dir = os.path.join(SCRIPT_DIR, "logs")
        os.makedirs(log_dir, exist_ok=True)

        log_path = os.path.join(SCRIPT_DIR, LOG_FILE)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
    except:
        pass


# ============================================================================
# ОРКЕСТРАТОР
# ============================================================================

class Orchestrator:
    def __init__(self, old_version: str, new_version: str):
        self.old_version = old_version
        self.new_version = new_version
        self.results: List[StepResult] = []
        self.start_time = datetime.now()

        # Очищаем старые Allure-результаты
        clean_allure_dirs()

        # Инициализируем Allure
        init_allure()

        log_message("=" * 80, "INFO")
        log_message("🚀 ЗАПУСК ОРКЕСТРАТОРА", "INFO")
        log_message("=" * 80, "INFO")
        log_message(f"  Старая версия: {old_version}", "INFO")
        log_message(f"  Новая версия: {new_version}", "INFO")
        log_message(f"  Путь к сборкам: {BUILD_PATH}", "INFO")
        if ALLURE_AVAILABLE:
            log_message(f"  Allure-результаты: {ALLURE_RESULTS_DIR}", "INFO")
        log_message("=" * 80, "INFO")

    def check_scripts(self) -> bool:
        with allure_step("Проверка наличия скриптов"):
            all_exist = True
            for name, path in SCRIPTS.items():
                if os.path.exists(path):
                    log_message(f"  ✅ {name}: {path}", "SUCCESS")
                else:
                    log_message(f"  ❌ {name}: {path} - НЕ НАЙДЕН", "ERROR")
                    all_exist = False
                    attach_text(f"Скрипт не найден: {path}", name=f"Ошибка: {name}")
            return all_exist

    def run_script(self, script_key: str, args: List[str]) -> StepResult:
        script_path = SCRIPTS.get(script_key)
        step_name = f"Запуск {script_key}"

        with allure_step(step_name):
            if not script_path or not os.path.exists(script_path):
                error_msg = f"Скрипт '{script_key}' не найден"
                attach_error(error_msg)
                return StepResult(
                    step_name=script_key,
                    script_path=script_path or "не найден",
                    status=StepStatus.FAILED,
                    message=error_msg
                )

            cmd = [sys.executable, script_path] + args
            timeout = STEP_TIMEOUTS.get(script_key, 600)

            log_message(f"  Команда: {' '.join(cmd)}", "INFO")
            log_message(f"  Таймаут: {timeout} сек", "INFO")

            attach_text(f"Команда: {' '.join(cmd)}\nТаймаут: {timeout} сек", name="Команда выполнения")

            start_time = datetime.now()
            output_lines = []

            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    bufsize=1,
                    universal_newlines=True
                )

                for line in process.stdout:
                    print(f"    {line.rstrip()}")
                    output_lines.append(line.rstrip())

                exit_code = process.wait(timeout=timeout)

                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                full_output = "\n".join(output_lines)
                if full_output:
                    attach_text(full_output, name=f"Вывод скрипта {script_key}")

                status = StepStatus.SUCCESS if exit_code == 0 else StepStatus.FAILED

                if status == StepStatus.FAILED:
                    attach_error(f"Скрипт завершился с кодом: {exit_code}", full_output)

                return StepResult(
                    step_name=script_key,
                    script_path=script_path,
                    status=status,
                    message="Скрипт выполнен" if exit_code == 0 else f"Ошибка (код: {exit_code})",
                    exit_code=exit_code,
                    start_time=start_time,
                    end_time=end_time,
                    duration=duration,
                    output=output_lines
                )

            except subprocess.TimeoutExpired:
                process.kill()
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                error_msg = f"Превышен таймаут ({timeout} сек)"
                attach_error(error_msg, "\n".join(output_lines))

                return StepResult(
                    step_name=script_key,
                    script_path=script_path,
                    status=StepStatus.FAILED,
                    message=error_msg,
                    exit_code=-1,
                    start_time=start_time,
                    end_time=end_time,
                    duration=duration,
                    output=output_lines
                )

            except Exception as e:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                import traceback
                error_trace = traceback.format_exc()
                attach_error(str(e), error_trace)

                return StepResult(
                    step_name=script_key,
                    script_path=script_path,
                    status=StepStatus.FAILED,
                    message=f"Исключение: {str(e)}",
                    exit_code=-2,
                    start_time=start_time,
                    end_time=end_time,
                    duration=duration,
                    output=output_lines
                )

    # ================================================================
    # ОБЯЗАТЕЛЬНЫЕ ШАГИ (1-4)
    # ================================================================

    def step_uninstall(self) -> StepResult:
        step_name = "ШАГ 1: УДАЛЕНИЕ СТАРОЙ ВЕРСИИ"
        with allure_step(step_name):
            log_message("\n" + "=" * 60, "INFO")
            log_message(f"📌 {step_name}", "INFO")
            log_message("=" * 60, "INFO")
            attach_text(f"Удаление версии: {self.old_version}", name="Удаляемая версия")
            args = [self.old_version]
            return self.run_script("uninstall", args)

    def step_download(self) -> StepResult:
        step_name = "ШАГ 2: СКАЧИВАНИЕ НОВОЙ ВЕРСИИ"
        with allure_step(step_name):
            log_message("\n" + "=" * 60, "INFO")
            log_message(f"📌 {step_name}", "INFO")
            log_message("=" * 60, "INFO")
            attach_text(f"Скачивание версии: {self.new_version}", name="Скачиваемая версия")
            args = [self.new_version]
            return self.run_script("download", args)

    def step_install(self) -> StepResult:
        step_name = "ШАГ 3: УСТАНОВКА НОВОЙ ВЕРСИИ"
        with allure_step(step_name):
            log_message("\n" + "=" * 60, "INFO")
            log_message(f"📌 {step_name}", "INFO")
            log_message("=" * 60, "INFO")
            attach_text(f"Установка версии: {self.new_version}", name="Устанавливаемая версия")
            args = [self.new_version]
            return self.run_script("install", args)

    def step_configure(self) -> StepResult:
        step_name = "ШАГ 4: НАСТРОЙКА СЕРВЕРА"
        with allure_step(step_name):
            log_message("\n" + "=" * 60, "INFO")
            log_message(f"📌 {step_name}", "INFO")
            log_message("=" * 60, "INFO")
            attach_text(f"Настройка сервера для версии: {self.new_version}", name="Настраиваемая версия")
            args = [self.new_version]
            return self.run_script("configure", args)

    # ================================================================
    # НЕЗАВИСИМЫЕ ТЕСТЫ (5-6) С ПРИКРЕПЛЕНИЕМ СКРИНШОТОВ
    # ================================================================

    def step_dispatch_test(self) -> StepResult:
        step_name = "ШАГ 5: ТЕСТИРОВАНИЕ DISPATCH CONSOLE"
        with allure_step(step_name):
            log_message("\n" + "=" * 60, "INFO")
            log_message(f"📌 {step_name}", "INFO")
            log_message("=" * 60, "INFO")

            # Запускаем тест
            args = [self.new_version]
            result = self.run_script("dispatch_test", args)

            # Сохраняем скриншоты в результат
            attachments = get_screenshot_attachments("console")
            if attachments:
                log_message(f"  📷 Найдено скриншотов: {len(attachments)}", "INFO")
            result._attachments = attachments

            return result

    def step_one_test(self) -> StepResult:
        step_name = "ШАГ 6: ТЕСТИРОВАНИЕ TRBOnet One"
        with allure_step(step_name):
            log_message("\n" + "=" * 60, "INFO")
            log_message(f"📌 {step_name}", "INFO")
            log_message("=" * 60, "INFO")

            # Запускаем тест
            args = [self.new_version]
            result = self.run_script("one_test", args)

            # Сохраняем скриншоты в результат
            attachments = get_screenshot_attachments("one")
            if attachments:
                log_message(f"  📷 Найдено скриншотов: {len(attachments)}", "INFO")
            result._attachments = attachments

            return result

    # ================================================================
    # ОСНОВНАЯ ЛОГИКА ЗАПУСКА
    # ================================================================

    def run_all(self) -> bool:
        with allure_step("Выполнение всех шагов оркестратора"):
            if not self.check_scripts():
                log_message("❌ Не все скрипты найдены. Завершение.", "ERROR")
                attach_error("Не все скрипты найдены", "Проверьте наличие файлов в папке core_desktop")
                return False

            # ================================================================
            # ШАГИ 1-4: ОБЯЗАТЕЛЬНЫЕ (установка)
            # ================================================================
            mandatory_steps = [
                ("uninstall", self.step_uninstall),
                ("download", self.step_download),
                ("install", self.step_install),
                ("configure", self.step_configure),
            ]

            for step_name, step_func in mandatory_steps:
                result = step_func()
                self.results.append(result)

                # Сохраняем результат шага в Allure (без вложений)
                status_allure = "passed" if result.status == StepStatus.SUCCESS else "failed"
                save_allure_result(
                    test_name=result.step_name.upper(),
                    status=status_allure,
                    start_time=result.start_time,
                    end_time=result.end_time or datetime.now(),
                    attachments=[]
                )

                if result.status != StepStatus.SUCCESS:
                    log_message(f"❌ ОБЯЗАТЕЛЬНЫЙ ШАГ '{step_name.upper()}' ПРОВАЛЕН. Остановка.", "ERROR")
                    self._save_report()
                    return False

                time.sleep(DELAY_BETWEEN_STEPS)

            # ================================================================
            # ШАГИ 5-6: НЕЗАВИСИМЫЕ ТЕСТЫ (продолжаем даже при ошибках)
            # ================================================================
            test_steps = [
                ("dispatch_test", self.step_dispatch_test, "Dispatch Console"),
                ("one_test", self.step_one_test, "TRBOnet One"),
            ]

            tests_failed = False

            for step_name, step_func, display_name in test_steps:
                log_message(f"\n{'=' * 60}", "INFO")
                log_message(f"🧪 ЗАПУСК ТЕСТА: {display_name}", "INFO")
                log_message(f"{'=' * 60}", "INFO")

                result = step_func()
                self.results.append(result)

                # Сохраняем результат в Allure С ВЛОЖЕНИЯМИ
                status_allure = "passed" if result.status == StepStatus.SUCCESS else "failed"

                # Получаем вложения из результата
                attachments = getattr(result, '_attachments', [])

                save_allure_result(
                    test_name=result.step_name.upper(),
                    status=status_allure,
                    start_time=result.start_time,
                    end_time=result.end_time or datetime.now(),
                    attachments=attachments  # ← ВЛОЖЕНИЯ!
                )

                if result.status != StepStatus.SUCCESS:
                    log_message(f"⚠️ ТЕСТ '{display_name}' ПРОВАЛЕН, но продолжаем выполнение...", "WARNING")
                    tests_failed = True
                else:
                    log_message(f"✅ ТЕСТ '{display_name}' ПРОШЕЛ УСПЕШНО", "SUCCESS")

                time.sleep(DELAY_BETWEEN_STEPS)

            # Сохраняем итоговый отчёт (даже если тесты упали)
            self._save_report()

            # Возвращаем False только если упали ОБЯЗАТЕЛЬНЫЕ шаги (1-4)
            # Если упали только тесты — возвращаем True, чтобы пайплайн не считался полностью проваленным
            return not tests_failed

    # ================================================================
    # СОХРАНЕНИЕ ОТЧЁТА
    # ================================================================

    def _save_report(self):
        total_time = (datetime.now() - self.start_time).total_seconds()

        # Разделяем обязательные шаги и тесты
        mandatory_results = self.results[:4] if len(self.results) >= 4 else self.results
        test_results = self.results[4:] if len(self.results) > 4 else []

        mandatory_ok = all(r.status == StepStatus.SUCCESS for r in mandatory_results) if mandatory_results else False
        tests_ok = all(r.status == StepStatus.SUCCESS for r in test_results) if test_results else True
        all_success = all(r.status == StepStatus.SUCCESS for r in self.results) if self.results else False

        log_message("\n" + "=" * 80, "INFO")
        log_message("📊 ОТЧЁТ О ВЫПОЛНЕНИИ", "INFO")
        log_message("=" * 80, "INFO")

        if mandatory_ok and not tests_ok:
            log_message(f"  ОБЩИЙ СТАТУС: ⚠️ УСТАНОВКА УСПЕШНА, НО ЕСТЬ ПРОБЛЕМЫ В ТЕСТАХ", "WARNING")
        elif all_success:
            log_message(f"  ОБЩИЙ СТАТУС: ✅ ВСЕ ШАГИ УСПЕШНЫ", "SUCCESS")
        else:
            log_message(f"  ОБЩИЙ СТАТУС: ❌ ЕСТЬ ОШИБКИ", "ERROR")

        log_message(f"  Общее время: {total_time:.1f} сек", "INFO")
        log_message("", "INFO")
        log_message("  ДЕТАЛИ ШАГОВ:", "INFO")
        log_message("  " + "-" * 70, "INFO")

        report_summary = f"""
Общий статус: {'ВСЕ УСПЕШНО' if all_success else 'ЕСТЬ ОШИБКИ'}
Общее время: {total_time:.1f} сек
Старая версия: {self.old_version}
Новая версия: {self.new_version}
Обязательные шаги (1-4): {'✅ УСПЕШНО' if mandatory_ok else '❌ ЕСТЬ ОШИБКИ'}
Тесты (5-6): {'✅ УСПЕШНО' if tests_ok else '⚠️ ЕСТЬ ОШИБКИ'}
        """

        with allure_step("Формирование отчёта"):
            attach_text(report_summary, name="Итоговый отчёт")

            for result in self.results:
                emoji = "✅" if result.status == StepStatus.SUCCESS else "❌"
                log_message(
                    f"    {emoji} {result.step_name.upper():14} | "
                    f"Статус: {result.status.value.upper():7} | "
                    f"Время: {result.duration:.1f} сек",
                    "INFO"
                )
                if result.message:
                    log_message(f"         Сообщение: {result.message}", "INFO")

                step_info = f"""
Шаг: {result.step_name}
Статус: {result.status.value}
Время выполнения: {result.duration:.1f} сек
Сообщение: {result.message}
                """
                attach_text(step_info, name=f"Результат: {result.step_name}")

        log_message("  " + "-" * 70, "INFO")
        log_message("=" * 80, "INFO")

        # Сохраняем JSON-отчёт
        report_file = os.path.join(
            SCRIPT_DIR,
            "logs",
            f"orchestrator_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        os.makedirs(os.path.dirname(report_file), exist_ok=True)

        report_data = {
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "total_duration_seconds": total_time,
            "old_version": self.old_version,
            "new_version": self.new_version,
            "build_path": BUILD_PATH,
            "overall_success": all_success,
            "mandatory_success": mandatory_ok,
            "tests_success": tests_ok,
            "steps": [
                {
                    "name": r.step_name,
                    "status": r.status.value,
                    "message": r.message,
                    "exit_code": r.exit_code,
                    "duration_seconds": r.duration,
                }
                for r in self.results
            ]
        }

        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            log_message(f"📄 Подробный отчёт сохранён: {report_file}", "INFO")
            attach_text(json.dumps(report_data, indent=2, ensure_ascii=False), name="JSON-отчёт")
        except Exception as e:
            log_message(f"⚠️ Не удалось сохранить отчёт: {e}", "WARNING")
            attach_error(f"Ошибка сохранения отчёта: {e}")

        # ================================================================
        # ГЕНЕРАЦИЯ ALLURE HTML-ОТЧЁТА
        # ================================================================

        # Сохраняем итоговый результат в Allure
        final_status = "passed" if all_success else "failed"
        save_allure_result(
            test_name="ВСЕ ШАГИ ОРКЕСТРАТОРА",
            status=final_status,
            start_time=self.start_time,
            end_time=datetime.now(),
            attachments=[]
        )

        # Валидация JSON-файлов
        validate_allure_json()

        # Генерируем HTML-отчёт
        report_generated = generate_allure_report()

        if report_generated:
            # Открываем отчёт в браузере
            open_allure_report()
        else:
            log_message("⚠️ HTML-отчёт не сгенерирован. Проверьте установку Allure CLI и Java.", "WARNING")
            log_message(f"  Результаты сохранены в: {ALLURE_RESULTS_DIR}", "INFO")
            log_message("  Для генерации отчёта вручную выполните:", "INFO")
            log_message("    allure generate allure-results -o allure-report --clean", "INFO")
            log_message("    allure open allure-report", "INFO")

        finalize_allure()


def validate_allure_json():
    """
    Проверяет корректность JSON-файлов в папке allure-results.
    """
    log_message("  🔍 Проверка JSON-файлов...", "INFO")

    if not os.path.exists(ALLURE_RESULTS_DIR):
        log_message("  ❌ Папка allure-results не найдена", "ERROR")
        return False

    errors = []
    json_files = [f for f in os.listdir(ALLURE_RESULTS_DIR) if f.endswith('.json')]

    if not json_files:
        log_message("  ❌ Нет JSON-файлов в папке allure-results", "ERROR")
        return False

    for file in json_files:
        file_path = os.path.join(ALLURE_RESULTS_DIR, file)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Проверяем обязательные поля
            required_fields = ['uuid', 'name', 'status', 'start', 'stop']
            for field in required_fields:
                if field not in data:
                    errors.append(f"{file}: отсутствует поле '{field}'")

        except json.JSONDecodeError as e:
            errors.append(f"{file}: ошибка парсинга JSON - {e}")
        except Exception as e:
            errors.append(f"{file}: ошибка - {e}")

    if errors:
        log_message(f"  ❌ Найдены ошибки в {len(errors)} файлах:", "ERROR")
        for error in errors:
            log_message(f"      - {error}", "ERROR")
        return False
    else:
        log_message(f"  ✅ Все JSON-файлы корректны ({len(json_files)} файлов)", "SUCCESS")
        return True


def finalize_allure():
    """Завершает Allure-сессию."""
    if not ALLURE_AVAILABLE:
        return

    try:
        log_message(f"✅ Allure-результаты сохранены в: {ALLURE_RESULTS_DIR}", "SUCCESS")

        result_files = [f for f in os.listdir(ALLURE_RESULTS_DIR) if f.endswith('.json')]
        log_message(f"   Создано JSON-файлов: {len(result_files)}", "INFO")

    except Exception as e:
        log_message(f"⚠️ Ошибка при завершении Allure: {e}", "WARNING")


# ============================================================================
# ТОЧКА ВХОДА
# ============================================================================

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Оркестратор для автоматической установки TRBOnet",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python orchestrator.py -o 6.5.0.9138 -n 6.5.0.9140
  python orchestrator.py --old-version 6.5.0.9138 --new-version 6.5.0.9140
  python orchestrator.py  # использует значения по умолчанию
        """
    )

    parser.add_argument(
        "-o", "--old-version",
        type=str,
        default=DEFAULT_OLD_VERSION,
        help=f"Версия для удаления (по умолчанию: {DEFAULT_OLD_VERSION})"
    )

    parser.add_argument(
        "-n", "--new-version",
        type=str,
        default=DEFAULT_NEW_VERSION,
        help=f"Версия для установки (по умолчанию: {DEFAULT_NEW_VERSION})"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Проверить наличие скриптов, но не запускать"
    )

    return parser.parse_args()


def main():
    args = parse_arguments()

    orchestrator = Orchestrator(
        old_version=args.old_version,
        new_version=args.new_version
    )

    try:
        if args.dry_run:
            log_message("🔍 Dry-run режим: проверка скриптов...", "INFO")
            orchestrator.check_scripts()
            log_message("Dry-run завершён.", "INFO")
            return

        success = orchestrator.run_all()

        if not success:
            attach_error("Оркестратор завершился с ошибкой", "Проверьте логи выше для деталей")

        sys.exit(0 if success else 1)

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        log_message(f"❌ Критическая ошибка: {e}", "ERROR")
        print(error_trace)

        if ALLURE_AVAILABLE:
            attach_error(f"Критическая ошибка: {str(e)}", error_trace)
            finalize_allure()

        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_message("⚠️ Операция прервана пользователем", "WARNING")
        sys.exit(130)
    except Exception as e:
        log_message(f"❌ Критическая ошибка: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1)