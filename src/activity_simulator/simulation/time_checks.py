"""
Модуль функций проверки времени.

Содержит функции для определения текущего режима работы:
рабочее время, перерывы, внерабочее время.
"""

from typing import Tuple, Optional

from .. import utils
from .state import get_state


def is_work_hours() -> bool:
    """Проверяет, находимся ли мы в рабочее время"""
    schedule = get_state().schedule
    current = utils.get_current_time_minutes()
    work_start = utils.time_str_to_minutes(schedule['work_start'])
    work_end = utils.time_str_to_minutes(schedule['work_end'])
    return work_start <= current <= work_end


def is_before_work() -> bool:
    """Проверяет, находимся ли мы ДО начала рабочего времени"""
    schedule = get_state().schedule
    current = utils.get_current_time_minutes()
    work_start = utils.time_str_to_minutes(schedule['work_start'])
    return current < work_start


def is_after_work() -> bool:
    """Проверяем, находимся ли мы ПОСЛЕ окончания рабочего времени"""
    schedule = get_state().schedule
    current = utils.get_current_time_minutes()
    work_end = utils.time_str_to_minutes(schedule['work_end'])
    return current > work_end


def is_break_time() -> Tuple[bool, Optional[str]]:
    """Проверяет, сейчас ли время перерыва"""
    schedule = get_state().schedule
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
    schedule = get_state().schedule
    current = utils.get_current_time_minutes()
    lunch_end = utils.time_str_to_minutes(schedule['lunch_end'])
    return current > lunch_end


def should_simulate_afterhours() -> bool:
    """Определяет, нужна ли активность вне рабочего времени"""
    mode = get_state().config['afterhours_mode']

    if mode == 'disabled':
        return False
    elif mode == 'before_only':
        return is_before_work()
    elif mode == 'before_and_after':
        return not is_work_hours()

    return False
