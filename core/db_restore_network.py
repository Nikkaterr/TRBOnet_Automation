"""
Универсальный модуль для восстановления базы данных из сетевого ZIP-архива
RESTORE выполняется через sqlcmd (subprocess), остальное через pyodbc
"""

import os
import sys
import time
import zipfile
import argparse
import pyodbc
import subprocess
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass

# ============================================================================
# DATACLASS ДЛЯ КОНФИГУРАЦИИ
# ============================================================================

@dataclass
class RestoreConfig:
    """Конфигурация для восстановления базы данных."""
    sql_server: str = "localhost"
    auth_type: str = "sql"
    sql_user: str = "sa"
    sql_password: str = ""
    sql_timeout: int = 3600
    odbc_driver: str = "ODBC Driver 18 for SQL Server"
    backup_network_path: str = ""
    database_name: str = ""
    data_path: str = "C:\\Database_Backups"
    network_username: str = ""
    network_password: str = ""
    network_drive_letter: str = "Z"
    cleanup_bak: bool = True
    restore_timeout: int = 600
    silent: bool = False

# ============================================================================
# ЛОГГИРОВАНИЕ
# ============================================================================

def log(message: str, config: RestoreConfig = None):
    if config and config.silent:
        return
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

# ============================================================================
# ПОДКЛЮЧЕНИЕ К SQL SERVER (pyodbc)
# ============================================================================

def get_connection_string(config: RestoreConfig, use_encryption: bool = False) -> str:
    base = f"DRIVER={{{config.odbc_driver}}};SERVER={config.sql_server};"
    if config.auth_type.lower() == "windows":
        base += "Trusted_Connection=yes;"
    else:
        base += f"UID={config.sql_user};PWD={config.sql_password};"
    if use_encryption:
        base += "Encrypt=yes;TrustServerCertificate=yes;"
    else:
        base += "Encrypt=no;TrustServerCertificate=yes;"
    base += f"Connection Timeout={min(30, config.sql_timeout)};"
    return base

def test_connection(config: RestoreConfig) -> Tuple[bool, str]:
    try:
        conn_str = get_connection_string(config, use_encryption=False)
        conn = pyodbc.connect(conn_str, timeout=10)
        conn.close()
        return True, "Подключение успешно"
    except Exception as e:
        try:
            conn_str = get_connection_string(config, use_encryption=True)
            conn = pyodbc.connect(conn_str, timeout=10)
            conn.close()
            return True, "Подключение успешно (Encrypt=yes)"
        except Exception as e2:
            return False, f"Ошибка подключения: {e2}"

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def format_size(size_bytes: int) -> str:
    if size_bytes is None or size_bytes < 0:
        return "0 Б"
    for unit in ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} ТБ"

def format_time(seconds: float) -> str:
    if seconds < 0:
        return "0 сек"
    if seconds < 60:
        return f"{seconds:.0f} сек"
    elif seconds < 3600:
        return f"{seconds // 60:.0f} мин {seconds % 60:.0f} сек"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours:.0f} ч {minutes:.0f} мин"

