"""
Основной модуль симуляции активности.
Содержит логику симуляции, функции выполнения действий и главный цикл.
"""

from typing import Optional, List, Tuple, Union, TextIO, Any
import time
import random
import os
import sys
import signal
import platform
import subprocess
import tkinter as tk
from tkinter import messagebox
from collections import deque
from threading import Thread, Lock, Timer
from pynput import mouse, keyboard
from pynput.mouse import Controller, Button
from pynput.keyboard import Controller as KeyboardController, Key
from datetime import datetime

from . import config
from . import utils
from .config import rotate_files


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


# Настройка контроллеров (глобальные, так как используются только для чтения)
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
        self._last_activity_time: float = time.time()
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
        self._log_file_path: str = f"activity_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
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

def setup_log_rotation() -> None:
    """Выполняет ротацию лог-файлов на основе настроек конфигурации"""
    config = _state.config
    if config:
        max_log_files = config.get('max_log_files', 5)
        rotate_files('.', 'activity_log_*.txt', max_log_files,
                     'лог-файл', exclude_file=os.path.basename(_state.log_file_path))


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
_logger: BufferedLogger = None


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

        if _state.config.get('verbose_logging', True):
            try:
                with open(_state.log_file_path, 'a', encoding='utf-8') as f:
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
    _state.log_file_path = file_path


def close_logger() -> None:
    """Закрывает глобальный логгер."""
    global _logger
    if _logger:
        _logger.close()
        _logger = None

# === ФУНКЦИИ ПРОВЕРКИ ВРЕМЕНИ ===

def is_work_hours() -> bool:
    """Проверяет, находимся ли мы в рабочее время"""
    schedule = _state.schedule
    current = utils.get_current_time_minutes()
    work_start = utils.time_str_to_minutes(schedule['work_start'])
    work_end = utils.time_str_to_minutes(schedule['work_end'])
    return work_start <= current <= work_end

def is_before_work() -> bool:
    """Проверяет, находимся ли мы ДО начала рабочего времени"""
    schedule = _state.schedule
    current = utils.get_current_time_minutes()
    work_start = utils.time_str_to_minutes(schedule['work_start'])
    return current < work_start

def is_after_work() -> bool:
    """Проверяем, находимся ли мы ПОСЛЕ окончания рабочего времени"""
    schedule = _state.schedule
    current = utils.get_current_time_minutes()
    work_end = utils.time_str_to_minutes(schedule['work_end'])
    return current > work_end

def is_break_time() -> Tuple[bool, Optional[str]]:
    """Проверяет, сейчас ли время перерыва"""
    schedule = _state.schedule
    current = utils.get_current_time_minutes()

    # Проверяем обед
    lunch_start = utils.time_str_to_minutes(schedule['lunch_start'])
    lunch_end = utils.time_str_to_minutes(schedule['lunch_end'])
    if lunch_start <= current <= lunch_end:
        return True, 'обед'

    # Проверяем другие перерывы
    for brk in schedule['breaks']:
        break_start = utils.time_str_to_minutes(brk['start'])
        break_end = utils.time_str_to_minutes(brk['end'])
        if break_start <= current <= break_end:
            return True, 'перерыв'

    return False, None

def is_after_lunch() -> bool:
    """Проверяем, находимся ли мы ПОСЛЕ обеденного перерыва"""
    schedule = _state.schedule
    current = utils.get_current_time_minutes()
    lunch_end = utils.time_str_to_minutes(schedule['lunch_end'])
    return current > lunch_end


def should_simulate_afterhours() -> bool:
    """Определяет, нужна ли активность вне рабочего времени"""
    mode = _state.config['afterhours_mode']

    if mode == 'disabled':
        return False
    elif mode == 'before_only':
        return is_before_work()
    elif mode == 'before_and_after':
        return not is_work_hours()

    return False


def type_key_sequence(sequence: str) -> None:
    """
    Вводит последовательность клавиш, включая специальные клавиши.

    Args:
        sequence (str): Строка с последовательностью, например "text{Enter}{Tab}"
    """
    if not sequence:
        return

    with _state.lock:
        if _state.user_activity_after_work:
            return

    log(f"🔑 Начало ввода последовательности клавиш")

    with _state.lock:
        _state.is_performing_action = True

    try:
        parsed = utils.parse_key_sequence(sequence)

        for element in parsed:
            # Проверяем, является ли элемент специальной клавишей
            if element == "Enter":
                keyboard_controller.press(Key.enter)
                time.sleep(0.05)
                keyboard_controller.release(Key.enter)
                log(f"  • Нажата клавиша")
                time.sleep(random.uniform(0.1, 0.3))

            elif element == "Tab":
                keyboard_controller.press(Key.tab)
                time.sleep(0.05)
                keyboard_controller.release(Key.tab)
                log(f"  • Нажата клавиша")
                time.sleep(random.uniform(0.1, 0.3))

            elif element == "Space":
                keyboard_controller.press(Key.space)
                time.sleep(0.05)
                keyboard_controller.release(Key.space)
                log(f"  • Нажата клавиша")
                time.sleep(random.uniform(0.05, 0.15))

            else:
                # Обычный текст - вводим посимвольно
                for char in element:
                    keyboard_controller.type(char)
                    time.sleep(random.uniform(0.05, 0.15))  # Задержка между символами

                log(f"  • Введен текст: {'*' * len(element)}")  # Маскируем текст в логе

        log(f"✅ Последовательность клавиш введена успешно")

    except Exception as e:
        log(f"❌ Ошибка при вводе последовательности: {e}", 'ERROR')

    finally:
        with _state.lock:
            _state.is_performing_action = False


