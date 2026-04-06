"""
Модуль функций выполнения действий.

Содержит функции для симуляции пользовательских действий:
движение мыши, нажатие клавиш, клики, Ctrl+Tab.
"""

import time
import random
from datetime import datetime
from .. import utils
from .state import SimulationState, get_mouse_controller, get_keyboard_controller, MINIMUM_DELAY_AFTER_USER_ACTIVITY
from .logger import log
from .time_checks import is_before_work


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def get_consecutive_safe_key_count(state: 'SimulationState') -> int:
    """
    Возвращает количество подряд идущих safe_key действий в конце истории.

    Args:
        state: Экземпляр состояния симуляции

    Returns:
        Количество последовательных safe_key действий
    """
    count = 0
    # Идем с конца истории и считаем последовательные safe_key
    for action_type, _ in reversed(state.action_history):
        if action_type == 'safe_key':
            count += 1
        else:
            break
    return count


def move_mouse_naturally(target_x: int, target_y: int, state: 'SimulationState') -> None:
    """
    Плавное перемещение мыши к целевой позиции.

    Args:
        target_x: Целевая координата X
        target_y: Целевая координата Y
        state: Экземпляр состояния симуляции
    """
    mouse_controller = get_mouse_controller()
    start_pos = mouse_controller.position
    dx = target_x - start_pos[0]
    dy = target_y - start_pos[1]
    config = state.config
    steps = config['smooth_move_steps']

    with state.lock:
        state.is_performing_action = True
        action_start_time = state.last_activity_time

    for step in range(steps):
        # Проверяем активность пользователя на каждом шаге
        with state.lock:
            if state.last_activity_time > action_start_time:
                # Пользователь проявил активность - прерываем движение
                state.action_history.append(('mouse_move', time.time()))
                state.is_performing_action = False
                state.is_simulating = False
                log(f"⚠️ Движение мыши прервано активностью пользователя (шаг {step}/{steps})", 'INFO')
                return
            # Проверка активности пользователя после работы
            if state.user_activity_after_work:
                state.action_history.append(('mouse_move', time.time()))
                state.is_performing_action = False
                state.is_simulating = False
                log(f"🚪 Движение мыши прервано активностью пользователя после рабочего дня (шаг {step}/{steps})", 'INFO')
                return

        t = step / steps
        if config['natural_behavior']:
            # Кривая ease-in-out для более естественного движения
            t = t * t * (3 - 2 * t)

        new_x = start_pos[0] + (dx * t)
        new_y = start_pos[1] + (dy * t)
        get_mouse_controller().position = (new_x, new_y)

        sleep_time = config['smooth_move_duration'] / steps
        if config['natural_behavior'] and random.random() < 0.1:
            sleep_time *= random.uniform(1.2, 1.5)

        time.sleep(sleep_time)

    get_mouse_controller().position = (target_x, target_y)

    with state.lock:
        state.is_performing_action = False


# === ФУНКЦИИ ВЫПОЛНЕНИЯ ДЕЙСТВИЙ ===

def type_key_sequence(sequence: str, state: 'SimulationState') -> None:
    """
    Вводит последовательность клавиш, включая специальные клавиши.

    Args:
        sequence: Строка с последовательностью, например "text{Enter}{Tab}"
        state: Экземпляр состояния симуляции
    """
    if not sequence:
        return

    with state.lock:
        if state.user_activity_after_work:
            return

    log(f"🔑 Начало ввода последовательности клавиш")

    with state.lock:
        state.is_performing_action = True

    try:
        parsed = utils.parse_key_sequence(sequence)
        from pynput.keyboard import Key
        keyboard_controller = get_keyboard_controller()

        for element in parsed:
            # Проверяем, является ли элемент специальной клавишей
            if element == "Enter":
                keyboard_controller.press(Key.enter)
                time.sleep(0.05)
                keyboard_controller.release(Key.enter)
                time.sleep(random.uniform(0.1, 0.3))

            elif element == "Tab":
                keyboard_controller.press(Key.tab)
                time.sleep(0.05)
                keyboard_controller.release(Key.tab)
                time.sleep(random.uniform(0.1, 0.3))

            elif element == "Space":
                keyboard_controller.press(Key.space)
                time.sleep(0.05)
                keyboard_controller.release(Key.space)
                time.sleep(random.uniform(0.05, 0.15))

            else:
                # Обычный текст - вводим посимвольно
                for char in element:
                    keyboard_controller.type(char)
                    time.sleep(random.uniform(0.05, 0.15))  # Задержка между символами

        log(f"✅ Последовательность клавиш введена успешно")

    except Exception as e:
        log(f"❌ Ошибка при вводе последовательности: {e}", 'ERROR')

    finally:
        with state.lock:
            state.is_performing_action = False