def extract_zip_in_network(zip_path: str, extract_to: str) -> Optional[str]:
    log(f"📦 Распаковка архива: {zip_path}")
    log(f"   Назначение: {extract_to}")

    if not os.path.exists(zip_path):
        log(f"❌ Архив не найден: {zip_path}")
        return None

    try:
        if not zipfile.is_zipfile(zip_path):
            log("❌ Файл не является корректным ZIP-архивом")
            return None

        with zipfile.ZipFile(zip_path, 'r') as zf:
            corrupted = zf.testzip()
            if corrupted:
                log(f"❌ Архив повреждён: {corrupted}")
                return None

            file_list = zf.namelist()
            bak_files = [f for f in file_list if f.lower().endswith('.bak')]
            if not bak_files:
                log("❌ В архиве не найдено .bak-файлов")
                return None

            target_bak_name = bak_files[0]
            bak_path = os.path.join(extract_to, os.path.basename(target_bak_name))

            if os.path.exists(bak_path):
                existing_size = os.path.getsize(bak_path)
                expected_size = zf.getinfo(target_bak_name).file_size
                if existing_size == expected_size:
                    log(f"✅ .bak файл уже существует: {os.path.basename(bak_path)}")
                    log(f"   Размер: {format_size(existing_size)}")
                    return bak_path
                else:
                    log(f"   Существующий .bak файл имеет неверный размер, удаляем...")
                    try:
                        os.remove(bak_path)
                    except Exception as e:
                        log(f"   Не удалось удалить старый файл: {e}")

            log(f"   Распаковка {os.path.basename(target_bak_name)}...")
            start_time = time.time()
            total_size = zf.getinfo(target_bak_name).file_size
            extracted = 0
            last_log_time = start_time

            os.makedirs(extract_to, exist_ok=True)

            with zf.open(target_bak_name) as source:
                with open(bak_path, 'wb') as target:
                    while True:
                        chunk = source.read(1024 * 1024)
                        if not chunk:
                            break
                        target.write(chunk)
                        extracted += len(chunk)

                        current_time = time.time()
                        if current_time - last_log_time >= 5:
                            percent = (extracted / total_size) * 100
                            elapsed = current_time - start_time
                            speed = extracted / elapsed if elapsed > 0 else 0
                            remaining = (total_size - extracted) / speed if speed > 0 else 0
                            log(f"      Прогресс: {percent:.1f}% | Скорость: {format_size(speed)}/с | Осталось: {format_time(remaining)}")
                            last_log_time = current_time

            elapsed = time.time() - start_time
            avg_speed = total_size / elapsed if elapsed > 0 else 0
            log(f"✅ Архив распакован за {format_time(elapsed)} (средняя скорость: {format_size(avg_speed)}/с)")

            if os.path.exists(bak_path) and os.path.getsize(bak_path) > 0:
                log(f"   .bak файл: {os.path.basename(bak_path)} ({format_size(os.path.getsize(bak_path))})")
                return bak_path
            else:
                log("❌ Распакованный .bak файл пустой или не существует")
                return None

    except Exception as e:
        log(f"❌ Ошибка при распаковке: {e}")
        import traceback
        traceback.print_exc()
        return None

def cleanup_bak_file(bak_path: str) -> bool:
    if bak_path and os.path.exists(bak_path):
        try:
            os.remove(bak_path)
            return True
        except:
            return False
    return True

# ============================================================================
# ПРОВЕРКА sqlcmd
# ============================================================================

