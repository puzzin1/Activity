"""
Основной модуль симуляции активности.
Содержит логику симуляции, функции выполнения действий и главный цикл.
"""

import time
import random
import os
import sys
import signal
import platform
import subprocess
import tkinter as tk
from tkinter import messagebox
from threading import Thread, Lock, Timer
from pynput import mouse, keyboard
from pynput.mouse import Controller, Button
from pynput.keyboard import Controller as KeyboardController, Key
from datetime import datetime

from . import config
from . import utils

# Настройка контроллеров
mouse_controller = Controller()
keyboard_controller = KeyboardController()

# --- МЕХАНИЗМ СИНХРОНИЗАЦИИ ---
global_lock = Lock()

# Переменные для отслеживания
last_activity_time = time.time()
initial_mouse_position = None
absolute_anchor_position = None
is_simulating = False
is_performing_action = False
action_history = []
log_file_path = f"activity_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
current_idle_threshold = None
last_mouse_log_time = 0
lunch_sequence_executed = False  # Флаг для отслеживания ввода после обеда
shutdown_cancelled = False  # Флаг отмены выключения
user_activity_after_work = False  # Флаг активности пользователя после работы

CONFIG = {}
SCHEDULE = {}

# Функция для логирования
def log(message, level='INFO'):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{timestamp}] [{level}] {message}"

    # Выводим в консоль только ERROR и WARNING
    if level in ['ERROR', 'WARNING']:
        print(log_message)

    # Записываем в файл если включено подробное логирование
    if CONFIG.get('verbose_logging', True):
        try:
            with open(log_file_path, 'a', encoding='utf-8') as f:
                f.write(log_message + '\n')
        except Exception as e:
            print(f"Ошибка записи в лог-файл: {e}")

# === ФУНКЦИИ ПРОВЕРКИ ВРЕМЕНИ ===

def is_work_hours():
    """Проверяет, находимся ли мы в рабочее время"""
    current = utils.get_current_time_minutes()
    work_start = utils.time_str_to_minutes(SCHEDULE['work_start'])
    work_end = utils.time_str_to_minutes(SCHEDULE['work_end'])
    return work_start <= current <= work_end

def is_before_work():
    """Проверяет, находимся ли мы ДО начала рабочего времени"""
    current = utils.get_current_time_minutes()
    work_start = utils.time_str_to_minutes(SCHEDULE['work_start'])
    return current < work_start

def is_after_work():
    """Проверяет, находимся ли мы ПОСЛЕ окончания рабочего времени"""
    current = utils.get_current_time_minutes()
    work_end = utils.time_str_to_minutes(SCHEDULE['work_end'])
    return current > work_end

def is_break_time():
    """Проверяет, сейчас ли время перерыва"""
    current = utils.get_current_time_minutes()

    # Проверяем обед
    lunch_start = utils.time_str_to_minutes(SCHEDULE['lunch_start'])
    lunch_end = utils.time_str_to_minutes(SCHEDULE['lunch_end'])
    if lunch_start <= current <= lunch_end:
        return True, 'обед'

    # Проверяем другие перерывы
    for brk in SCHEDULE['breaks']:
        break_start = utils.time_str_to_minutes(brk['start'])
        break_end = utils.time_str_to_minutes(brk['end'])
        if break_start <= current <= break_end:
            return True, 'перерыв'

    return False, None

def is_after_lunch():
    """Проверяет, находимся ли мы ПОСЛЕ обеденного перерыва"""
    current = utils.get_current_time_minutes()
    lunch_end = utils.time_str_to_minutes(SCHEDULE['lunch_end'])
    return current > lunch_end


def should_simulate_afterhours():
    """Определяет, нужна ли активность вне рабочего времени"""
    mode = CONFIG['afterhours_mode']

    if mode == 'disabled':
        return False
    elif mode == 'before_only':
        return is_before_work()
    elif mode == 'before_and_after':
        return not is_work_hours()

    return False


