"""
Модуль управления состоянием симуляции.

Содержит класс SimulationState для инкапсуляции глобального состояния,
константы и исключения.
"""

from typing import Optional, Tuple
from threading import Lock
from pynput.mouse import Controller
from pynput.keyboard import Controller as KeyboardController
from collections import deque


# === ИМЕНОВАННЫЕ КОНСТАНТЫ ===

# Минимальная задержка в секундах после активности пользователя
MINIMUM_DELAY_AFTER_USER_ACTIVITY: int = 60

# Максимальное количество подряд идущих safe_key действий
MAX_CONSECUTIVE_SAFE_KEYS: int = 4

# Порог очистки истории действий
ACTION_HISTORY_CLEAR_THRESHOLD: int = 100


# === КЛАССЫ ИСКЛЮЧЕНИЙ ===

class ExitSimulation(Exception):
    """
    Исключение для корректного выхода из симуляции.

    Позволяет заменить os._exit() на более чистый механизм выхода,
    который позволяет корректно завершить все потоки и слушатели.
    """
    def __init__(self, message, should_lock=False, should_shutdown=False, show_warning=True):
        super().__init__(message)
        self.should_lock = should_lock
        self.should_shutdown = should_shutdown
        self.show_warning = show_warning


# Контроллеры ввода (глобальные, так как используются только для чтения)
mouse_controller: Controller = Controller()
keyboard_controller: KeyboardController = KeyboardController()


# === КЛАСС ИНКАПСУЛЯЦИИ ГЛОБАЛЬНОГО СОСТОЯНИЯ ===