def show_shutdown_warning(state: 'SimulationState') -> bool:
    """
    Показывает всплывающее окно с предупреждением о выключении.

    Args:
        state: Экземпляр состояния симуляции

    Returns:
        True если нужно продолжить выключение, False если отменено
    """
    import tkinter as tk
    from threading import Timer
    timer = None

    def on_cancel() -> None:
        nonlocal timer
        state.shutdown_cancelled = True
        log("⚠️ Выключение отменено пользователем")
        if timer is not None:
            try:
                timer.cancel()
            except Exception:
                pass
        root.destroy()

    def on_timeout() -> None:
        try:
            root.destroy()
        except Exception:
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

    if state.config.get('shutdown_on_exit', False):
        warning_text += f"Компьютер будет ВЫКЛЮЧЕН через {state.config.get('shutdown_warning_time', 30)} секунд."
    else:
        warning_text += f"Компьютер будет ЗАБЛОКИРОВАН через {state.config.get('shutdown_warning_time', 30)} секунд."

    label = tk.Label(root, text=warning_text, font=("Arial", 12), pady=20)
    label.pack()

    # Кнопка отмены
    cancel_btn = tk.Button(root, text="Отменить", command=on_cancel,
                          font=("Arial", 12), bg="#ff4444", fg="white",
                          padx=20, pady=10)
    cancel_btn.pack(pady=10)

    # Автоматическое закрытие через заданное время
    timer = Timer(state.config.get('shutdown_warning_time', 30), on_timeout)
    timer.daemon = True
    timer.start()

    # Запускаем окно
    root.mainloop()

    return not state.shutdown_cancelled


def random_mouse_move(state: 'SimulationState') -> None:
    """
    Случайное движение мыши в пределах заданного диапазона.

    Args:
        state: Экземпляр состояния симуляции
    """
    config = state.config
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

    target_x = state.initial_mouse_position[0] + offset_x
    target_y = state.initial_mouse_position[1] + offset_y

    # Ограничение дрифта от начальной точки симуляции
    with state.lock:
        if state.absolute_anchor_position is not None:
            anchor_x = state.absolute_anchor_position[0]
            anchor_y = state.absolute_anchor_position[1]
            max_abs_range = config['max_mouse_range']

            target_x = max(anchor_x - max_abs_range, min(target_x, anchor_x + max_abs_range))
            target_y = max(anchor_y - max_abs_range, min(target_y, anchor_y + max_abs_range))

    log(f"Движение мыши: ({state.initial_mouse_position[0]}, {state.initial_mouse_position[1]}) -> ({target_x}, {target_y})")
    move_mouse_naturally(target_x, target_y, state)
    state.action_history.append(('mouse_move', time.time()))

    state.initial_mouse_position = get_mouse_controller().position