def type_key_sequence(sequence):
    """
    Вводит последовательность клавиш, включая специальные клавиши.

    Args:
        sequence (str): Строка с последовательностью, например "text{Enter}{Tab}"
    """
    global is_performing_action

    if not sequence:
        return

    log(f"🔑 Начало ввода последовательности клавиш")

    with global_lock:
        is_performing_action = True

    try:
        parsed = utils.parse_key_sequence(sequence)

        for element in parsed:
            # Проверяем, является ли элемент специальной клавишей
            if element == "Enter":
                keyboard_controller.press(Key.enter)
                time.sleep(0.05)
                keyboard_controller.release(Key.enter)
                log(f"  • Нажата клавиша: Enter")
                time.sleep(random.uniform(0.1, 0.3))

            elif element == "Tab":
                keyboard_controller.press(Key.tab)
                time.sleep(0.05)
                keyboard_controller.release(Key.tab)
                log(f"  • Нажата клавиша: Tab")
                time.sleep(random.uniform(0.1, 0.3))

            elif element == "Space":
                keyboard_controller.press(Key.space)
                time.sleep(0.05)
                keyboard_controller.release(Key.space)
                log(f"  • Нажата клавиша: Space")
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
        with global_lock:
            is_performing_action = False


def show_shutdown_warning():
    """Показывает всплывающее окно с предупреждением о выключении"""
    global shutdown_cancelled

    def on_cancel():
        global shutdown_cancelled
        shutdown_cancelled = True
        log("⚠️ Выключение отменено пользователем")
        root.destroy()

    def on_timeout():
        root.destroy()

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

    if CONFIG.get('shutdown_on_exit', False):
        warning_text += f"Компьютер будет ВЫКЛЮЧЕН через {CONFIG.get('shutdown_warning_time', 30)} секунд."
    else:
        warning_text += f"Компьютер будет ЗАБЛОКИРОВАН через {CONFIG.get('shutdown_warning_time', 30)} секунд."

    label = tk.Label(root, text=warning_text, font=("Arial", 12), pady=20)
    label.pack()

    # Кнопка отмены
    cancel_btn = tk.Button(root, text="Отменить", command=on_cancel,
                          font=("Arial", 12), bg="#ff4444", fg="white",
                          padx=20, pady=10)
    cancel_btn.pack(pady=10)

    # Автоматическое закрытие через заданное время
    timer = Timer(CONFIG.get('shutdown_warning_time', 30), on_timeout)
    timer.daemon = True
    timer.start()

    # Запускаем окно
    root.mainloop()

    return not shutdown_cancelled


# === ФУНКЦИИ ВЫПОЛНЕНИЯ ДЕЙСТВИЙ ===

def move_mouse_naturally(target_x, target_y):
    """Плавное перемещение мыши к целевой позиции"""
    start_pos = mouse_controller.position
    dx = target_x - start_pos[0]
    dy = target_y - start_pos[1]
    steps = CONFIG['smooth_move_steps']

    global is_performing_action, is_simulating, last_activity_time
    with global_lock:
        is_performing_action = True
        action_start_time = last_activity_time

    for step in range(steps):
        # Проверяем активность пользователя на каждом шаге
        with global_lock:
            if last_activity_time > action_start_time:
                # Пользователь проявил активность - прерываем движение
                is_performing_action = False
                is_simulating = False
                log(f"⚠️ Движение мыши прервано активностью пользователя (шаг {step}/{steps})", 'INFO')
                return

        t = step / steps
        if CONFIG['natural_behavior']:
            # Кривая ease-in-out для более естественного движения
            t = t * t * (3 - 2 * t)

        new_x = start_pos[0] + (dx * t)
        new_y = start_pos[1] + (dy * t)
        mouse_controller.position = (new_x, new_y)

        sleep_time = CONFIG['smooth_move_duration'] / steps
        if CONFIG['natural_behavior'] and random.random() < 0.1:
            sleep_time *= random.uniform(1.2, 1.5)

        time.sleep(sleep_time)

    mouse_controller.position = (target_x, target_y)

    with global_lock:
        is_performing_action = False