def check_sqlcmd() -> bool:
    """Проверяет, доступен ли sqlcmd в системе."""
    try:
        result = subprocess.run(
            ["sqlcmd", "-?"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False

# ============================================================================
# ОСНОВНАЯ ФУНКЦИЯ: RESTORE через sqlcmd (subprocess)
# ============================================================================

def restore_via_sqlcmd(
    config: RestoreConfig,
    bak_path: str,
    db_name: str,
    mdf_path: str,
    ldf_path: Optional[str],
    data_file: str,
    log_file: Optional[str]
) -> Tuple[bool, str]:
    """
    Выполняет RESTORE DATABASE через sqlcmd (subprocess).
    Это основной и самый надёжный метод.
    """
    # Формируем команду RESTORE
    restore_cmd = f"""
RESTORE DATABASE [{db_name}]
FROM DISK = N'{bak_path}'
WITH REPLACE, RECOVERY,
MOVE N'{data_file}' TO N'{mdf_path}'
"""
    if log_file and ldf_path:
        restore_cmd += f",\nMOVE N'{log_file}' TO N'{ldf_path}'"
    restore_cmd += ";"

    log(f"   Выполняем RESTORE через sqlcmd...", config)

    # Формируем команду для sqlcmd
    sqlcmd_cmd = [
        "sqlcmd",
        "-S", config.sql_server,
        "-Q", restore_cmd,
        "-C",  # Доверять сертификату
        "-b",  # Останавливаться при ошибке
    ]

    if config.auth_type.lower() != "windows":
        sqlcmd_cmd.extend(["-U", config.sql_user, "-P", config.sql_password])

    log(f"   Команда: sqlcmd -S {config.sql_server} -Q \"RESTORE...\" -C -b", config)

    try:
        # Запускаем sqlcmd и ждём завершения
        result = subprocess.run(
            sqlcmd_cmd,
            capture_output=True,
            text=True,
            timeout=config.restore_timeout,
            check=False  # Не выбрасывать исключение при ошибке
        )

        # Выводим stdout для диагностики
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                log(f"      {line}", config)

        # Проверяем наличие ошибок
        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Неизвестная ошибка"
            log(f"   ❌ sqlcmd вернул ошибку: {error_msg}", config)
            return False, f"sqlcmd ошибка: {error_msg}"

        # Проверяем, что в выводе есть признак успеха
        if "successfully" in result.stdout.lower() and "restore" in result.stdout.lower():
            log(f"   ✅ RESTORE успешно завершён", config)
            return True, "RESTORE через sqlcmd выполнен успешно"
        else:
            log(f"   ⚠️ Не удалось определить успех RESTORE", config)
            # Если нет явной ошибки, считаем, что всё ОК
            return True, "RESTORE через sqlcmd выполнен (без явных ошибок)"

    except subprocess.TimeoutExpired:
        log(f"   ❌ Таймаут выполнения sqlcmd ({config.restore_timeout} сек.)", config)
        return False, f"Таймаут выполнения sqlcmd"
    except Exception as e:
        log(f"   ❌ Ошибка выполнения sqlcmd: {e}", config)
        return False, f"Ошибка выполнения sqlcmd: {e}"

# ============================================================================
# ОСНОВНАЯ ФУНКЦИЯ ВОССТАНОВЛЕНИЯ
# ============================================================================

def restore_database(config: RestoreConfig) -> Dict[str, Any]:
    """
    Универсальное восстановление базы данных.
    RESTORE выполняется через sqlcmd (subprocess).
    """
    result = {
        "success": False,
        "message": "",
        "database_name": config.database_name,
        "duration_seconds": 0,
        "bak_path": None,
        "server": config.sql_server,
        "error": None
    }

    start_time = datetime.now()

    try:
        log(f"🚀 Восстановление базы {config.database_name} на {config.sql_server}", config)
        log(f"   Архив: {config.backup_network_path}", config)

        # ШАГ 0: Проверка подключения
        log("   Проверка подключения к SQL Server...", config)
        conn_ok, conn_msg = test_connection(config)
        if not conn_ok:
            result["message"] = f"Не удалось подключиться: {conn_msg}"
            return result
        log(f"   ✅ {conn_msg}", config)

        # ШАГ 1: Распаковка ZIP
        network_folder = os.path.dirname(config.backup_network_path)
        log("   Распаковка архива...", config)

        # Пытаемся использовать UNC-путь напрямую
        zip_path = config.backup_network_path
        bak_path = extract_zip_in_network(zip_path, network_folder)

        if not bak_path:
            result["message"] = "Ошибка при распаковке архива"
            return result

        result["bak_path"] = bak_path
        log(f"   ✅ .bak файл: {os.path.basename(bak_path)} ({format_size(os.path.getsize(bak_path))})", config)

        # ШАГ 2: Получение структуры бэкапа (pyodbc)
        conn_str = get_connection_string(config, use_encryption=False)
        log("   Получение структуры бэкапа...", config)

        try:
            conn = pyodbc.connect(conn_str, timeout=config.sql_timeout, autocommit=False)
            cursor = conn.cursor()
            cursor.execute(f"RESTORE FILELISTONLY FROM DISK = N'{bak_path}'")
            rows = cursor.fetchall()

            if not rows:
                conn.close()
                result["message"] = "Не удалось прочитать структуру бэкапа"
                return result

            data_file = rows[0][0] if len(rows) > 0 else None
            log_file = rows[1][0] if len(rows) > 1 else None

            if not data_file:
                conn.close()
                result["message"] = "Не найден файл данных в бэкапе"
                return result

            mdf_path = os.path.join(config.data_path, f"{config.database_name}.mdf")
            ldf_path = os.path.join(config.data_path, f"{config.database_name}_log.ldf") if log_file else None
            conn.close()

            log(f"   Файл данных: {data_file} → {mdf_path}", config)
            if log_file and ldf_path:
                log(f"   Файл лога: {log_file} → {ldf_path}", config)

        except Exception as e:
            result["message"] = f"Ошибка при чтении структуры бэкапа: {e}"
            return result

        # ШАГ 3: Удаление существующей БД (pyodbc)
        log("   Удаление существующей БД (если есть)...", config)
        try:
            conn = pyodbc.connect(conn_str, timeout=config.sql_timeout, autocommit=True)
            cursor = conn.cursor()

            cursor.execute("SELECT database_id, state FROM sys.databases WHERE name = ?", config.database_name)
            db_info = cursor.fetchone()

            if db_info:
                if db_info[1] == 1:
                    try:
                        cursor.execute(f"RESTORE DATABASE [{config.database_name}] WITH RECOVERY")
                    except:
                        pass

                try:
                    cursor.execute(f"ALTER DATABASE [{config.database_name}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE")
                    cursor.execute(f"DROP DATABASE [{config.database_name}]")
                    log(f"   ✅ База {config.database_name} удалена", config)
                except:
                    try:
                        cursor.execute(f"ALTER DATABASE [{config.database_name}] SET OFFLINE WITH ROLLBACK IMMEDIATE")
                        cursor.execute(f"DROP DATABASE [{config.database_name}]")
                        log(f"   ✅ База {config.database_name} удалена (через OFFLINE)", config)
                    except:
                        log(f"   ⚠️ Не удалось удалить базу", config)
            else:
                log(f"   ✅ База {config.database_name} не существует", config)

            for file_path in [mdf_path, ldf_path]:
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        log(f"   🗑️ Удалён файл: {file_path}", config)
                    except:
                        pass
            conn.close()
        except Exception as e:
            log(f"   ⚠️ Ошибка при удалении БД: {e}", config)

        # ШАГ 4: RESTORE через sqlcmd (subprocess)
        log("   Выполнение RESTORE...", config)

        # Проверяем, доступен ли sqlcmd
        if not check_sqlcmd():
            log("   ⚠️ sqlcmd не найден, пробуем прямой RESTORE через pyodbc...", config)
            # Прямой RESTORE через pyodbc (резервный метод)
            success, message = restore_via_pyodbc(
                config, bak_path, config.database_name,
                mdf_path, ldf_path, data_file, log_file
            )
        else:
            success, message = restore_via_sqlcmd(
                config, bak_path, config.database_name,
                mdf_path, ldf_path, data_file, log_file
            )

        if not success:
            result["message"] = message
            return result

        log(f"   ✅ RESTORE выполнен: {message}", config)

        # ШАГ 5: Проверка состояния (pyodbc)
        log("   Проверка завершения восстановления...", config)
        try:
            conn = pyodbc.connect(conn_str, timeout=config.sql_timeout, autocommit=True)
            cursor = conn.cursor()

            max_wait = 120
            waited = 0
            db_online = False

            while waited < max_wait:
                time.sleep(5)
                waited += 5
                cursor.execute("SELECT database_id, state FROM sys.databases WHERE name = ?", config.database_name)
                db_info = cursor.fetchone()
                if db_info and db_info[1] == 0:
                    db_online = True
                    break
                if waited % 30 == 0:
                    log(f"      Ожидание завершения... ({waited} сек.)", config)

            if db_online:
                try:
                    cursor.execute(f"ALTER DATABASE [{config.database_name}] SET MULTI_USER")
                    conn.commit()
                    log("   ✅ База переведена в MULTI_USER", config)
                except Exception as e:
                    log(f"   ⚠️ Не удалось переключить в MULTI_USER: {e}", config)

                elapsed = (datetime.now() - start_time).total_seconds()
                log(f"   ✅ База восстановлена за {elapsed:.1f} сек.", config)

                if config.cleanup_bak:
                    cleanup_bak_file(bak_path)
                    log(f"   🗑️ .bak файл удалён", config)

                result["success"] = True
                result["message"] = "База данных успешно восстановлена"
                result["duration_seconds"] = elapsed
                conn.close()
                return result
            else:
                conn.close()
                result["message"] = "База не перешла в ONLINE"
                return result

        except Exception as e:
            result["message"] = f"Ошибка при проверке: {e}"
            return result

    except Exception as e:
        result["success"] = False
        result["message"] = f"Ошибка: {str(e)}"
        result["error"] = str(e)
        return result

# ============================================================================
# РЕЗЕРВНЫЙ МЕТОД: ПРЯМОЙ RESTORE ЧЕРЕЗ PYODBC
# ============================================================================

def restore_via_pyodbc(
    config: RestoreConfig,
    bak_path: str,
    db_name: str,
    mdf_path: str,
    ldf_path: Optional[str],
    data_file: str,
    log_file: Optional[str]
) -> Tuple[bool, str]:
    """
    Резервный метод: прямой RESTORE через pyodbc (если sqlcmd недоступен).
    """
    conn_str = get_connection_string(config, use_encryption=False)

    try:
        conn = pyodbc.connect(conn_str, timeout=config.sql_timeout, autocommit=True)
        cursor = conn.cursor()

        restore_cmd = f"""
RESTORE DATABASE [{db_name}]
FROM DISK = N'{bak_path}'
WITH REPLACE, RECOVERY,
MOVE N'{data_file}' TO N'{mdf_path}'
"""
        if log_file and ldf_path:
            restore_cmd += f",\nMOVE N'{log_file}' TO N'{ldf_path}'"
        restore_cmd += ";"

        log(f"   Выполняем RESTORE через pyodbc...", config)
        cursor.execute(restore_cmd)

        # Проверяем состояние
        time.sleep(5)
        cursor.execute("SELECT state FROM sys.databases WHERE name = ?", db_name)
        result_state = cursor.fetchone()

        if result_state and result_state[0] == 0:
            conn.close()
            return True, "Прямой RESTORE выполнен успешно"
        else:
            conn.close()
            state_msg = f"состояние {result_state[0]}" if result_state else "не существует"
            return False, f"RESTORE не завершился: база {state_msg}"

    except Exception as e:
        return False, str(e)

# ============================================================================
# КОМАНДНАЯ СТРОКА
# ============================================================================

def main_cli():
    parser = argparse.ArgumentParser(
        description="Универсальное восстановление базы данных из сетевого ZIP-архива"
    )

    parser.add_argument("--zip", required=True, help="Путь к ZIP архиву")
    parser.add_argument("--db", required=True, help="Имя базы данных")
    parser.add_argument("--data-path", default="C:\\Database_Backups", help="Путь для MDF/LDF файлов")
    parser.add_argument("--no-cleanup", action="store_true", help="Не удалять .bak")
    parser.add_argument("--server", default="localhost", help="SQL Server")
    parser.add_argument("--auth", default="sql", choices=["sql", "windows"], help="Тип аутентификации")
    parser.add_argument("--user", default="sa", help="SQL пользователь")
    parser.add_argument("--password", default="trbonet.com", help="SQL пароль")
    parser.add_argument("--silent", action="store_true", help="Не выводить логи")

    args = parser.parse_args()

    config = RestoreConfig(
        sql_server=args.server,
        auth_type=args.auth,
        sql_user=args.user,
        sql_password=args.password,
        backup_network_path=args.zip,
        database_name=args.db,
        data_path=args.data_path,
        cleanup_bak=not args.no_cleanup,
        silent=args.silent
    )

    result = restore_database(config)

    if result["success"]:
        print(f"\n✅ БАЗА ДАННЫХ ВОССТАНОВЛЕНА!")
        print(f"   Имя: {result['database_name']}")
        print(f"   Сервер: {result['server']}")
        print(f"   Время: {result['duration_seconds']:.1f} сек.")
        return 0
    else:
        print(f"\n❌ ОШИБКА: {result['message']}")
        return 1

if __name__ == "__main__":
    sys.exit(main_cli())