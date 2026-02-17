"""
Модуль обработчиков событий мыши и клавиатуры.
Содержит функции-слушатели для отслеживания активности пользователя.
"""

import time
from pynput import mouse, keyboard
from pynput.mouse import Button
from pynput.keyboard import Key

from . import simulation


# === ФУНКЦИИ-СЛУШАТЕЛИ ===

def on_keyboard_event(key):
    """Обработчик нажатий клавиш клавиатуры"""
    with simulation.global_lock:
        if simulation.is_performing_action:
            simulation.log(f"Игнорирование симулированного события клавиатуры: {key}", 'DEBUG')
            return

        # Проверка активности после рабочего дня
        if simulation.CONFIG.get('exit_on_activity_after_work', True) and simulation.is_after_work() and not simulation.is_work_hours():
            simulation.user_activity_after_work = True
            simulation.log("🚪 Обнаружена активность пользователя после рабочего дня. Завершение программы.")
            return

        simulation.last_activity_time = time.time()
        simulation.current_idle_threshold = None
        simulation.is_simulating = False
        simulation.absolute_anchor_position = None
        simulation.log(f"Обнаружена активность клавиатуры: {key}", 'DEBUG')

def on_mouse_event(x, y):
    """
    Обработчик движения мыши/тачпада.
    Автоматически отслеживает как движения мыши, так и тачпада.
    """
    with simulation.global_lock:
        if simulation.is_performing_action:
            return

        # Проверка активности после рабочего дня
        if simulation.CONFIG.get('exit_on_activity_after_work', True) and simulation.is_after_work() and not simulation.is_work_hours():
            simulation.user_activity_after_work = True
            simulation.log("🚪 Обнаружена активность пользователя после рабочего дня. Завершение программы.")
            return

        # Обновляем время активности - программа не будет действовать минимум 60 секунд
        simulation.last_activity_time = time.time()
        simulation.initial_mouse_position = (x, y)
        simulation.current_idle_threshold = None
        simulation.is_simulating = False
        simulation.absolute_anchor_position = None

        current_time = time.time()
        if current_time - simulation.last_mouse_log_time >= 1.0:
            simulation.log(f"Обнаружено движение мыши пользователем: ({x}, {y})", 'DEBUG')
            simulation.last_mouse_log_time = current_time

def on_mouse_click(x, y, button, pressed):
    """
    Обработчик кликов мыши/тачпада.
    Автоматически отслеживает как клики мыши, так и тапы тачпада.
    """
    if pressed:
        with simulation.global_lock:
            if simulation.is_performing_action:
                simulation.log(f"Игнорирование симулированного клика мыши: {button}", 'DEBUG')
                return

            # Проверка активности после рабочего дня
            if simulation.CONFIG.get('exit_on_activity_after_work', True) and simulation.is_after_work() and not simulation.is_work_hours():
                simulation.user_activity_after_work = True
                simulation.log("🚪 Обнаружена активность пользователя после рабочего дня. Завершение программы.")
                return

            simulation.last_activity_time = time.time()
            simulation.is_simulating = False
            simulation.current_idle_threshold = None
            simulation.absolute_anchor_position = None
            simulation.log(f"Обнаружен клик мыши: {button} в ({x}, {y})", 'DEBUG')