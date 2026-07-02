"""
Модуль обработчиков событий мыши и клавиатуры.
Содержит функции-слушатели для отслеживания активности пользователя.
"""

from typing import Union, TYPE_CHECKING
import time
import sys

# Импортируем типы pynput только для проверки типов, не во время выполнения
if TYPE_CHECKING:
    from pynput.keyboard import Key, KeyCode
    from pynput.mouse import Button

from . import simulation


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def _check_and_update_activity_after_work(state: 'simulation.SimulationState') -> bool:
    """
    Проверяет активность после рабочего дня и обновляет флаг.
    Возвращает True, если нужно прервать обработку (послерабочее время).

    Args:
        state: Экземпляр состояния симуляции

    Returns:
        True если нужно прервать обработку
    """
    if state.config.get('exit_on_activity_after_work', True) and simulation.is_after_work(state) and not simulation.is_work_hours(state):
        if not state.user_activity_after_work:
            state.user_activity_after_work = True
            simulation.log("🚪 Обнаружена активность пользователя после рабочего дня. Завершение программы.")
        return True
    return False


# === ФУНКЦИИ-СЛУШАТЕЛИ ===

def on_keyboard_event(key: 'Union[Key, KeyCode]', injected: bool = False, state: 'simulation.SimulationState' = None) -> None:
    """
    Обработчик нажатий клавиатуры.

    Args:
        key: Нажатая клавиша
        state: Экземпляр состояния симуляции
    """
    try:
        with state.lock:
            if state.is_performing_action or time.time() < state.sim_action_grace_until:
                simulation.log(f"Игнорирование симулированного события клавиатуры", 'DEBUG')
                return

            if _check_and_update_activity_after_work(state):
                return

            state.last_activity_time = time.time()
            state.current_idle_threshold = None
            state.is_simulating = False
            state.absolute_anchor_position = None
            simulation.log(f"Обнаружена активность клавиатуры", 'DEBUG', state)
    except Exception as e:
        simulation.log(f"ОШИБКА в on_keyboard_event: {e}", 'ERROR')
        simulation.log(f"Тип state: {type(state)}, has lock: {hasattr(state, 'lock')}", 'ERROR')
        import traceback
        simulation.log(f"Traceback: {''.join(traceback.format_exc())}", 'ERROR')


def on_mouse_event(x: int, y: int, injected: bool = False, state: 'simulation.SimulationState' = None) -> None:
    """
    Обработчик движения мыши/тачпада.
    Автоматически отслеживает как движения мыши, так и тачпада.

    Args:
        x: Координата X
        y: Координата Y
        injected: True если событие инжектировано программой
        state: Экземпляр состояния симуляции
    """
    try:
        with state.lock:
            if state.is_performing_action or time.time() < state.sim_action_grace_until:
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
    except Exception as e:
        simulation.log(f"ОШИБКА в on_mouse_event: {e}", 'ERROR')
        simulation.log(f"Тип state: {type(state)}, has lock: {hasattr(state, 'lock')}", 'ERROR')
        import traceback
        simulation.log(f"Traceback: {''.join(traceback.format_exc())}", 'ERROR')


def on_mouse_scroll(x: int, y: int, dx: int, dy: int, injected: bool = False, state: 'simulation.SimulationState' = None) -> None:
    """
    Обработчик прокрутки колеса мыши/тачпада.

    Args:
        x: Координата X
        y: Координата Y
        dx: Горизонтальная прокрутка
        dy: Вертикальная прокрутка
        injected: True если событие инжектировано программой
        state: Экземпляр состояния симуляции
    """
    try:
        with state.lock:
            if state.is_performing_action or time.time() < state.sim_action_grace_until:
                return

            if _check_and_update_activity_after_work(state):
                return

            state.last_activity_time = time.time()
            state.is_simulating = False
            state.current_idle_threshold = None
            state.absolute_anchor_position = None
            simulation.log(f"Обнаружена прокрутка колеса мыши", 'DEBUG', state)
    except Exception as e:
        simulation.log(f"ОШИБКА в on_mouse_scroll: {e}", 'ERROR')
        simulation.log(f"Тип state: {type(state)}, has lock: {hasattr(state, 'lock')}", 'ERROR')
        import traceback
        simulation.log(f"Traceback: {''.join(traceback.format_exc())}", 'ERROR')


def on_mouse_click(x: int, y: int, button: 'Button', pressed: bool, injected: bool = False, state: 'simulation.SimulationState' = None) -> None:
    """
    Обработчик кликов мыши/тачпада.
    Автоматически отслеживает как клики мыши, так и тапы тачпада.

    Args:
        x: Координата X
        y: Координата Y
        button: Нажатая кнопка
        pressed: True если нажата, False если отпущена
        injected: True если событие инжектировано программой
        state: Экземпляр состояния симуляции
    """
    try:
        if pressed:
            with state.lock:
                if state.is_performing_action or time.time() < state.sim_action_grace_until:
                    simulation.log(f"Игнорирование симулированного клика мыши", 'DEBUG', state)
                    return

                if _check_and_update_activity_after_work(state):
                    return

                state.last_activity_time = time.time()
                state.is_simulating = False
                state.current_idle_threshold = None
                state.absolute_anchor_position = None
                simulation.log(f"Обнаружен клик мыши", 'DEBUG', state)
    except Exception as e:
        simulation.log(f"ОШИБКА в on_mouse_click: {e}", 'ERROR')
        simulation.log(f"Тип state: {type(state)}, has lock: {hasattr(state, 'lock')}", 'ERROR')
        import traceback
        simulation.log(f"Traceback: {''.join(traceback.format_exc())}", 'ERROR')
