"""
Модуль обработчиков режимов симуляции.

Содержит функции для выполнения активности в разных режимах:
внерабочее время, перерывы.
"""

import random
import time
from typing import Optional, Callable, Tuple

from .state import get_state, MINIMUM_DELAY_AFTER_USER_ACTIVITY, MAX_CONSECUTIVE_SAFE_KEYS, get_mouse_controller
from .logger import log
from .actions import get_consecutive_safe_key_count, random_mouse_move, safe_key_press


def execute_burst_activity(
    last_burst_time_ref: list[float],
    burst_interval_min: int,
    burst_interval_max: int,
    burst_duration_min: int,
    burst_duration_max: int,
    mode_name: str,
    time_indicator: str = "",
    check_break_ended: Optional[Callable[[], Tuple[bool, Optional[str]]]] = None,
) -> str:
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
    state = get_state()
    config = state.config
    current_last_burst = last_burst_time_ref[0]
    time_since_burst = time.time() - current_last_burst
    burst_interval = random.uniform(
        burst_interval_min * 60,
        burst_interval_max * 60
    )

    # Проверяем, прошло ли минимум MINIMUM_DELAY_AFTER_USER_ACTIVITY секунд с последней активности пользователя
    with state.lock:
        time_since_user_activity = time.time() - state.last_activity_time

    if time_since_burst >= burst_interval and time_since_user_activity >= MINIMUM_DELAY_AFTER_USER_ACTIVITY:
        burst_duration = random.uniform(burst_duration_min, burst_duration_max)

        log(f"{time_indicator} {mode_name}: всплеск активности на {burst_duration:.0f} сек")

        burst_end_time = time.time() + burst_duration

        with state.lock:
            mouse_controller = get_mouse_controller()
            state.absolute_anchor_position = mouse_controller.position
            state.initial_mouse_position = mouse_controller.position
            state.is_simulating = True

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
            if state.user_activity_after_work:
                log(f"🚪 {mode_name}: прерывание всплеска из-за активности пользователя после рабочего дня")
                burst_interrupted = True
                with state.lock:
                    state.is_simulating = False
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

            with state.lock:
                state.last_activity_time = time.time()

            time.sleep(random.uniform(2, 5))
        else:
            # Цикл завершился без break (время всплеска истекло)
            burst_completed = True

        with state.lock:
            state.is_simulating = False

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
