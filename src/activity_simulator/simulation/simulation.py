"""
Главный модуль симуляции активности.

Содержит главный цикл симуляции и функцию инициализации.
"""

import time
import random
from datetime import datetime

from .state import get_state, MINIMUM_DELAY_AFTER_USER_ACTIVITY, MAX_CONSECUTIVE_SAFE_KEYS, mouse_controller
from .logger import log
from .time_checks import (
    is_work_hours, is_before_work, is_after_work,
    is_break_time, is_after_lunch, should_simulate_afterhours,
)
from .actions import (
    type_key_sequence, random_mouse_move, random_arrow_press,
    random_mouse_click, safe_key_press, control_tab_press,
    show_shutdown_warning, get_consecutive_safe_key_count,
)
from .modes import execute_burst_activity


def init_simulation(config: dict, schedule: dict) -> None:
    """
    Инициализирует состояние симуляции конфигурацией и расписанием.

    Args:
        config: Конфигурация программы
        schedule: Расписание рабочего дня
    """
    state = get_state()
    state.set_config(config)
    state.set_schedule(schedule)
    state.last_activity_time = time.time()
    state.program_start_time = time.time()


def simulate_activity() -> None:
    """Основной цикл симуляции активности"""
    last_burst_time = time.time()
    last_break_burst_time_list = [time.time()]  # Используем список для мутации

    while True:
        state = get_state()
        config = state.config

        # Проверка: прошло ли 60 секунд с момента запуска программы
        # Первое симулированное действие не ранее 60 сек после запуска
        time_since_start = time.time() - state.program_start_time
        if time_since_start < MINIMUM_DELAY_AFTER_USER_ACTIVITY:
            time.sleep(1)
            continue

        # Проверка активности пользователя после работы
        if state.user_activity_after_work:
            log("🚪 Завершение программы из-за активности пользователя после рабочего дня")
            print("\n" + "=" * 70)
            print("🚪 ОБНАРУЖЕНА АКТИВНОСТЬ ПОЛЬЗОВАТЕЛЯ")
            print("=" * 70)
            print("Программа завершена без блокировки/выключения компьютера")
            if config['verbose_logging']:
                print(f"📄 Лог сохранён в файл: {state.log_file_path}")
            print("=" * 70)
            time.sleep(1)
            state.simulation_finished = True
            from .state import ExitSimulation
            raise ExitSimulation("Активность пользователя после рабочего дня")

        # Проверяем режим работы
        in_work_hours = is_work_hours()
        on_break, break_type = is_break_time()

        # === ПРОВЕРКА И ВЫПОЛНЕНИЕ ДЕЙСТВИЙ ПОСЛЕ ОБЕДА ===
        if config.get('after_lunch_action', False) and not state.lunch_sequence_executed:
            # Проверяем, прошел ли обед и находимся ли мы после него
            if in_work_hours and is_after_lunch() and not on_break:
                log(f"🍽️ Обеденный перерыв завершен. Ожидание {config.get('after_lunch_delay', 5)} сек...")
                time.sleep(config.get('after_lunch_delay', 5))

                # Вводим последовательность клавиш
                sequence = config.get('after_lunch_sequence', '')
                if sequence:
                    type_key_sequence(sequence)
                    state.lunch_sequence_executed = True

                    # Обновляем время активности
                    with state.lock:
                        state.last_activity_time = time.time()
                else:
                    log(f"⚠️ Последовательность после обеда не задана", 'WARNING')
                    state.lunch_sequence_executed = True

        # === РЕЖИМ ВНЕ РАБОЧЕГО ВРЕМЕНИ ===
        if not in_work_hours:
            # Проверяем, нужна ли активность вне рабочего времени
            if not should_simulate_afterhours():
                # Если мы ПОСЛЕ работы и активность отключена - завершаем программу
                if is_after_work():
                    _handle_work_day_finished()

                # Если мы ДО работы - просто ждем
                if state.is_simulating:
                    with state.lock:
                        state.is_simulating = False
                    log(f"🌙 Внерабочее время. Активность отключена (режим: {config['afterhours_mode']})")
                time.sleep(60)
                continue

            # Режим всплесков активности
            _handle_afterhours_burst(last_burst_time)
            continue

        # === РЕЖИМ ПЕРЕРЫВА ===
        if on_break:
            if state.is_simulating:
                with state.lock:
                    state.is_simulating = False
                log(f"☕ Перерыв ({break_type}). Переход в режим легкой активности.")

            # Логика всплесков активности во время перерыва
            _handle_break_burst(last_break_burst_time_list)
            continue

        # === ОБЫЧНЫЙ РАБОЧИЙ РЕЖИМ ===
        _handle_work_mode()
        continue