class SimulationState:
    """
    Инкапсулирует глобальное состояние симуляции.

    Обеспечивает потокобезопасный доступ к общим переменным через
    методы с блокировкой, вместо прямого обращения к глобальным переменным.
    """

    # Контроллеры ввода (ссылки на глобальные)
    mouse_controller: Controller
    keyboard_controller: KeyboardController

    def __init__(self) -> None:
        """Инициализирует состояние симуляции с начальными значениями."""
        self._lock: Lock = Lock()
        self._last_activity_time: float = 0.0
        self._initial_mouse_position: Optional[Tuple[int, int]] = None
        self._absolute_anchor_position: Optional[Tuple[int, int]] = None
        self._is_simulating: bool = False
        self._is_performing_action: bool = False
        self._action_history: deque[Tuple[str, float]] = deque(maxlen=ACTION_HISTORY_CLEAR_THRESHOLD)
        self._current_idle_threshold: Optional[int] = None
        self._last_mouse_log_time: float = 0.0
        self._lunch_sequence_executed: bool = False
        self._shutdown_cancelled: bool = False
        self._user_activity_after_work: bool = False
        self._simulation_finished: bool = False
        self._last_break_burst_time: Optional[float] = None
        self._log_file_path: str = ""
        self._config: dict = {}
        self._schedule: dict = {}

    # === Свойства для доступа к состоянию ===

    @property
    def lock(self) -> Lock:
        """Возвращает блокировку для внешнего использования (например, в контекстных менеджерах)."""
        return self._lock

    @property
    def last_activity_time(self) -> float:
        """Время последней активности пользователя."""
        return self._last_activity_time

    @last_activity_time.setter
    def last_activity_time(self, value: float) -> None:
        self._last_activity_time = value

    @property
    def initial_mouse_position(self) -> Optional[Tuple[int, int]]:
        """Начальная позиция мыши."""
        return self._initial_mouse_position

    @initial_mouse_position.setter
    def initial_mouse_position(self, value: Optional[Tuple[int, int]]) -> None:
        self._initial_mouse_position = value

    @property
    def absolute_anchor_position(self) -> Optional[Tuple[int, int]]:
        """Референсная точка для ограничений движения мыши."""
        return self._absolute_anchor_position

    @absolute_anchor_position.setter
    def absolute_anchor_position(self, value: Optional[Tuple[int, int]]) -> None:
        self._absolute_anchor_position = value

    @property
    def is_simulating(self) -> bool:
        """Флаг, указывающий, что симуляция активна."""
        return self._is_simulating

    @is_simulating.setter
    def is_simulating(self, value: bool) -> None:
        self._is_simulating = value

    @property
    def is_performing_action(self) -> bool:
        """Флаг, указывающий, что действие выполняется."""
        return self._is_performing_action

    @is_performing_action.setter
    def is_performing_action(self, value: bool) -> None:
        self._is_performing_action = value

    @property
    def action_history(self) -> deque[Tuple[str, float]]:
        """История выполненных действий."""
        return self._action_history

    @property
    def log_file_path(self) -> str:
        """Путь к файлу лога."""
        return self._log_file_path

    @log_file_path.setter
    def log_file_path(self, value: str) -> None:
        self._log_file_path = value

    @property
    def current_idle_threshold(self) -> Optional[int]:
        """Текущий порог бездействия."""
        return self._current_idle_threshold

    @current_idle_threshold.setter
    def current_idle_threshold(self, value: Optional[int]) -> None:
        self._current_idle_threshold = value

    @property
    def last_mouse_log_time(self) -> float:
        """Время последнего лога движения мыши."""
        return self._last_mouse_log_time

    @last_mouse_log_time.setter
    def last_mouse_log_time(self, value: float) -> None:
        self._last_mouse_log_time = value

    @property
    def lunch_sequence_executed(self) -> bool:
        """Флаг выполнения последовательности после обеда."""
        return self._lunch_sequence_executed

    @lunch_sequence_executed.setter
    def lunch_sequence_executed(self, value: bool) -> None:
        self._lunch_sequence_executed = value

    @property
    def shutdown_cancelled(self) -> bool:
        """Флаг отмены выключения."""
        return self._shutdown_cancelled

    @shutdown_cancelled.setter
    def shutdown_cancelled(self, value: bool) -> None:
        self._shutdown_cancelled = value

    @property
    def user_activity_after_work(self) -> bool:
        """Флаг активности пользователя после работы."""
        return self._user_activity_after_work

    @user_activity_after_work.setter
    def user_activity_after_work(self, value: bool) -> None:
        self._user_activity_after_work = value

    @property
    def simulation_finished(self) -> bool:
        """Флаг завершения симуляции."""
        return self._simulation_finished

    @simulation_finished.setter
    def simulation_finished(self, value: bool) -> None:
        self._simulation_finished = value

    @property
    def last_break_burst_time(self) -> Optional[float]:
        """Время последнего всплеска во время перерыва."""
        return self._last_break_burst_time

    @last_break_burst_time.setter
    def last_break_burst_time(self, value: Optional[float]) -> None:
        self._last_break_burst_time = value

    # === Методы для работы с конфигурацией и расписанием ===

    @property
    def config(self) -> dict:
        """Конфигурация программы (только для чтения после инициализации)."""
        return self._config

    def set_config(self, config: dict) -> None:
        """Устанавливает конфигурацию (вызывается один раз при запуске)."""
        with self._lock:
            self._config = config.copy()

    @property
    def schedule(self) -> dict:
        """Расписание рабочего дня (только для чтения после инициализации)."""
        return self._schedule

    def set_schedule(self, schedule: dict) -> None:
        """Устанавливает расписание (вызывается один раз при запуске)."""
        with self._lock:
            self._schedule = schedule.copy()

    # === Контекстный менеджер для работы с блокировкой ===

    def __enter__(self):
        """Вход в контекст с блокировкой."""
        self._lock.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Выход из контекста с разблокировкой."""
        self._lock.release()


# Глобальный экземпляр состояния симуляции
_state: SimulationState = SimulationState()


def get_state() -> SimulationState:
    """Возвращает глобальный экземпляр состояния симуляции."""
    return _state