def random_mouse_move():
    """Случайное движение мыши в пределах заданного диапазона"""
    global initial_mouse_position

    max_range_relative = CONFIG['max_mouse_range']

    if CONFIG['natural_behavior']:
        # Треугольное распределение дает больше движений ближе к центру
        offset_x = random.randint(-max_range_relative, max_range_relative) * random.triangular(0.1, 1.0, 0.4)
        offset_y = random.randint(-max_range_relative, max_range_relative) * random.triangular(0.1, 1.0, 0.4)
        offset_x = int(offset_x)
        offset_y = int(offset_y)
    else:
        offset_x = random.randint(-max_range_relative, max_range_relative)
        offset_y = random.randint(-max_range_relative, max_range_relative)

    target_x = initial_mouse_position[0] + offset_x
    target_y = initial_mouse_position[1] + offset_y

    # Ограничение дрифта от начальной точки симуляции
    with global_lock:
        if absolute_anchor_position is not None:
            anchor_x = absolute_anchor_position[0]
            anchor_y = absolute_anchor_position[1]
            max_abs_range = CONFIG['max_mouse_range']

            target_x = max(anchor_x - max_abs_range, min(target_x, anchor_x + max_abs_range))
            target_y = max(anchor_y - max_abs_range, min(target_y, anchor_y + max_abs_range))

    log(f"Движение мыши: ({initial_mouse_position[0]}, {initial_mouse_position[1]}) -> ({target_x}, {target_y})")
    move_mouse_naturally(target_x, target_y)
    action_history.append(('mouse_move', time.time()))

    initial_mouse_position = mouse_controller.position

def random_arrow_press():
    """Нажатие клавиш-стрелок (имитация прокрутки/навигации)"""
    global is_performing_action, is_simulating, last_activity_time

    if CONFIG['natural_behavior']:
        # Больший вес для up/down (вертикальная прокрутка популярнее)
        arrows = [Key.up, Key.down, Key.up, Key.down, Key.left, Key.right]
    else:
        arrows = [Key.up, Key.down, Key.left, Key.right]

    arrow = random.choice(arrows)

    repetitions = random.randint(CONFIG['min_key_presses'], CONFIG['max_key_presses'])
    log(f"Нажатие стрелки: {arrow} (x{repetitions})")

    with global_lock:
        is_performing_action = True
        action_start_time = last_activity_time  # Запоминаем время начала действия

    for i in range(repetitions):
        # Проверяем, не было ли активности пользователя
        with global_lock:
            if last_activity_time > action_start_time:
                # Пользователь проявил активность - прерываем серию
                log(f"⚠️ Серия нажатий прервана активностью пользователя (выполнено {i}/{repetitions})", 'INFO')
                is_performing_action = False
                is_simulating = False
                return

        keyboard_controller.press(arrow)
        time.sleep(random.uniform(0.05, 0.15))
        keyboard_controller.release(arrow)

        if i < repetitions - 1:
            time.sleep(random.uniform(0.1, 0.3))

    with global_lock: is_performing_action = False
    action_history.append(('keyboard', time.time()))

def random_mouse_click():
    """Клик левой кнопкой мыши в текущей позиции"""
    global is_performing_action
    log(f"Клик левой кнопкой мыши в текущей позиции")

    with global_lock: is_performing_action = True

    mouse_controller.click(Button.left, 1)

    with global_lock: is_performing_action = False
    action_history.append(('mouse_click', time.time()))

def safe_key_press():
    """Нажатие безопасной клавиши (Shift) - не производит побочных эффектов"""
    global is_performing_action
    log(f"Нажатие безопасной клавиши (Shift)")

    with global_lock: is_performing_action = True

    keyboard_controller.press(Key.shift)
    time.sleep(0.05)
    keyboard_controller.release(Key.shift)

    with global_lock: is_performing_action = False
    action_history.append(('safe_key', time.time()))

