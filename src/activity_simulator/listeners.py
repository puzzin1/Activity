"""
Модуль обработчиков событий мыши и клавиатуры.
Содержит функции-слушатели для отслеживания активности пользователя.
"""

from typing import Union, Optional, TYPE_CHECKING
import time
import sys

# Импортируем типы pynput только для проверки типов, не во время выполнения
if TYPE_CHECKING:
    from pynput.keyboard import Key, KeyCode
    from pynput.mouse import Button
else:
    # Заглушки для runtime
    Key = None  # type: ignore
    KeyCode = None  # type: ignore
    Button = None  # type: ignore

from . import simulation


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def _check_and_update_activity_after_work(state: Optional['simulation.SimulationState'] = None) -> bool:
    """
    Проверяет активность после рабочего дня и обновляет флаг.
    Возвращает True, если нужно прервать обработку (послерабочее время).

    Args:
        state: Экземпляр состояния симуляции (если None, используется глобальный)

    Returns:
        True если нужно прервать обработку
    """
    if state is None:
        state = simulation.get_state()
    if state.config.get('exit_on_activity_after_work', True) and simulation.is_after_work() and not simulation.is_work_hours():
        if not state.user_activity_after_work:
            state.user_activity_after_work = True
            simulation.log("🚪 Обнаружена активность пользователя после рабочего дня. Завершение программы.")
        return True
    return False


# === ФУНКЦИИ-СЛУШАТЕЛИ ===

def on_keyboard_event(key: Union[Key, KeyCode], state: Optional['simulation.SimulationState'] = None) -> None:
    """
    Обработчик нажатий клавиатуры.

    Args:
        key: Нажатая клавиша
        state: Экземпляр состояния симуляции (если None, используется глобальный)
    """
    if state is None:
        state = simulation.get_state()

    with state.lock:
        if state.is_performing_action:
            simulation.log(f"Игнорирование симулированного события клавиатуры", 'DEBUG')
            return

        if _check_and_update_activity_after_work(state):
            return

        state.last_activity_time = time.time()
        state.current_idle_threshold = None
        state.is_simulating = False
        state.absolute_anchor_position = None
        simulation.log(f"Обнаружена активность клавиатуры", 'DEBUG', state)


def on_mouse_event(x: int, y: int, state: Optional['simulation.SimulationState'] = None) -> None:
    """
    Обработчик движения мыши/тачпада.
    Автоматически отслеживает как движения мыши, так и тачпада.

    Args:
        x: Координата X
        y: Координата Y
        state: Экземпляр состояния симуляции (если None, используется глобальный)
    """
    if state is None:
        state = simulation.get_state()

    with state.lock:
        if state.is_performing_action:
            return

        if _check_and_update_activity_after_work(state):
            return

        # Обновляем время активности - программа не будет действовать минимум 60 секунд
        state.last_activity_time = time.time()
        state.initial_mouse_position = (x, y)
        state.current_idle_threshold = None
        state.is_simulating = False
        state.absolute_anchor_position = None

        current_time = time.time()
        if current_time - state.last_mouse_log_time >= 1.0:
            simulation.log(f"Обнаружено движение мыши пользователем", 'DEBUG', state)
            state.last_mouse_log_time = current_time


def on_mouse_click(x: int, y: int, button: Button, pressed: bool, state: Optional['simulation.SimulationState'] = None) -> None:
    """
    Обработчик кликов мыши/тачпада.
    Автоматически отслеживает как клики мыши, так и тапы тачпада.

    Args:
        x: Координата X
        y: Координата Y
        button: Нажатая кнопка
        pressed: True если нажата, False если отпущена
        state: Экземпляр состояния симуляции (если None, используется глобальный)
    """
    if state is None:
        state = simulation.get_state()

    if pressed:
        with state.lock:
            if state.is_performing_action:
                simulation.log(f"Игнорирование симулированного клика мыши", 'DEBUG', state)
                return

            if _check_and_update_activity_after_work(state):
                return

            state.last_activity_time = time.time()
            state.is_simulating = False
            state.current_idle_threshold = None
            state.absolute_anchor_position = None
            simulation.log(f"Обнаружен клик мыши", 'DEBUG', state)