def random_arrow_press(state: 'SimulationState') -> None:
    """
    Нажатие клавиш-стрелок (имитация прокрутки/навигации).

    Args:
        state: Экземпляр состояния симуляции
    """
    from pynput.keyboard import Key

    config = state.config
    keyboard_controller = get_keyboard_controller()

    if config['natural_behavior']:
        # Больший вес для up/down (вертикальная прокрутка популярнее)
        arrows = [Key.up, Key.down, Key.up, Key.down, Key.left, Key.right]
    else:
        arrows = [Key.up, Key.down, Key.left, Key.right]

    arrow = random.choice(arrows)

    repetitions = random.randint(config['min_key_presses'], config['max_key_presses'])
    log(f"Нажатие стрелки (x{repetitions})")

    with state.lock:
        state.is_performing_action = True
        action_start_time = state.last_activity_time

    for i in range(repetitions):
        # Проверяем, не было ли активности пользователя
        with state.lock:
            if state.last_activity_time > action_start_time:
                # Пользователь проявил активность - прерываем серию
                log(f"⚠️ Серия нажатий прервана активностью пользователя (выполнено {i}/{repetitions})", 'INFO')
                state.action_history.append(('keyboard', time.time()))
                state.is_performing_action = False
                state.is_simulating = False
                return
            # Проверка активности пользователя после работы
            if state.user_activity_after_work:
                log(f"🚪 Серия нажатий прервана активностью пользователя после рабочего дня (выполнено {i}/{repetitions})", 'INFO')
                state.is_performing_action = False
                state.is_simulating = False
                return

        keyboard_controller.press(arrow)
        time.sleep(random.uniform(0.05, 0.15))
        keyboard_controller.release(arrow)

        if i < repetitions - 1:
            time.sleep(random.uniform(0.1, 0.3))

    with state.lock:
        state.is_performing_action = False
    state.action_history.append(('keyboard', time.time()))


def random_mouse_click(state: 'SimulationState') -> None:
    """
    Клик левой кнопкой мыши в текущей позиции.

    Args:
        state: Экземпляр состояния симуляции
    """
    from pynput.mouse import Button
    with state.lock:
        if state.user_activity_after_work:
            return
    log(f"Клик левой кнопкой мыши в текущей позиции")

    with state.lock:
        state.is_performing_action = True

    get_mouse_controller().click(Button.left, 1)

    with state.lock:
        state.is_performing_action = False
    state.action_history.append(('mouse_click', time.time()))


def safe_key_press(state: 'SimulationState') -> None:
    """
    Нажатие безопасной клавиши (Shift) - не производит побочных эффектов.

    Args:
        state: Экземпляр состояния симуляции
    """
    from pynput.keyboard import Key
    with state.lock:
        if state.user_activity_after_work:
            return
    log(f"Нажатие безопасной клавиши")

    with state.lock:
        state.is_performing_action = True

    keyboard_controller = get_keyboard_controller()
    keyboard_controller.press(Key.shift)
    time.sleep(0.05)
    keyboard_controller.release(Key.shift)

    with state.lock:
        state.is_performing_action = False
    state.action_history.append(('safe_key', time.time()))


def control_tab_press(state: 'SimulationState') -> None:
    """
    Нажатие Ctrl+Tab (переключение вкладок).

    Args:
        state: Экземпляр состояния симуляции
    """
    from pynput.keyboard import Key
    log(f"Нажатие комбинации клавиш")

    with state.lock:
        state.is_performing_action = True
        action_start_time = state.last_activity_time

    keyboard_controller = get_keyboard_controller()
    keyboard_controller.press(Key.ctrl_l)
    time.sleep(random.uniform(0.05, 0.15))

    # Проверяем активность пользователя перед нажатием Tab
    with state.lock:
        if state.last_activity_time > action_start_time:
            # Пользователь проявил активность - отменяем действие
            keyboard_controller.release(Key.ctrl_l)
            state.action_history.append(('ctrl_tab', time.time()))
            state.is_performing_action = False
            state.is_simulating = False
            log(f"⚠️ Комбинация клавиш прервана активностью пользователя", 'INFO')
            return
        # Проверка активности пользователя после работы
        if state.user_activity_after_work:
            keyboard_controller.release(Key.ctrl_l)
            state.action_history.append(('ctrl_tab', time.time()))
            state.is_performing_action = False
            state.is_simulating = False
            log(f"🚪 Комбинация клавиш прервана активностью пользователя после рабочего дня", 'INFO')
            return

    keyboard_controller.press(Key.tab)
    time.sleep(random.uniform(0.1, 0.2))
    keyboard_controller.release(Key.tab)
    time.sleep(random.uniform(0.05, 0.15))
    keyboard_controller.release(Key.ctrl_l)

    with state.lock:
        state.is_performing_action = False
    state.action_history.append(('ctrl_tab', time.time()))