def _handle_work_day_finished() -> None:
    """Обрабатывает завершение рабочего дня"""
    state = get_state()
    config = state.config

    log(f"🏁 Рабочий день завершен. Программа останавливается (режим: {config['afterhours_mode']})")

    # Показываем предупреждение, если включено
    should_proceed = True
    if config.get('show_shutdown_warning', True):
        print(f"\n⏰ Показ предупреждения о завершении работы...")
        log("⏰ Показ предупреждения о завершении работы")
        should_proceed = show_shutdown_warning()

    if not should_proceed or state.shutdown_cancelled:
        log("✋ Завершение работы отменено пользователем")
        print("\n✋ Завершение работы отменено")
        # Продолжаем работу в режиме ожидания
        time.sleep(60)
        state.shutdown_cancelled = False
        with state.lock:
            state.user_activity_after_work = False
        return

    print("\n" + "=" * 70)
    print("🏁 РАБОЧИЙ ДЕНЬ ЗАВЕРШЕН")
    print("=" * 70)
    print(f"⏰ Время окончания: {datetime.now().strftime('%H:%M:%S')}")
    if config['verbose_logging']:
        print(f"📄 Лог сохранён в файл: {state.log_file_path}")

    # Логируем статистику в файл
    log(f"Всего выполнено действий: {len(state.action_history)}")

    # Выключение или блокировка компьютера при АВТОМАТИЧЕСКОМ завершении
    from .. import utils

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
    state.simulation_finished = True
    from .state import ExitSimulation
    raise ExitSimulation("Рабочий день завершен", show_warning=False)


def _handle_afterhours_burst(last_burst_time: float) -> None:
    """Обрабатывает всплеск активности внерабочего режима"""
    state = get_state()
    config = state.config

    time_since_burst = time.time() - last_burst_time
    burst_interval = random.uniform(
        config['afterhours_burst_interval_min'] * 60,
        config['afterhours_burst_interval_max'] * 60
    )

    # Проверяем, прошло ли минимум MINIMUM_DELAY_AFTER_USER_ACTIVITY секунд
    with state.lock:
        time_since_user_activity = time.time() - state.last_activity_time

    if time_since_burst >= burst_interval and time_since_user_activity >= MINIMUM_DELAY_AFTER_USER_ACTIVITY:
        burst_duration = random.uniform(
            config['afterhours_burst_duration_min'],
            config['afterhours_burst_duration_max']
        )

        time_indicator = "🌅" if is_before_work() else "🌙"
        log(f"{time_indicator} Внерабочий режим: всплеск активности на {burst_duration:.0f} сек")

        burst_end_time = time.time() + burst_duration

        with state.lock:
            # mouse_controller импортирован на верхнем уровне
            state.absolute_anchor_position = mouse_controller.position
            state.initial_mouse_position = mouse_controller.position
            state.is_simulating = True

        burst_interrupted = False
        while time.time() < burst_end_time:
            # Проверка активности пользователя после работы
            with state.lock:
                if state.user_activity_after_work:
                    log("🚪 Внерабочий режим: прерывание всплеска из-за активности пользователя после рабочего дня")
                    burst_interrupted = True
                    state.is_simulating = False
                    break

            _perform_light_action()

            time.sleep(random.uniform(2, 5))

        with state.lock:
            state.is_simulating = False

        if not burst_interrupted:
            last_burst_time = time.time()
            log(f"{time_indicator} Всплеск активности завершен. Следующий через {burst_interval/60:.1f} мин")

    elif time_since_user_activity < MINIMUM_DELAY_AFTER_USER_ACTIVITY:
        # Ждем, пока не пройдет минимальная задержка после активности пользователя
        remaining = MINIMUM_DELAY_AFTER_USER_ACTIVITY - time_since_user_activity
        log(f"⏸️  Ожидание после активности пользователя: {remaining:.1f} сек", 'DEBUG')
        time.sleep(10)

    time.sleep(10)


