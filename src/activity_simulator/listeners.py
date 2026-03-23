"""
Модуль обработчиков событий мыши и клавиатуры.
Содержит функции-слушатели для отслеживания активности пользователя.
"""

from typing import Union
import time
from pynput import mouse, keyboard
from pynput.mouse import Button
from pynput.keyboard import Key, KeyCode

from . import simulation


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def _check_and_update_activity_after_work() -> bool:
    """
    Проверяет активность после рабочего дня и обновляет флаг.
    Возвращает True, если нужно прервать обработку (послерабочее время).
    """
    if simulation.CONFIG.get('exit_on_activity_after_work', True) and simulation.is_after_work() and not simulation.is_work_hours():
        if not simulation.user_activity_after_work:
            simulation.user_activity_after_work = True
            simulation.log("🚪 Обнаружена активность пользователя после рабочего дня. Завершение программы.")
        return True
    return False


# === ФУНКЦИИ-СЛУШАТЕЛИ ===

def on_keyboard_event(key: Union[Key, KeyCode]) -> None:
    """Обработчик нажатий клавиатуры"""
    with simulation.global_lock:
        if simulation.is_performing_action:
            simulation.log(f"Игнорирование симулированного события клавиатуры", 'DEBUG')
            return

        if _check_and_update_activity_after_work():
            return

        simulation.last_activity_time = time.time()
        simulation.current_idle_threshold = None
        simulation.is_simulating = False
        simulation.absolute_anchor_position = None
        simulation.log(f"Обнаружена активность клавиатуры", 'DEBUG')


def on_mouse_event(x: int, y: int) -> None:
    """
    Обработчик движения мыши/тачпада.
    Автоматически отслеживает как движения мыши, так и тачпада.
    """
    with simulation.global_lock:
        if simulation.is_performing_action:
            return

        if _check_and_update_activity_after_work():
            return

        # Обновляем время активности - программа не будет действовать минимум 60 секунд
        simulation.last_activity_time = time.time()
        simulation.initial_mouse_position = (x, y)
        simulation.current_idle_threshold = None
        simulation.is_simulating = False
        simulation.absolute_anchor_position = None

        current_time = time.time()
        if current_time - simulation.last_mouse_log_time >= 1.0:
            simulation.log(f"Обнаружено движение мыши пользователем", 'DEBUG')
            simulation.last_mouse_log_time = current_time


def on_mouse_click(x: int, y: int, button: Button, pressed: bool) -> None:
    """
    Обработчик кликов мыши/тачпада.
    Автоматически отслеживает как клики мыши, так и тапы тачпада.
    """
    if pressed:
        with simulation.global_lock:
            if simulation.is_performing_action:
                simulation.log(f"Игнорирование симулированного клика мыши", 'DEBUG')
                return

            if _check_and_update_activity_after_work():
                return

            simulation.last_activity_time = time.time()
            simulation.is_simulating = False
            simulation.current_idle_threshold = None
            simulation.absolute_anchor_position = None
            simulation.log(f"Обнаружен клик мыши", 'DEBUG')