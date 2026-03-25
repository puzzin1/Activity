"""
Модуль логгера на базе стандартной библиотеки logging.

Использует FileHandler для записи в файл, StreamHandler для вывода в консоль,
и RotatingFileHandler для ротации файлов.
"""

import logging
import logging.handlers
import os
from typing import Optional
from .state import get_state, SimulationState

# Глобальный логгер (инициализируется в main.py)
_logger: Optional[logging.Logger] = None


def get_logger() -> Optional[logging.Logger]:
    """Возвращает глобальный экземпляр логгера."""
    return _logger


def init_logger(file_path: str, enabled: bool = True, verbose: bool = True, state: Optional['SimulationState'] = None) -> None:
    """
    Инициализирует глобальный логгер с FileHandler и StreamHandler.

    Args:
        file_path: Путь к файлу лога
        enabled: Включен ли логгер
        verbose: Включено ли подробное логирование
        state: Экземпляр состояния симуляции (если None, используется глобальный)
    """
    global _logger

    # Получаем или создаём логгер
    _logger = logging.getLogger('activity_simulator')
    _logger.setLevel(logging.DEBUG)
    _logger.handlers.clear()

    if not enabled:
        _logger.addHandler(logging.NullHandler())
        return

    # Форматирование сообщений
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # FileHandler - все уровни
    try:
        file_handler = logging.FileHandler(file_path, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        _logger.addHandler(file_handler)
    except (OSError, IOError, PermissionError) as e:
        print(f"Ошибка открытия лог-файла: {e}")
        _logger.addHandler(logging.NullHandler())
        return

    # StreamHandler - только WARNING и ERROR
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    _logger.addHandler(console_handler)

    # Сохраняем путь к файлу в состоянии
    state = get_state()
    state.log_file_path = file_path


def close_logger() -> None:
    """Закрывает глобальный логгер."""
    global _logger
    if _logger:
        for handler in _logger.handlers[:]:
            handler.close()
            _logger.removeHandler(handler)
        _logger = None


def _mask_sensitive_data(message: str) -> str:
    """
    Маскирует конфиденциальные данные в сообщении лога.

    Args:
        message: Исходное сообщение

    Returns:
        Сообщение с замаскированными секретами
    """
    import re

    # Маскируем значения переменных окружения в f-строках типа: '...'
    if re.search(r"env_var_name\s*=\s*['\"](.*?)['\"]", message):
        message = re.sub(r"(env_var_name\s*=\s*['\"])(.*?)(['\"])", r"\1***\3", message)

    # Маскируем имена переменных окружения в сообщениях о последовательностях
    if re.search(r"after_lunch_sequence['\"]?:\s*['\"](.*?)['\"]", message):
        message = re.sub(r"(['\"]?after_lunch_sequence['\"]?:\s*['\"])(.*?)(['\"])", r"\1***\3", message)

    # Маскируем значение последовательности клавиш (если попало в лог)
    if re.search(r"sequence['\"]?:\s*['\"][^'\"]{3,}['\"]", message):
        message = re.sub(r"(['\"]?sequence['\"]?:\s*['\"])([^'\"]{3,})(['\"])", r"\1***\3", message)

    # Маскируем имя переменной окружения в сообщении "Переменная окружения: ..."
    if re.search(r"Переменная окружения:\s*(.+)", message):
        message = re.sub(r"(Переменная окружения:\s*)(.+)", r"\1***", message)

    # Маскируем значение переменной окружения в конце строки (для шаблонов типа f"... {env_var_name}")
    if re.search(r"env_var_name$", message):
        message = "***"

    return message


def log(message: str, level: str = 'INFO', state: Optional['SimulationState'] = None) -> None:
    """
    Функция для логирования.

    Args:
        message: Сообщение для логирования
        level: Уровень логирования (INFO, WARNING, ERROR, DEBUG)
        state: Экземпляр состояния симуляции (если None, используется глобальный)
    """
    # Маскируем конфиденциальные данные
    message = _mask_sensitive_data(message)

    if _logger is None:
        # Fallback: прямой вывод если логгер не инициализирован
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] [{level}] {message}"

        if level in ['ERROR', 'WARNING']:
            print(log_message)
        return

    # Преобразуем уровень в константу logging
    log_level = getattr(logging, level.upper(), logging.INFO)
    _logger.log(log_level, message)


def setup_log_rotation(state: Optional['SimulationState'] = None) -> None:
    """
    Настраивает RotatingFileHandler для ротации лог-файлов.

    Ротация происходит на основе количества файлов (max_files) из конфигурации.

    Args:
        state: Экземпляр состояния симуляции (если None, используется глобальный)
    """
    from ..config import rotate_files

    if state is None:
        state = get_state()
    config = state.config
    if not config or _logger is None:
        return

    max_log_files = config.get('max_log_files', 5)
    if max_log_files <= 0:
        return

    # Ротация через удаление старых файлов
    rotate_files('.', 'activity_log_*.txt', max_log_files,
                 'лог-файл', exclude_file=os.path.basename(state.log_file_path))