def _handle_break_burst(last_break_burst_time_list: list) -> None:
    """Обрабатывает всплеск активности во время перерыва"""
    state = get_state()
    config = state.config

    time_since_break_burst = time.time() - last_break_burst_time_list[0]
    burst_interval = random.uniform(
        config['afterhours_burst_interval_min'] * 60,
        config['afterhours_burst_interval_max'] * 60
    )

    # Проверяем, прошло ли минимум MINIMUM_DELAY_AFTER_USER_ACTIVITY секунд
    with state.lock:
        time_since_user_activity = time.time() - state.last_activity_time

    if time_since_break_burst >= burst_interval and time_since_user_activity >= MINIMUM_DELAY_AFTER_USER_ACTIVITY:
        burst_duration = random.uniform(
            config['afterhours_burst_duration_min'],
            config['afterhours_burst_duration_max']
        )

        on_break_check, break_type_check = is_break_time()
        log(f"☕ Перерыв ({break_type_check}): всплеск активности на {burst_duration:.0f} сек")

        burst_end_time = time.time() + burst_duration

        with state.lock:
            # mouse_controller импортирован на верхнем уровне
            state.absolute_anchor_position = mouse_controller.position
            state.initial_mouse_position = mouse_controller.position
            state.is_simulating = True

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
            with state.lock:
                if state.user_activity_after_work:
                    log("🚪 Режим перерыва: прерывание всплеска из-за активности пользователя после рабочего дня")
                    burst_interrupted = True
                    break

            _perform_light_action()

            time.sleep(random.uniform(2, 5))
        else:
            # Цикл завершился без break (время всплеска истекло)
            burst_completed = True

        with state.lock:
            state.is_simulating = False

        if burst_interrupted:
            return

        if break_ended:
            # Перерыв закончился досрочно, не обновляем время последнего всплеска
            return

        if burst_completed:
            last_break_burst_time_list[0] = time.time()
            log(f"☕ Перерыв ({break_type_check}): всплеск активности завершен. Следующий через {burst_interval/60:.1f} мин")

    elif time_since_user_activity < MINIMUM_DELAY_AFTER_USER_ACTIVITY:
        # Ждем, пока не пройдет минимальная задержка после активности пользователя
        remaining = MINIMUM_DELAY_AFTER_USER_ACTIVITY - time_since_user_activity
        log(f"⏸️  Ожидание после активности пользователя: {remaining:.1f} сек", 'DEBUG')
        time.sleep(10)

    time.sleep(10)


def _perform_light_action() -> None:
    """Выполняет легкое действие (используется в перерывах и внерабочем режиме)"""
    # MAX_CONSECUTIVE_SAFE_KEYS уже импортирован из state

    state = get_state()
    config = state.config

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


def _handle_work_mode() -> None:
    """Обрабатывает обычный рабочий режим"""
    state = get_state()
    config = state.config

    with state.lock:
        time_since_last_activity = time.time() - state.last_activity_time
        current_idle_threshold_local = state.current_idle_threshold
        state.is_simulating = state.is_simulating

    # Генерация нового порога бездействия
    if current_idle_threshold_local is None:
        new_threshold = random.randint(config['min_idle_time'], config['max_idle_time'])
        with state.lock:
            state.current_idle_threshold = new_threshold
            current_idle_threshold_local = state.current_idle_threshold
        log(f"Установлен новый порог бездействия: {current_idle_threshold_local} сек", 'DEBUG')

    # КРИТИЧЕСКИ ВАЖНО: Минимальная задержка MINIMUM_DELAY_AFTER_USER_ACTIVITY секунд
    if time_since_last_activity >= MINIMUM_DELAY_AFTER_USER_ACTIVITY and \
       (state.is_simulating or time_since_last_activity >= current_idle_threshold_local):

        # Начало симуляции
        if not state.is_simulating:
            # mouse_controller импортирован на верхнем уровне
            with state.lock:
                state.absolute_anchor_position = mouse_controller.position
                state.initial_mouse_position = mouse_controller.position
                state.is_simulating = True
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
        if consecutive_safe_keys >= 5 and 'safe_key' in available_actions:
            # Удаляем все 'safe_key' из списка доступных действий
            available_actions = [a for a in available_actions if a != 'safe_key']
            log(f"⚠️ Избегаем 5-го подряд нажатия Shift (уже {consecutive_safe_keys} подряд)", 'DEBUG')

        # Если после удаления safe_key список пуст, добавляем обратно одно действие
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
        with state.lock:
            state.last_activity_time = time.time()

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
        if state.is_simulating:
            with state.lock:
                if not state.is_simulating:
                    log("Симуляция прервана активностью пользователя.", 'INFO')

        # Показываем оставшееся время с учетом минимальной задержки
        if time_since_last_activity < MINIMUM_DELAY_AFTER_USER_ACTIVITY:
            remaining = MINIMUM_DELAY_AFTER_USER_ACTIVITY - time_since_last_activity
            log(f"Ожидание после активности пользователя. Осталось: {remaining:.1f} сек", 'DEBUG')
        else:
            remaining = current_idle_threshold_local - time_since_last_activity
            log(f"Ожидание бездействия. Осталось: {remaining:.1f} сек", 'DEBUG')

        time.sleep(1)


def show_stats() -> None:
    """Периодический вывод статистики выполненных действий"""
    while True:
        time.sleep(300)  # Каждые 5 минут
        state = get_state()
        if len(state.action_history) > 0:
            recent = [a for a in state.action_history if time.time() - a[1] < 3600]
            log(f"[Статистика] Действий за последний час: {len(recent)}")