def show_shutdown_warning() -> bool:
    """Показывает всплывающее окно с предупреждением о выключении"""
    timer = None

    def on_cancel():
        nonlocal timer
        _state.shutdown_cancelled = True
        log("⚠️ Выключение отменено пользователем")
        if timer is not None:
            try:
                timer.cancel()
            except:
                pass
        root.destroy()

    def on_timeout():
        try:
            root.destroy()
        except:
            pass

    # Создаем окно
    root = tk.Tk()
    root.title("⚠️ Предупреждение")
    root.geometry("400x200")
    root.resizable(False, False)

    # Поднимаем окно поверх всех
    root.attributes('-topmost', True)
    root.lift()
    root.focus_force()

    # Центрируем окно
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (400 // 2)
    y = (root.winfo_screenheight() // 2) - (200 // 2)
    root.geometry(f"+{x}+{y}")

    # Текст предупреждения
    warning_text = f"⚠️ ВНИМАНИЕ!\n\nРабочий день завершен.\n"

    if _state.config.get('shutdown_on_exit', False):
        warning_text += f"Компьютер будет ВЫКЛЮЧЕН через {_state.config.get('shutdown_warning_time', 30)} секунд."
    else:
        warning_text += f"Компьютер будет ЗАБЛОКИРОВАН через {_state.config.get('shutdown_warning_time', 30)} секунд."

    label = tk.Label(root, text=warning_text, font=("Arial", 12), pady=20)
    label.pack()

    # Кнопка отмены
    cancel_btn = tk.Button(root, text="Отменить", command=on_cancel,
                          font=("Arial", 12), bg="#ff4444", fg="white",
                          padx=20, pady=10)
    cancel_btn.pack(pady=10)

    # Автоматическое закрытие через заданное время
    timer = Timer(_state.config.get('shutdown_warning_time', 30), on_timeout)
    timer.daemon = True
    timer.start()

    # Запускаем окно
    root.mainloop()

    return not _state.shutdown_cancelled


# === ФУНКЦИИ ВЫПОЛНЕНИЯ ДЕЙСТВИЙ ===

def get_consecutive_safe_key_count() -> int:
    """Возвращает количество подряд идущих safe_key действий в конце истории"""
    count = 0
    # Идем с конца истории и считаем последовательные safe_key
    for action_type, _ in reversed(_state._state.action_history):
        if action_type == 'safe_key':
            count += 1
        else:
            break
    return count

def move_mouse_naturally(target_x: int, target_y: int) -> None:
    """Плавное перемещение мыши к целевой позиции"""
    start_pos = mouse_controller.position
    dx = target_x - start_pos[0]
    dy = target_y - start_pos[1]
    config = _state.config
    steps = config['smooth_move_steps']

    with _state.lock:
        _state.is_performing_action = True
        action_start_time = _state.last_activity_time

    for step in range(steps):
        # Проверяем активность пользователя на каждом шаге
        with _state.lock:
            if _state.last_activity_time > action_start_time:
                # Пользователь проявил активность - прерываем движение
                # Добавляем запись в историю, чтобы сбросить счетчик последовательных safe_key
                _state._state.action_history.append(('mouse_move', time.time()))
                _state.is_performing_action = False
                _state.is_simulating = False
                log(f"⚠️ Движение мыши прервано активностью пользователя (шаг {step}/{steps})", 'INFO')
                return
            # Проверка активности пользователя после работы
            if _state.user_activity_after_work:
                _state._state.action_history.append(('mouse_move', time.time()))
                _state.is_performing_action = False
                _state.is_simulating = False
                log(f"🚪 Движение мыши прервано активностью пользователя после рабочего дня (шаг {step}/{steps})", 'INFO')
                return

        t = step / steps
        if config['natural_behavior']:
            # Кривая ease-in-out для более естественного движения
            t = t * t * (3 - 2 * t)

        new_x = start_pos[0] + (dx * t)
        new_y = start_pos[1] + (dy * t)
        mouse_controller.position = (new_x, new_y)

        sleep_time = config['smooth_move_duration'] / steps
        if config['natural_behavior'] and random.random() < 0.1:
            sleep_time *= random.uniform(1.2, 1.5)

        time.sleep(sleep_time)

    mouse_controller.position = (target_x, target_y)

    with _state.lock:
        _state.is_performing_action = False

def random_mouse_move() -> None:
    """Случайное движение мыши в пределах заданного диапазона"""
    config = _state.config
    max_range_relative = config['max_mouse_range']

    if config['natural_behavior']:
        # Треугольное распределение дает больше движений ближе к центру
        offset_x = random.randint(-max_range_relative, max_range_relative) * random.triangular(0.1, 1.0, 0.4)
        offset_y = random.randint(-max_range_relative, max_range_relative) * random.triangular(0.1, 1.0, 0.4)
        offset_x = int(offset_x)
        offset_y = int(offset_y)
    else:
        offset_x = random.randint(-max_range_relative, max_range_relative)
        offset_y = random.randint(-max_range_relative, max_range_relative)

    target_x = _state.initial_mouse_position[0] + offset_x
    target_y = _state.initial_mouse_position[1] + offset_y

    # Ограничение дрифта от начальной точки симуляции
    with _state.lock:
        if _state.absolute_anchor_position is not None:
            anchor_x = _state.absolute_anchor_position[0]
            anchor_y = _state.absolute_anchor_position[1]
            max_abs_range = config['max_mouse_range']

            target_x = max(anchor_x - max_abs_range, min(target_x, anchor_x + max_abs_range))
            target_y = max(anchor_y - max_abs_range, min(target_y, anchor_y + max_abs_range))

    log(f"Движение мыши: ({_state.initial_mouse_position[0]}, {_state.initial_mouse_position[1]}) -> ({target_x}, {target_y})")
    move_mouse_naturally(target_x, target_y)
    _state._state.action_history.append(('mouse_move', time.time()))

    _state.initial_mouse_position = mouse_controller.position

def random_arrow_press() -> None:
    """Нажатие клавиш-стрелок (имитация прокрутки/навигации)"""
    config = _state.config

    if config['natural_behavior']:
        # Больший вес для up/down (вертикальная прокрутка популярнее)
        arrows = [Key.up, Key.down, Key.up, Key.down, Key.left, Key.right]
    else:
        arrows = [Key.up, Key.down, Key.left, Key.right]

    arrow = random.choice(arrows)

    repetitions = random.randint(config['min_key_presses'], config['max_key_presses'])
    log(f"Нажатие стрелки (x{repetitions})")

    with _state.lock:
        _state.is_performing_action = True
        action_start_time = _state.last_activity_time

    for i in range(repetitions):
        # Проверяем, не было ли активности пользователя
        with _state.lock:
            if _state.last_activity_time > action_start_time:
                # Пользователь проявил активность - прерываем серию
                log(f"⚠️ Серия нажатий прервана активностью пользователя (выполнено {i}/{repetitions})", 'INFO')
                # Добавляем запись в историю, чтобы сбросить счетчик последовательных safe_key
                _state._state.action_history.append(('keyboard', time.time()))
                _state.is_performing_action = False
                _state.is_simulating = False
                return
            # Проверка активности пользователя после работы
            if _state.user_activity_after_work:
                log(f"🚪 Серия нажатий прервана активностью пользователя после рабочего дня (выполнено {i}/{repetitions})", 'INFO')
                _state.is_performing_action = False
                _state.is_simulating = False
                return

        keyboard_controller.press(arrow)
        time.sleep(random.uniform(0.05, 0.15))
        keyboard_controller.release(arrow)

        if i < repetitions - 1:
            time.sleep(random.uniform(0.1, 0.3))

    with _state.lock:
        _state.is_performing_action = False
    _state._state.action_history.append(('keyboard', time.time()))

def random_mouse_click() -> None:
    """Клик левой кнопкой мыши в текущей позиции"""
    with _state.lock:
        if _state.user_activity_after_work:
            return
    log(f"Клик левой кнопкой мыши в текущей позиции")

    with _state.lock:
        _state.is_performing_action = True

    mouse_controller.click(Button.left, 1)

    with _state.lock:
        _state.is_performing_action = False
    _state._state.action_history.append(('mouse_click', time.time()))

def safe_key_press() -> None:
    """Нажатие безопасной клавиши (Shift) - не производит побочных эффектов"""
    with _state.lock:
        if _state.user_activity_after_work:
            return
    log(f"Нажатие безопасной клавиши")

    with _state.lock:
        _state.is_performing_action = True

    keyboard_controller.press(Key.shift)
    time.sleep(0.05)
    keyboard_controller.release(Key.shift)

    with _state.lock:
        _state.is_performing_action = False
    _state._state.action_history.append(('safe_key', time.time()))

def control_tab_press() -> None:
    """Нажатие Ctrl+Tab (переключение вкладок)"""
    log(f"Нажатие комбинации клавиш")

    with _state.lock:
        _state.is_performing_action = True
        action_start_time = _state.last_activity_time

    keyboard_controller.press(Key.ctrl_l)
    time.sleep(random.uniform(0.05, 0.15))

    # Проверяем активность пользователя перед нажатием Tab
    with _state.lock:
        if _state.last_activity_time > action_start_time:
            # Пользователь проявил активность - отменяем действие
            keyboard_controller.release(Key.ctrl_l)
            # Добавляем запись в историю, чтобы сбросить счетчик последовательных safe_key
            _state._state.action_history.append(('ctrl_tab', time.time()))
            _state.is_performing_action = False
            _state.is_simulating = False
            log(f"⚠️ Комбинация клавиш прервана активностью пользователя", 'INFO')
            return
        # Проверка активности пользователя после работы
        if _state.user_activity_after_work:
            keyboard_controller.release(Key.ctrl_l)
            _state._state.action_history.append(('ctrl_tab', time.time()))
            _state.is_performing_action = False
            _state.is_simulating = False
            log(f"🚪 Комбинация клавиш прервана активностью пользователя после рабочего дня", 'INFO')
            return

    keyboard_controller.press(Key.tab)
    time.sleep(random.uniform(0.1, 0.2))
    keyboard_controller.release(Key.tab)
    time.sleep(random.uniform(0.05, 0.15))
    keyboard_controller.release(Key.ctrl_l)

    with _state.lock:
        _state.is_performing_action = False
    _state._state.action_history.append(('ctrl_tab', time.time()))


# === ФУНКЦИИ ОБРАБОТЧИКИ РЕЖИМОВ ===

def _execute_burst_activity(last_burst_time_ref: Optional[float],
                            burst_interval_min: int,
                            burst_interval_max: int,
                              burst_duration_min, burst_duration_max, mode_name,
                              time_indicator="", check_break_ended=None):
    """
    Универсальная функция выполнения всплеска активности.

    Используется как для внерабочего режима, так и для режима перерывов.

    Args:
        last_burst_time_ref: list - [время] для изменяемой ссылки (используем список для мутации)
        burst_interval_min: int - мин. интервал между всплесками в минутах
        burst_interval_max: int - макс. интервал между всплесками в минутах
        burst_duration_min: int - мин. продолжительность всплеска в секундах
        burst_duration_max: int - макс. продолжительность всплеска в секундах
        mode_name: str - название режима для логов (например, "Внерабочий", "Перерыв")
        time_indicator: str - emoji индикатор времени (например, "🌅", "🌙")
        check_break_ended: callable или None - функция для проверки окончания перерыва

    Returns:
        str: 'completed', 'interrupted', 'ended', или 'waiting'
    """
    config = _state.config
    current_last_burst = last_burst_time_ref[0]
    time_since_burst = time.time() - current_last_burst
    burst_interval = random.uniform(
        burst_interval_min * 60,
        burst_interval_max * 60
    )

    # Проверяем, прошло ли минимум MINIMUM_DELAY_AFTER_USER_ACTIVITY секунд с последней активности пользователя
    with _state.lock:
        time_since_user_activity = time.time() - _state.last_activity_time

    if time_since_burst >= burst_interval and time_since_user_activity >= MINIMUM_DELAY_AFTER_USER_ACTIVITY:
        burst_duration = random.uniform(burst_duration_min, burst_duration_max)

        log(f"{time_indicator} {mode_name}: всплеск активности на {burst_duration:.0f} сек")

        burst_end_time = time.time() + burst_duration

        with _state.lock:
            _state.absolute_anchor_position = mouse_controller.position
            _state.initial_mouse_position = mouse_controller.position
            _state.is_simulating = True

        burst_interrupted = False
        burst_completed = False

        while time.time() < burst_end_time:
            # Проверяем, не закончился ли перерыв (если есть проверка)
            if check_break_ended is not None:
                on_break_check, _ = check_break_ended()
                if not on_break_check:
                    log(f"☕ Перерыв завершился. Выход из режима перерыва.")
                    return 'ended'

            # Проверка активности пользователя после работы
            if _state.user_activity_after_work:
                log(f"🚪 {mode_name}: прерывание всплеска из-за активности пользователя после рабочего дня")
                burst_interrupted = True
                with _state.lock:
                    _state.is_simulating = False
                break

            # Выполняем легкую активность
            # Избегаем 5 подряд нажатий Shift
            consecutive_safe_keys = get_consecutive_safe_key_count()
            available_actions = []

            # Проверяем, доступно ли движение мыши
            if config['use_mouse_move']:
                available_actions.append('mouse_move')

            # Всегда добавляем safe_key, но ограничим если уже 4 подряд
            if consecutive_safe_keys < MAX_CONSECUTIVE_SAFE_KEYS:
                available_actions.append('safe_key')

            # Если доступных действий нет - все равно добавляем safe_key
            if not available_actions:
                available_actions.append('safe_key')
                log(f"⚠️ {mode_name}: вынужденно используем safe_key (уже {consecutive_safe_keys} подряд)", 'DEBUG')

            action = random.choice(available_actions)

            try:
                if action == 'mouse_move':
                    random_mouse_move()
                elif action == 'safe_key':
                    safe_key_press()
            except Exception as e:
                log(f"Ошибка при выполнении действия: {e}", 'ERROR')

            with _state.lock:
                _state.last_activity_time = time.time()

            time.sleep(random.uniform(2, 5))
        else:
            # Цикл завершился без break (время всплеска истекло)
            burst_completed = True

        with _state.lock:
            _state.is_simulating = False

        if burst_interrupted:
            return 'interrupted'

        if burst_completed:
            last_burst_time_ref[0] = time.time()
            log(f"{time_indicator} {mode_name}: всплеск активности завершен. Следующий через {burst_interval/60:.1f} мин")
            return 'completed'

    elif time_since_user_activity < MINIMUM_DELAY_AFTER_USER_ACTIVITY:
        # Ждем, пока не пройдет минимальная задержка после активности пользователя
        remaining = MINIMUM_DELAY_AFTER_USER_ACTIVITY - time_since_user_activity
        log(f"⏸️  Ожидание после активности пользователя: {remaining:.1f} сек", 'DEBUG')
        time.sleep(10)

    return 'waiting'


# === ГЛАВНАЯ ФУНКЦИЯ СИМУЛЯЦИИ ===

def simulate_activity() -> None:
    """Основной цикл симуляции активности"""
    last_burst_time = time.time()
    last_break_burst_time_list = [time.time()]  # Используем список для мутации
    config = _state.config

    while True:
        # Проверка активности пользователя после работы
        if _state.user_activity_after_work:
            log("🚪 Завершение программы из-за активности пользователя после рабочего дня")
            print("\n" + "=" * 70)
            print("🚪 ОБНАРУЖЕНА АКТИВНОСТЬ ПОЛЬЗОВАТЕЛЯ")
            print("=" * 70)
            print("Программа завершена без блокировки/выключения компьютера")
            if config['verbose_logging']:
                print(f"📄 Лог сохранён в файл: {_state.log_file_path}")
            print("=" * 70)
            time.sleep(1)
            _state.simulation_finished = True
            raise ExitSimulation("Активность пользователя после рабочего дня")

        # Проверяем режим работы
        in_work_hours = is_work_hours()
        on_break, break_type = is_break_time()

        # === ПРОВЕРКА И ВЫПОЛНЕНИЕ ДЕЙСТВИЙ ПОСЛЕ ОБЕДА ===
        if config.get('after_lunch_action', False) and not _state.lunch_sequence_executed:
            # Проверяем, прошел ли обед и находимся ли мы после него
            if in_work_hours and is_after_lunch() and not on_break:
                log(f"🍽️ Обеденный перерыв завершен. Ожидание {config.get('after_lunch_delay', 5)} сек...")
                time.sleep(config.get('after_lunch_delay', 5))

                # Вводим последовательность клавиш
                sequence = config.get('after_lunch_sequence', '')
                if sequence:
                    type_key_sequence(sequence)
                    _state.lunch_sequence_executed = True

                    # Обновляем время активности
                    with _state.lock:
                        _state.last_activity_time = time.time()
                else:
                    log(f"⚠️ Последовательность после обеда не задана", 'WARNING')
                    _state.lunch_sequence_executed = True

        # === РЕЖИМ ВНЕ РАБОЧЕГО ВРЕМЕНИ ===
        if not in_work_hours:
            # Проверяем, нужна ли активность вне рабочего времени
            if not should_simulate_afterhours():
                # Проверка активности пользователя после работы
                if _state.user_activity_after_work:
                    log("🚪 Обнаружена активность пользователя после рабочего дня. Завершение программы.")
                    print("\n" + "=" * 70)
                    print("🚪 ОБНАРУЖЕНА АКТИВНОСТЬ ПОЛЬЗОВАТЕЛЯ")
                    print("=" * 70)
                    print("Программа завершена без блокировки/выключения компьютера")
                    if config['verbose_logging']:
                        print(f"📄 Лог сохранён в файл: {_state.log_file_path}")
                    print("=" * 70)
                    time.sleep(1)
                    _state.simulation_finished = True
                    raise ExitSimulation("Активность пользователя после рабочего дня (внерабочий)")
                # Если мы ПОСЛЕ работы и активность отключена - завершаем программу
                if is_after_work():
                    log(f"🏁 Рабочий день завершен. Программа останавливается (режим: {config['afterhours_mode']})")

                    # Показываем предупреждение, если включено
                    should_proceed = True
                    if config.get('show_shutdown_warning', True):
                        print(f"\n⏰ Показ предупреждения о завершении работы...")
                        log("⏰ Показ предупреждения о завершении работы")
                        should_proceed = show_shutdown_warning()

                    if not should_proceed or _state.shutdown_cancelled:
                        log("✋ Завершение работы отменено пользователем")
                        print("\n✋ Завершение работы отменено")
                        # Продолжаем работу в режиме ожидания
                        time.sleep(60)
                        _state.shutdown_cancelled = False
                        with _state.lock:
                            _state.user_activity_after_work = False
                        continue

                    print("\n" + "=" * 70)
                    print("🏁 РАБОЧИЙ ДЕНЬ ЗАВЕРШЕН")
                    print("=" * 70)
                    print(f"⏰ Время окончания: {datetime.now().strftime('%H:%M:%S')}")
                    if config['verbose_logging']:
                        print(f"📄 Лог сохранён в файл: {_state.log_file_path}")

                    # Логируем статистику в файл
                    log(f"Всего выполнено действий: {len(_state._state.action_history)}")

                    # Выключение или блокировка компьютера при АВТОМАТИЧЕСКОМ завершении
                    if config.get('shutdown_on_exit', False):
                        print("🔌 ВЫКЛЮЧЕНИЕ КОМПЬЮТЕРА...")
                        time.sleep(1)
                        success, message = utils.shutdown_computer()
                        log(message)
                    elif config.get('lock_on_exit', True):
                        print("🔒 Блокировка компьютера...")
                        time.sleep(1)
                        success, message = utils.lock_computer()
                        log(message)

                    print("=" * 70)
                    time.sleep(1)  # Задержка перед завершением
                    _state.simulation_finished = True
                    raise ExitSimulation("Рабочий день завершен", show_warning=False)

                # Если мы ДО работы - просто ждем
                if _state.is_simulating:
                    with _state.lock:
                        _state.is_simulating = False
                    log(f"🌙 Внерабочее время. Активность отключена (режим: {config['afterhours_mode']})")
                time.sleep(60)
                continue

            # Режим всплесков активности
            time_since_burst = time.time() - last_burst_time
            burst_interval = random.uniform(
                config['afterhours_burst_interval_min'] * 60,
                config['afterhours_burst_interval_max'] * 60
            )

            # Проверяем, прошло ли минимум MINIMUM_DELAY_AFTER_USER_ACTIVITY секунд с последней активности пользователя
            with _state.lock:
                time_since_user_activity = time.time() - _state.last_activity_time

            if time_since_burst >= burst_interval and time_since_user_activity >= MINIMUM_DELAY_AFTER_USER_ACTIVITY:
                burst_duration = random.uniform(
                    config['afterhours_burst_duration_min'],
                    config['afterhours_burst_duration_max']
                )

                time_indicator = "🌅" if is_before_work() else "🌙"
                log(f"{time_indicator} Внерабочий режим: всплеск активности на {burst_duration:.0f} сек")

                burst_end_time = time.time() + burst_duration

                with _state.lock:
                    _state.absolute_anchor_position = mouse_controller.position
                    _state.initial_mouse_position = mouse_controller.position
                    _state.is_simulating = True

                burst_interrupted = False
                while time.time() < burst_end_time:
                    # Проверка активности пользователя после работы
                    with _state.lock:
                        if _state.user_activity_after_work:
                            log("🚪 Внерабочий режим: прерывание всплеска из-за активности пользователя после рабочего дня")
                            burst_interrupted = True
                            with _state.lock:
                                _state.is_simulating = False
                            break
                    # Выполняем легкую активность
                    # Избегаем 5 подряд нажатий Shift
                    consecutive_safe_keys = get_consecutive_safe_key_count()
                    available_actions = []

                    # Проверяем, доступно ли движение мыши
                    if config['use_mouse_move']:
                        available_actions.append('mouse_move')

                    # Всегда добавляем safe_key, но ограничим если уже 4 подряд
                    if consecutive_safe_keys < MAX_CONSECUTIVE_SAFE_KEYS:
                        available_actions.append('safe_key')

                    # Если доступных действий нет (use_mouse_move=false и consecutive_safe_keys>=4)
                    # то все равно добавляем safe_key, чтобы программа не зависла
                    if not available_actions:
                        available_actions.append('safe_key')
                        log(f"⚠️ Внерабочий режим: вынужденно используем safe_key (уже {consecutive_safe_keys} подряд)", 'DEBUG')

                    action = random.choice(available_actions)

                    try:
                        if action == 'mouse_move':
                            random_mouse_move()
                        elif action == 'safe_key':
                            safe_key_press()
                    except Exception as e:
                        log(f"Ошибка при выполнении действия: {e}", 'ERROR')

                    with _state.lock:
                        _state.last_activity_time = time.time()

                    time.sleep(random.uniform(2, 5))

                with _state.lock:
                    _state.is_simulating = False

                if burst_interrupted:
                    continue

                last_burst_time = time.time()
                log(f"{time_indicator} Всплеск активности завершен. Следующий через {burst_interval/60:.1f} мин")
            elif time_since_user_activity < MINIMUM_DELAY_AFTER_USER_ACTIVITY:
                # Ждем, пока не пройдет минимальная задержка после активности пользователя
                remaining = MINIMUM_DELAY_AFTER_USER_ACTIVITY - time_since_user_activity
                log(f"⏸️  Ожидание после активности пользователя: {remaining:.1f} сек", 'DEBUG')
                time.sleep(10)

            time.sleep(10)
            continue

        # === РЕЖИМ ПЕРЕРЫВА ===
        if on_break:
            if _state.is_simulating:
                with _state.lock:
                    _state.is_simulating = False
                log(f"☕ Перерыв ({break_type}). Переход в режим легкой активности.")

            # Логика всплесков активности во время перерыва (аналогично внерабочему режиму)
            time_since_break_burst = time.time() - last_break_burst_time
            burst_interval = random.uniform(
                config['afterhours_burst_interval_min'] * 60,
                config['afterhours_burst_interval_max'] * 60
            )

            # Проверяем, прошло ли минимум MINIMUM_DELAY_AFTER_USER_ACTIVITY секунд с последней активности пользователя
            with _state.lock:
                time_since_user_activity = time.time() - _state.last_activity_time

            if time_since_break_burst >= burst_interval and time_since_user_activity >= MINIMUM_DELAY_AFTER_USER_ACTIVITY:
                burst_duration = random.uniform(
                    config['afterhours_burst_duration_min'],
                    config['afterhours_burst_duration_max']
                )

                log(f"☕ Перерыв ({break_type}): всплеск активности на {burst_duration:.0f} сек")

                burst_end_time = time.time() + burst_duration

                with _state.lock:
                    _state.absolute_anchor_position = mouse_controller.position
                    _state.initial_mouse_position = mouse_controller.position
                    _state.is_simulating = True

                burst_completed = False
                break_ended = False
                burst_interrupted = False

                while time.time() < burst_end_time:
                    # Проверяем, не закончился ли перерыв
                    on_break_check, break_type_check = is_break_time()
                    if not on_break_check:
                        log(f"☕ Перерыв завершился. Выход из режима перерыва.")
                        break_ended = True
                        break

                    # Проверка активности пользователя после работы
                    with _state.lock:
                        if _state.user_activity_after_work:
                            log("🚪 Режим перерыва: прерывание всплеска из-за активности пользователя после рабочего дня")
                            burst_interrupted = True
                            break

                    # Выполняем легкую активность
                    # Избегаем 5 подряд нажатий Shift
                    consecutive_safe_keys = get_consecutive_safe_key_count()
                    available_actions = []

                    # Проверяем, доступно ли движение мыши
                    if config['use_mouse_move']:
                        available_actions.append('mouse_move')

                    # Всегда добавляем safe_key, но ограничим если уже 4 подряд
                    if consecutive_safe_keys < MAX_CONSECUTIVE_SAFE_KEYS:
                        available_actions.append('safe_key')

                    # Если доступных действий нет (use_mouse_move=false и consecutive_safe_keys>=4)
                    # то все равно добавляем safe_key, чтобы программа не зависла
                    if not available_actions:
                        available_actions.append('safe_key')
                        log(f"⚠️ Режим перерыва: вынужденно используем safe_key (уже {consecutive_safe_keys} подряд)", 'DEBUG')

                    action = random.choice(available_actions)

                    try:
                        if action == 'mouse_move':
                            random_mouse_move()
                        elif action == 'safe_key':
                            safe_key_press()
                    except Exception as e:
                        log(f"Ошибка при выполнении действия: {e}", 'ERROR')

                    with _state.lock:
                        _state.last_activity_time = time.time()

                    time.sleep(random.uniform(2, 5))
                else:
                    # Цикл завершился без break (время всплеска истекло)
                    burst_completed = True

                with _state.lock:
                    _state.is_simulating = False

                if burst_interrupted:
                    continue

                if break_ended:
                    # Перерыв закончился досрочно, не обновляем время последнего всплеска
                    # и переходим к следующей итерации главного цикла
                    continue

                if burst_completed:
                    last_break_burst_time = time.time()
                    log(f"☕ Перерыв ({break_type}): всплеск активности завершен. Следующий через {burst_interval/60:.1f} мин")
            elif time_since_user_activity < MINIMUM_DELAY_AFTER_USER_ACTIVITY:
                # Ждем, пока не пройдет минимальная задержка после активности пользователя
                remaining = MINIMUM_DELAY_AFTER_USER_ACTIVITY - time_since_user_activity
                log(f"⏸️  Ожидание после активности пользователя: {remaining:.1f} сек", 'DEBUG')
                time.sleep(10)

            time.sleep(10)
            continue

        # === ОБЫЧНЫЙ РАБОЧИЙ РЕЖИМ ===
        with _state.lock:
            time_since_last_activity = time.time() - _state.last_activity_time
            current_idle_threshold_local = _state.current_idle_threshold
            _state.is_simulating = _state.is_simulating

        # Генерация нового порога бездействия
        if current_idle_threshold_local is None:
            new_threshold = random.randint(config['min_idle_time'], config['max_idle_time'])
            with _state.lock:
                _state.current_idle_threshold = new_threshold
                current_idle_threshold_local = _state.current_idle_threshold
            log(f"Установлен новый порог бездействия: {current_idle_threshold_local} сек", 'DEBUG')

        # КРИТИЧЕСКИ ВАЖНО: Минимальная задержка MINIMUM_DELAY_AFTER_USER_ACTIVITY секунд после любой активности пользователя
        # Проверка необходимости симуляции
        # Программа начинает действовать только если:
        # 1. Прошло минимум 60 секунд с последней активности пользователя
        # 2. И прошло достаточно времени согласно порогу бездействия
        if time_since_last_activity >= MINIMUM_DELAY_AFTER_USER_ACTIVITY and \
           (_state.is_simulating or time_since_last_activity >= current_idle_threshold_local):

            # Начало симуляции
            if not _state.is_simulating:
                with _state.lock:
                    _state.absolute_anchor_position = mouse_controller.position
                    _state.initial_mouse_position = mouse_controller.position
                    _state.is_simulating = True
                    _state.is_simulating = True
                log(f"💼 Начало симуляции активности (бездействие: {time_since_last_activity:.1f} сек)")

            # Формирование списка доступных действий с весами
            available_actions = []

            if config['use_mouse_move']:
                available_actions.extend(['mouse_move'] * config['action_weight_mouse_move'])

            if config['use_keyboard']:
                available_actions.extend(['keyboard'] * config['action_weight_keyboard'])
                available_actions.extend(['ctrl_tab'] * config['action_weight_ctrl_tab'])

            if config['use_mouse_click']:
                available_actions.extend(['mouse_click'] * config['action_weight_mouse_click'])

            if config['natural_behavior']:
                available_actions.extend(['safe_key'] * config['action_weight_safe_key'])

            if not available_actions:
                available_actions = ['safe_key']

            # Проверка: избегаем 5 подряд нажатий Shift
            consecutive_safe_keys = get_consecutive_safe_key_count()
            if consecutive_safe_keys >= MAX_CONSECUTIVE_SAFE_KEYS and 'safe_key' in available_actions:
                # Удаляем все 'safe_key' из списка доступных действий
                available_actions = [a for a in available_actions if a != 'safe_key']
                log(f"⚠️ Избегаем 5-го подряд нажатия Shift (уже {consecutive_safe_keys} подряд)", 'DEBUG')

            # Если после удаления safe_key список пуст, добавляем обратно одно действие
            # (лучше безопасная клавиша, чем ничего)
            if not available_actions:
                available_actions = ['safe_key']
                log(f"⚠️ Нет других доступных действий, оставляем safe_key", 'DEBUG')

            # Выбор и выполнение действия
            action = random.choice(available_actions)
            log(f"Выбрано действие: {action}")

            try:
                if action == 'mouse_move':
                    random_mouse_move()
                elif action == 'keyboard':
                    random_arrow_press()
                elif action == 'mouse_click':
                    random_mouse_click()
                elif action == 'safe_key':
                    safe_key_press()
                elif action == 'ctrl_tab':
                    control_tab_press()
            except Exception as e:
                log(f"Ошибка при выполнении действия: {e}", 'ERROR')

            # Обновление времени активности
            with _state.lock:
                _state.last_activity_time = time.time()

            # Расчет паузы до следующего действия
            action_interval = random.uniform(
                config['min_action_interval'],
                config['max_action_interval']
            )

            # Случайное увеличение паузы для естественности
            if config['natural_behavior'] and random.random() < 0.15:
                action_interval *= random.uniform(1.5, 2.5)
                log(f"Увеличенная пауза: {action_interval:.1f} сек", 'DEBUG')

            log(f"Следующее действие через {action_interval:.1f} сек", 'DEBUG')
            time.sleep(action_interval)

        else:
            # Режим ожидания
            if _state.is_simulating:
                 with _state.lock:
                    if not _state.is_simulating:
                        log("Симуляция прервана активностью пользователя.", 'INFO')

            # Показываем оставшееся время с учетом минимальной задержки
            if time_since_last_activity < MINIMUM_DELAY_AFTER_USER_ACTIVITY:
                remaining = MINIMUM_DELAY_AFTER_USER_ACTIVITY - time_since_last_activity
                log(f"Ожидание после активности пользователя. Осталось: {remaining:.1f} сек", 'DEBUG')
            else:
                remaining = current_idle_threshold_local - time_since_last_activity
                log(f"Ожидание бездействия. Осталось: {remaining:.1f} сек", 'DEBUG')

            time.sleep(1)


# === ФУНКЦИЯ СТАТИСТИКИ ===

def show_stats() -> None:
    """Периодический вывод статистики выполненных действий"""
    while True:
        time.sleep(300)  # Каждые 5 минут
        if len(_state._state.action_history) > 0:
            recent = [a for a in _state._state.action_history if time.time() - a[1] < 3600]
            log(f"[Статистика] Действий за последний час: {len(recent)}")