def control_tab_press():
    """Нажатие Ctrl+Tab (переключение вкладок)"""
    global is_performing_action, is_simulating, last_activity_time
    log(f"Нажатие Ctrl+Tab")

    with global_lock:
        is_performing_action = True
        action_start_time = last_activity_time

    keyboard_controller.press(Key.ctrl_l)
    time.sleep(random.uniform(0.05, 0.15))

    # Проверяем активность пользователя перед нажатием Tab
    with global_lock:
        if last_activity_time > action_start_time:
            # Пользователь проявил активность - отменяем действие
            keyboard_controller.release(Key.ctrl_l)
            is_performing_action = False
            is_simulating = False
            log(f"⚠️ Ctrl+Tab прерван активностью пользователя", 'INFO')
            return

    keyboard_controller.press(Key.tab)
    time.sleep(random.uniform(0.1, 0.2))
    keyboard_controller.release(Key.tab)
    time.sleep(random.uniform(0.05, 0.15))
    keyboard_controller.release(Key.ctrl_l)

    with global_lock: is_performing_action = False
    action_history.append(('ctrl_tab', time.time()))


# === ГЛАВНАЯ ФУНКЦИЯ СИМУЛЯЦИИ ===

def simulate_activity():
    """Основной цикл симуляции активности"""
    global last_activity_time, is_simulating, initial_mouse_position, current_idle_threshold, absolute_anchor_position, lunch_sequence_executed, shutdown_cancelled, user_activity_after_work

    last_burst_time = time.time()

    while True:
        # Проверка активности пользователя после работы
        if user_activity_after_work:
            log("🚪 Завершение программы из-за активности пользователя после рабочего дня")
            print("\n" + "=" * 70)
            print("🚪 ОБНАРУЖЕНА АКТИВНОСТЬ ПОЛЬЗОВАТЕЛЯ")
            print("=" * 70)
            print("Программа завершена без блокировки/выключения компьютера")
            if CONFIG['verbose_logging']:
                print(f"📄 Лог сохранён в файл: {log_file_path}")
            print("=" * 70)
            time.sleep(1)
            os._exit(0)

        # Проверяем режим работы
        in_work_hours = is_work_hours()
        on_break, break_type = is_break_time()

        # === ПРОВЕРКА И ВЫПОЛНЕНИЕ ДЕЙСТВИЙ ПОСЛЕ ОБЕДА ===
        if CONFIG.get('after_lunch_action', False) and not lunch_sequence_executed:
            # Проверяем, прошел ли обед и находимся ли мы после него
            if in_work_hours and is_after_lunch() and not on_break:
                log(f"🍽️ Обеденный перерыв завершен. Ожидание {CONFIG.get('after_lunch_delay', 5)} сек...")
                time.sleep(CONFIG.get('after_lunch_delay', 5))

                # Вводим последовательность клавиш
                sequence = CONFIG.get('after_lunch_sequence', '')
                if sequence:
                    type_key_sequence(sequence)
                    lunch_sequence_executed = True

                    # Обновляем время активности
                    with global_lock:
                        last_activity_time = time.time()
                else:
                    log(f"⚠️ Последовательность после обеда не задана", 'WARNING')
                    lunch_sequence_executed = True

        # === РЕЖИМ ВНЕ РАБОЧЕГО ВРЕМЕНИ ===
        if not in_work_hours:
            # Проверяем, нужна ли активность вне рабочего времени
            if not should_simulate_afterhours():
                # Если мы ПОСЛЕ работы и активность отключена - завершаем программу
                if is_after_work():
                    log(f"🏁 Рабочий день завершен. Программа останавливается (режим: {CONFIG['afterhours_mode']})")

                    # Показываем предупреждение, если включено
                    should_proceed = True
                    if CONFIG.get('show_shutdown_warning', True):
                        print(f"\n⏰ Показ предупреждения о завершении работы...")
                        log("⏰ Показ предупреждения о завершении работы")
                        should_proceed = show_shutdown_warning()

                    if not should_proceed or shutdown_cancelled:
                        log("✋ Завершение работы отменено пользователем")
                        print("\n✋ Завершение работы отменено")
                        # Продолжаем работу в режиме ожидания
                        time.sleep(60)
                        shutdown_cancelled = False
                        continue

                    print("\n" + "=" * 70)
                    print("🏁 РАБОЧИЙ ДЕНЬ ЗАВЕРШЕН")
                    print("=" * 70)
                    print(f"⏰ Время окончания: {datetime.now().strftime('%H:%M:%S')}")
                    if CONFIG['verbose_logging']:
                        print(f"📄 Лог сохранён в файл: {log_file_path}")

                    # Логируем статистику в файл
                    log(f"Всего выполнено действий: {len(action_history)}")

                    # Выключение или блокировка компьютера при АВТОМАТИЧЕСКОМ завершении
                    if CONFIG.get('shutdown_on_exit', False):
                        print("🔌 ВЫКЛЮЧЕНИЕ КОМПЬЮТЕРА...")
                        time.sleep(1)
                        success, message = utils.shutdown_computer()
                        log(message)
                    elif CONFIG.get('lock_on_exit', True):
                        print("🔒 Блокировка компьютера...")
                        time.sleep(1)
                        success, message = utils.lock_computer()
                        log(message)

                    print("=" * 70)
                    time.sleep(1)  # Задержка перед завершением
                    os._exit(0)  # Принудительное завершение всех потоков

                # Если мы ДО работы - просто ждем
                if is_simulating:
                    with global_lock:
                        is_simulating = False
                    log(f"🌙 Внерабочее время. Активность отключена (режим: {CONFIG['afterhours_mode']})")
                time.sleep(60)
                continue

            # Режим всплесков активности
            time_since_burst = time.time() - last_burst_time
            burst_interval = random.uniform(
                CONFIG['afterhours_burst_interval_min'] * 60,
                CONFIG['afterhours_burst_interval_max'] * 60
            )

            # Проверяем, прошло ли минимум 60 секунд с последней активности пользователя
            MINIMUM_DELAY_AFTER_USER_ACTIVITY = 60
            with global_lock:
                time_since_user_activity = time.time() - last_activity_time

            if time_since_burst >= burst_interval and time_since_user_activity >= MINIMUM_DELAY_AFTER_USER_ACTIVITY:
                burst_duration = random.uniform(
                    CONFIG['afterhours_burst_duration_min'],
                    CONFIG['afterhours_burst_duration_max']
                )

                time_indicator = "🌅" if is_before_work() else "🌙"
                log(f"{time_indicator} Внерабочий режим: всплеск активности на {burst_duration:.0f} сек")

                burst_end_time = time.time() + burst_duration

                with global_lock:
                    absolute_anchor_position = mouse_controller.position
                    initial_mouse_position = mouse_controller.position
                    is_simulating = True

                while time.time() < burst_end_time:
                    # Выполняем легкую активность
                    action = random.choice(['mouse_move', 'safe_key'])

                    try:
                        if action == 'mouse_move':
                            random_mouse_move()
                        elif action == 'safe_key':
                            safe_key_press()
                    except Exception as e:
                        log(f"Ошибка при выполнении действия: {e}", 'ERROR')

                    with global_lock:
                        last_activity_time = time.time()

                    time.sleep(random.uniform(2, 5))

                with global_lock:
                    is_simulating = False

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
            if is_simulating:
                with global_lock:
                    is_simulating = False
                log(f"☕ Перерыв ({break_type}). Активность приостановлена.")
            time.sleep(30)
            continue

        # === ОБЫЧНЫЙ РАБОЧИЙ РЕЖИМ ===
        with global_lock:
            time_since_last_activity = time.time() - last_activity_time
            current_idle_threshold_local = current_idle_threshold
            is_simulating_local = is_simulating

        # Генерация нового порога бездействия
        if current_idle_threshold_local is None:
            new_threshold = random.randint(CONFIG['min_idle_time'], CONFIG['max_idle_time'])
            with global_lock:
                current_idle_threshold = new_threshold
                current_idle_threshold_local = current_idle_threshold
            log(f"Установлен новый порог бездействия: {current_idle_threshold_local} сек", 'DEBUG')

        # КРИТИЧЕСКИ ВАЖНО: Минимальная задержка 60 секунд после любой активности пользователя
        MINIMUM_DELAY_AFTER_USER_ACTIVITY = 60

        # Проверка необходимости симуляции
        # Программа начинает действовать только если:
        # 1. Прошло минимум 60 секунд с последней активности пользователя
        # 2. И прошло достаточно времени согласно порогу бездействия
        if time_since_last_activity >= MINIMUM_DELAY_AFTER_USER_ACTIVITY and \
           (is_simulating_local or time_since_last_activity >= current_idle_threshold_local):

            # Начало симуляции
            if not is_simulating_local:
                with global_lock:
                    absolute_anchor_position = mouse_controller.position
                    initial_mouse_position = mouse_controller.position
                    is_simulating = True
                    is_simulating_local = True
                log(f"💼 Начало симуляции активности (бездействие: {time_since_last_activity:.1f} сек)")

            # Формирование списка доступных действий с весами
            available_actions = []

            if CONFIG['use_mouse_move']:
                available_actions.extend(['mouse_move'] * CONFIG['action_weight_mouse_move'])

            if CONFIG['use_keyboard']:
                available_actions.extend(['keyboard'] * CONFIG['action_weight_keyboard'])
                available_actions.extend(['ctrl_tab'] * CONFIG['action_weight_ctrl_tab'])

            if CONFIG['use_mouse_click']:
                available_actions.extend(['mouse_click'] * CONFIG['action_weight_mouse_click'])

            if CONFIG['natural_behavior']:
                available_actions.extend(['safe_key'] * CONFIG['action_weight_safe_key'])

            if not available_actions:
                available_actions = ['safe_key']

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
            with global_lock:
                last_activity_time = time.time()

            # Расчет паузы до следующего действия
            action_interval = random.uniform(
                CONFIG['min_action_interval'],
                CONFIG['max_action_interval']
            )

            # Случайное увеличение паузы для естественности
            if CONFIG['natural_behavior'] and random.random() < 0.15:
                action_interval *= random.uniform(1.5, 2.5)
                log(f"Увеличенная пауза: {action_interval:.1f} сек", 'DEBUG')

            log(f"Следующее действие через {action_interval:.1f} сек", 'DEBUG')
            time.sleep(action_interval)

        else:
            # Режим ожидания
            if is_simulating_local:
                 with global_lock:
                    if not is_simulating:
                        log("Симуляция прервана активностью пользователя.", 'INFO')

            # Показываем оставшееся время с учетом минимальной задержки 60 сек
            MINIMUM_DELAY_AFTER_USER_ACTIVITY = 60
            if time_since_last_activity < MINIMUM_DELAY_AFTER_USER_ACTIVITY:
                remaining = MINIMUM_DELAY_AFTER_USER_ACTIVITY - time_since_last_activity
                log(f"Ожидание после активности пользователя. Осталось: {remaining:.1f} сек", 'DEBUG')
            else:
                remaining = current_idle_threshold_local - time_since_last_activity
                log(f"Ожидание бездействия. Осталось: {remaining:.1f} сек", 'DEBUG')

            time.sleep(1)


# === ФУНКЦИЯ СТАТИСТИКИ ===

def show_stats():
    """Периодический вывод статистики выполненных действий"""
    while True:
        time.sleep(300)  # Каждые 5 минут
        if len(action_history) > 0:
            recent = [a for a in action_history if time.time() - a[1] < 3600]
            log(f"[Статистика] Действий за последний час: {len(recent)}")
            if len(action_history) > 100:
                action_history.clear()