"""
Модуль функций проверки времени.

Содержит функции для определения текущего режима работы:
рабочее время, перерывы, внерабочее время.
"""

from typing import Tuple, Optional

from .. import utils
from .state import SimulationState


def is_work_hours(state: 'SimulationState') -> bool:
    """
    Проверяет, находимся ли мы в рабочее время.

    Args:
        state: Экземпляр состояния симуляции

    Returns:
        True если сейчас рабочее время
    """
    schedule = state.schedule
    current = utils.get_current_time_minutes()
    work_start = utils.time_str_to_minutes(schedule['work_start'])
    work_end = utils.time_str_to_minutes(schedule['work_end'])
    return work_start <= current <= work_end


def is_before_work(state: 'SimulationState') -> bool:
    """
    Проверяет, находимся ли мы ДО начала рабочего времени.

    Args:
        state: Экземпляр состояния симуляции

    Returns:
        True если сейчас до начала рабочего времени
    """
    schedule = state.schedule
    current = utils.get_current_time_minutes()
    work_start = utils.time_str_to_minutes(schedule['work_start'])
    return current < work_start


def is_after_work(state: 'SimulationState') -> bool:
    """
    Проверяем, находимся ли мы ПОСЛЕ окончания рабочего времени.

    Args:
        state: Экземпляр состояния симуляции

    Returns:
        True если сейчас после окончания рабочего времени
    """
    schedule = state.schedule
    current = utils.get_current_time_minutes()
    work_end = utils.time_str_to_minutes(schedule['work_end'])
    return current > work_end


def is_break_time(state: 'SimulationState') -> Tuple[bool, Optional[str]]:
    """
    Проверяет, сейчас ли время перерыва.

    Args:
        state: Экземпляр состояния симуляции

    Returns:
        Кортеж (is_break, break_type) где break_type - 'обед' или 'перерыв'
    """
    schedule = state.schedule
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


def is_after_lunch(state: 'SimulationState') -> bool:
    """
    Проверяем, находимся ли мы ПОСЛЕ обеденного перерыва.

    Args:
        state: Экземпляр состояния симуляции

    Returns:
        True если сейчас после обеденного перерыва
    """
    schedule = state.schedule
    current = utils.get_current_time_minutes()
    lunch_end = utils.time_str_to_minutes(schedule['lunch_end'])
    return current > lunch_end


def should_simulate_afterhours(state: 'SimulationState') -> bool:
    """
    Определяет, нужна ли активность вне рабочего времени.

    Args:
        state: Экземпляр состояния симуляции

    Returns:
        True если нужна активность вне рабочего времени
    """
    mode = state.config['afterhours_mode']

    if mode == 'disabled':
        return False
    elif mode == 'before_only':
        return is_before_work(state)
    elif mode == 'before_and_after':
        return not is_work_hours(state)

    return False
