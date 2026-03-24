"""
Модуль буферизованного логгера.

Содержит класс BufferedLogger для снижения количества операций ввода-вывода
и функции для управления логгером.
"""

from typing import List, TextIO, Optional
from datetime import datetime
import time
from threading import Lock
import os

from .state import get_state


# === КЛАСС БУФЕРИЗОВАННОГО ЛОГГАРА ===

class BufferedLogger:
    """
    Буферизованный логгер для снижения количества операций ввода-вывода.

    Накапливает сообщения в памяти и записывает их в файл периодически
    или при достижении определенного количества сообщений.
    """

    # Параметры буферизации
    FLUSH_INTERVAL: float = 5.0  # Интервал flush в секундах
    BUFFER_SIZE: int = 100  # Максимальный размер буфера сообщений

    file_path: str
    enabled: bool
    _buffer: List[str]
    _last_flush_time: float
    _lock: Lock
    _file_handle: Optional[TextIO]

    def __init__(self, file_path: str, enabled: bool = True) -> None:
        """
        Инициализирует буферизованный логгер.

        Args:
            file_path: Путь к файлу лога
            enabled: Включен ли логгер
        """
        self.file_path = file_path
        self.enabled = enabled
        self._buffer = []
        self._last_flush_time = time.time()
        self._lock = Lock()
        self._file_handle = None

        # Открываем файл в режиме добавления
        if self.enabled:
            try:
                self._file_handle = open(file_path, 'a', encoding='utf-8')
            except (OSError, IOError, PermissionError) as e:
                print(f"Ошибка открытия лог-файла: {e}")
                self.enabled = False

    def log(self, message: str, level: str = 'INFO') -> None:
        """
        Добавляет сообщение в буфер лога.

        Args:
            message: Сообщение для логирования
            level: Уровень логирования (INFO, WARNING, ERROR, DEBUG)
        """
        if not self.enabled:
            return

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] [{level}] {message}"

        # Выводим в консоль только ERROR и WARNING
        if level in ['ERROR', 'WARNING']:
            print(log_message)

        with self._lock:
            self._buffer.append(log_message)

            # Важные сообщения выводим немедленно
            if level in ['ERROR', 'WARNING']:
                self._flush_buffer()
            # Или при достижении размера буфера
            elif len(self._buffer) >= self.BUFFER_SIZE:
                self._flush_buffer()
            # Или по интервалу времени
            elif time.time() - self._last_flush_time >= self.FLUSH_INTERVAL:
                self._flush_buffer()

    def _flush_buffer(self) -> None:
        """Записывает все сообщения из буфера в файл."""
        if not self._buffer or not self._file_handle:
            return

        try:
            for msg in self._buffer:
                self._file_handle.write(msg + '\n')
            self._file_handle.flush()
        except (OSError, IOError, PermissionError) as e:
            print(f"Ошибка записи в лог-файл: {e}")

        self._buffer.clear()
        self._last_flush_time = time.time()

    def close(self) -> None:
        """Закрывает логгер, записывая все оставшиеся сообщения."""
        with self._lock:
            if self._file_handle:
                try:
                    self._flush_buffer()
                    self._file_handle.close()
                except Exception as e:
                    print(f"Ошибка закрытия лог-файла: {e}")
                finally:
                    self._file_handle = None


# Глобальный экземпляр логгера (инициализируется в main.py)
_logger: Optional[BufferedLogger] = None


def log(message: str, level: str = 'INFO') -> None:
    """
    Функция для логирования через буферизованный логгер.

    Args:
        message: Сообщение для логирования
        level: Уровень логирования (INFO, WARNING, ERROR, DEBUG)
    """
    if _logger:
        _logger.log(message, level)
    else:
        # Fallback: прямой вывод если логгер не инициализирован
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] [{level}] {message}"

        if level in ['ERROR', 'WARNING']:
            print(log_message)

        state = get_state()
        if state.config.get('verbose_logging', True):
            try:
                with open(state.log_file_path, 'a', encoding='utf-8') as f:
                    f.write(log_message + '\n')
            except (OSError, IOError, PermissionError) as e:
                print(f"Ошибка записи в лог-файл: {e}")


def init_logger(file_path: str, enabled: bool = True) -> None:
    """
    Инициализирует глобальный логгер.

    Args:
        file_path: Путь к файлу лога
        enabled: Включен ли логгер
    """
    global _logger
    _logger = BufferedLogger(file_path, enabled)
    state = get_state()
    state.log_file_path = file_path


def close_logger() -> None:
    """Закрывает глобальный логгер."""
    global _logger
    if _logger:
        _logger.close()
        _logger = None


def setup_log_rotation() -> None:
    """Выполняет ротацию лог-файлов на основе настроек конфигурации"""
    from ..config import rotate_files

    state = get_state()
    config = state.config
    if config:
        max_log_files = config.get('max_log_files', 5)
        rotate_files('.', 'activity_log_*.txt', max_log_files,
                     'лог-файл', exclude_file=os.path.basename(state.log_file_path))
