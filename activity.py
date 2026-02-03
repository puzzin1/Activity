import time
import random
import os
import sys
import platform
import subprocess
import tkinter as tk
from tkinter import messagebox
from threading import Thread, Lock, Timer
from pynput import mouse, keyboard
from pynput.mouse import Controller, Button
from pynput.keyboard import Controller as KeyboardController, Key
from datetime import datetime
from config_manager import load_or_create_config, get_config_filename

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

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def lock_computer():
    """Блокирует компьютер в зависимости от операционной системы"""
    system = platform.system()
    
    try:
        if system == "Windows":
            # Windows: использует rundll32 для блокировки
            subprocess.call(['rundll32.exe', 'user32.dll,LockWorkStation'])
            log("🔒 Компьютер заблокирован (Windows)")
        elif system == "Darwin":  # macOS
            # macOS: использует pmset для блокировки экрана
            subprocess.call(['/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession', '-suspend'])
            log("🔒 Компьютер заблокирован (macOS)")
        elif system == "Linux":
            # Linux: пробует различные методы блокировки
            try:
                # Попытка 1: gnome-screensaver
                subprocess.call(['gnome-screensaver-command', '--lock'])
            except:
                try:
                    # Попытка 2: xdg-screensaver
                    subprocess.call(['xdg-screensaver', 'lock'])
                except:
                    try:
                        # Попытка 3: loginctl
                        subprocess.call(['loginctl', 'lock-session'])
                    except:
                        log("⚠️ Не удалось заблокировать компьютер (Linux)", 'ERROR')
                        return
            log("🔒 Компьютер заблокирован (Linux)")
        else:
            log(f"⚠️ Блокировка не поддерживается для ОС: {system}", 'ERROR')
    except Exception as e:
        log(f"⚠️ Ошибка при блокировке компьютера: {e}", 'ERROR')

def shutdown_computer():
    """Принудительно выключает компьютер без запроса подтверждения"""
    system = platform.system()
    
    try:
        if system == "Windows":
            # Windows: принудительное выключение через shutdown
            subprocess.call(['shutdown', '/s', '/f', '/t', '0'])
            log("🔌 Компьютер выключается (Windows)")
        elif system == "Darwin":  # macOS
            # macOS: принудительное выключение
            subprocess.call(['sudo', 'shutdown', '-h', 'now'])
            log("🔌 Компьютер выключается (macOS)")
        elif system == "Linux":
            # Linux: принудительное выключение
            try:
                subprocess.call(['systemctl', 'poweroff'])
            except:
                try:
                    subprocess.call(['shutdown', '-h', 'now'])
                except:
                    log("⚠️ Не удалось выключить компьютер (Linux)", 'ERROR')
                    return
            log("🔌 Компьютер выключается (Linux)")
        else:
            log(f"⚠️ Выключение не поддерживается для ОС: {system}", 'ERROR')
    except Exception as e:
        log(f"⚠️ Ошибка при выключении компьютера: {e}", 'ERROR')

def time_str_to_minutes(time_str):
    """Конвертирует строку времени 'HH:MM' в минуты с начала дня"""
    h, m = map(int, time_str.split(':'))
    return h * 60 + m

def get_current_time_minutes():
    """Возвращает текущее время в минутах с начала дня"""
    now = datetime.now()
    return now.hour * 60 + now.minute

def is_work_hours():
    """Проверяет, находимся ли мы в рабочее время"""
    current = get_current_time_minutes()
    work_start = time_str_to_minutes(SCHEDULE['work_start'])
    work_end = time_str_to_minutes(SCHEDULE['work_end'])
    return work_start <= current <= work_end

def is_before_work():
    """Проверяет, находимся ли мы ДО начала рабочего времени"""
    current = get_current_time_minutes()
    work_start = time_str_to_minutes(SCHEDULE['work_start'])
    return current < work_start

def is_after_work():
    """Проверяет, находимся ли мы ПОСЛЕ окончания рабочего времени"""
    current = get_current_time_minutes()
    work_end = time_str_to_minutes(SCHEDULE['work_end'])
    return current > work_end

def is_break_time():
    """Проверяет, сейчас ли время перерыва"""
    current = get_current_time_minutes()
    
    # Проверяем обед
    lunch_start = time_str_to_minutes(SCHEDULE['lunch_start'])
    lunch_end = time_str_to_minutes(SCHEDULE['lunch_end'])
    if lunch_start <= current <= lunch_end:
        return True, 'обед'
    
    # Проверяем другие перерывы
    for brk in SCHEDULE['breaks']:
        break_start = time_str_to_minutes(brk['start'])
        break_end = time_str_to_minutes(brk['end'])
        if break_start <= current <= break_end:
            return True, 'перерыв'
    
    return False, None

def is_after_lunch():
    """Проверяет, находимся ли мы ПОСЛЕ обеденного перерыва"""
    current = get_current_time_minutes()
    lunch_end = time_str_to_minutes(SCHEDULE['lunch_end'])
    return current > lunch_end

def parse_key_sequence(sequence):
    """
    Парсит строку последовательности клавиш, разделяя обычный текст и специальные клавиши.
    
    Args:
        sequence (str): Строка типа "text{Enter}more{Tab}text"
    
    Returns:
        list: Список элементов, где каждый элемент - это либо строка текста, либо специальная клавиша
    
    Example:
        parse_key_sequence("user{Tab}pass{Enter}") 
        -> ["user", "Tab", "pass", "Enter"]
    """
    result = []
    current_text = ""
    i = 0
    
    while i < len(sequence):
        if sequence[i] == '{':
            # Сохраняем накопленный текст
            if current_text:
                result.append(current_text)
                current_text = ""
            
            # Ищем закрывающую скобку
            end = sequence.find('}', i)
            if end != -1:
                key_name = sequence[i+1:end]
                result.append(key_name)
                i = end + 1
            else:
                # Если нет закрывающей скобки, считаем это обычным текстом
                current_text += sequence[i]
                i += 1
        else:
            current_text += sequence[i]
            i += 1
    
    # Добавляем оставшийся текст
    if current_text:
        result.append(current_text)
    
    return result

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
        parsed = parse_key_sequence(sequence)
        
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

# === ФУНКЦИИ-СЛУШАТЕЛИ ===

def on_keyboard_event(key):
    global last_activity_time, is_simulating, current_idle_threshold, absolute_anchor_position, is_performing_action, user_activity_after_work
    
    with global_lock:
        if is_performing_action:
            log(f"Игнорирование симулированного события клавиатуры: {key}", 'DEBUG')
            return

        # Проверка активности после рабочего дня
        if CONFIG.get('exit_on_activity_after_work', True) and is_after_work() and not is_work_hours():
            user_activity_after_work = True
            log("🚪 Обнаружена активность пользователя после рабочего дня. Завершение программы.")
            return

        last_activity_time = time.time()
        current_idle_threshold = None
        is_simulating = False
        absolute_anchor_position = None
        log(f"Обнаружена активность клавиатуры: {key}", 'DEBUG')

def on_mouse_event(x, y):
    """
    Обработчик движения мыши/тачпада.
    Автоматически отслеживает как движения мыши, так и тачпада.
    """
    global last_activity_time, is_simulating, initial_mouse_position, current_idle_threshold, absolute_anchor_position, is_performing_action, last_mouse_log_time, user_activity_after_work
    
    with global_lock:
        if is_performing_action:
            return
        
        # Проверка активности после рабочего дня
        if CONFIG.get('exit_on_activity_after_work', True) and is_after_work() and not is_work_hours():
            user_activity_after_work = True
            log("🚪 Обнаружена активность пользователя после рабочего дня. Завершение программы.")
            return
            
        last_activity_time = time.time()
        initial_mouse_position = (x, y) 
        current_idle_threshold = None
        is_simulating = False
        absolute_anchor_position = None
        
        current_time = time.time()
        if current_time - last_mouse_log_time >= 1.0:
            log(f"Обнаружено движение мыши пользователем: ({x}, {y})", 'DEBUG')
            last_mouse_log_time = current_time

def on_mouse_click(x, y, button, pressed):
    """
    Обработчик кликов мыши/тачпада.
    Автоматически отслеживает как клики мыши, так и тапы тачпада.
    """
    global last_activity_time, is_simulating, current_idle_threshold, absolute_anchor_position, is_performing_action, user_activity_after_work
    if pressed:
        with global_lock:
            if is_performing_action:
                log(f"Игнорирование симулированного клика мыши: {button}", 'DEBUG')
                return
            
            # Проверка активности после рабочего дня
            if CONFIG.get('exit_on_activity_after_work', True) and is_after_work() and not is_work_hours():
                user_activity_after_work = True
                log("🚪 Обнаружена активность пользователя после рабочего дня. Завершение программы.")
                return
                
            last_activity_time = time.time()
            is_simulating = False
            current_idle_threshold = None
            absolute_anchor_position = None
            log(f"Обнаружен клик мыши: {button} в ({x}, {y})", 'DEBUG')

# === ФУНКЦИИ ВЫПОЛНЕНИЯ ДЕЙСТВИЙ ===

def move_mouse_naturally(target_x, target_y):
    """Плавное перемещение мыши к целевой позиции"""
    start_pos = mouse_controller.position
    dx = target_x - start_pos[0]
    dy = target_y - start_pos[1]
    steps = CONFIG['smooth_move_steps']
    
    global is_performing_action
    with global_lock:
        is_performing_action = True 
    
    for step in range(steps):
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
    global is_performing_action

    if CONFIG['natural_behavior']:
        # Больший вес для up/down (вертикальная прокрутка популярнее)
        arrows = [Key.up, Key.down, Key.up, Key.down, Key.left, Key.right]
    else:
        arrows = [Key.up, Key.down, Key.left, Key.right]
    
    arrow = random.choice(arrows)
    
    repetitions = random.randint(CONFIG['min_key_presses'], CONFIG['max_key_presses'])
    log(f"Нажатие стрелки: {arrow} (x{repetitions})")
    
    with global_lock: is_performing_action = True
    
    for i in range(repetitions):
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
    global is_performing_action
    log(f"Нажатие Ctrl+Tab")
    
    with global_lock: is_performing_action = True
    
    keyboard_controller.press(Key.ctrl_l)
    time.sleep(random.uniform(0.05, 0.15)) 
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
                    
                    # Выключение или блокировка компьютера
                    if CONFIG.get('shutdown_on_exit', False):
                        print("🔌 ВЫКЛЮЧЕНИЕ КОМПЬЮТЕРА...")
                        time.sleep(1)
                        shutdown_computer()
                    elif CONFIG.get('lock_on_exit', True):
                        print("🔒 Блокировка компьютера...")
                        time.sleep(1)
                        lock_computer()
                    
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
            
            if time_since_burst >= burst_interval:
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
        
        # Проверка необходимости симуляции
        if is_simulating_local or time_since_last_activity >= current_idle_threshold_local:
            
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
            print(f"\n[Статистика] Действий за последний час: {len(recent)}")
            if len(action_history) > 100:
                action_history.clear()

# === ОСНОВНОЙ КОД ЗАПУСКА ===

if __name__ == "__main__":
    # Загружаем конфигурацию
    CONFIG, SCHEDULE = load_or_create_config()

    # Запуск слушателей
    keyboard_listener = keyboard.Listener(on_press=on_keyboard_event)
    mouse_listener = mouse.Listener(on_move=on_mouse_event, on_click=on_mouse_click)

    keyboard_listener.start()
    mouse_listener.start()

    initial_mouse_position = mouse_controller.position

    # Запуск потоков
    simulate_thread = Thread(target=simulate_activity, daemon=True)
    stats_thread = Thread(target=show_stats, daemon=True)

    simulate_thread.start()
    stats_thread.start()

    # === ВЫВОД ИНФОРМАЦИИ ===
    print("=" * 70)
    print("🚀 ПРОГРАММА СИМУЛЯЦИИ АКТИВНОСТИ ЗАПУЩЕНА")
    print("=" * 70)
    print(f"📅 Конфигурация: {get_config_filename()}")
    print(f"🖱️  Отслеживание: Мышь + Тачпад + Клавиатура")
    print()
    
    print(f"⏰ РАСПИСАНИЕ НА СЕГОДНЯ:")
    print(f"  • Рабочее время: {SCHEDULE['work_start']} - {SCHEDULE['work_end']}")
    print(f"  • Обед: {SCHEDULE['lunch_start']} - {SCHEDULE['lunch_end']} " +
          f"({time_str_to_minutes(SCHEDULE['lunch_end']) - time_str_to_minutes(SCHEDULE['lunch_start'])} мин)")
    
    if SCHEDULE['breaks']:
        print(f"  • Перерывы:")
        for i, brk in enumerate(SCHEDULE['breaks'], 1):
            print(f"    {i}. {brk['start']} - {brk['end']} ({brk['duration']} мин)")
    else:
        print(f"  • Перерывы: нет")
    
    print()
    print(f"⚙️  ОСНОВНЫЕ ПАРАМЕТРЫ:")
    print(f"  • Порог бездействия: {CONFIG['min_idle_time']}-{CONFIG['max_idle_time']} сек")
    print(f"  • Интервал между действиями: {CONFIG['min_action_interval']}-{CONFIG['max_action_interval']} сек")
    print(f"  • Серия нажатий стрелок: {CONFIG['min_key_presses']}-{CONFIG['max_key_presses']} раз")
    print(f"  • Макс. диапазон мыши: {CONFIG['max_mouse_range']} пикс")
    
    print()
    print(f"🎯 ТИПЫ ДЕЙСТВИЙ:")
    print(f"  • Движение мыши: {'✓' if CONFIG['use_mouse_move'] else '✗'} (вес: {CONFIG['action_weight_mouse_move']})")
    print(f"  • Стрелки клавиатуры: {'✓' if CONFIG['use_keyboard'] else '✗'} (вес: {CONFIG['action_weight_keyboard']})")
    print(f"  • Ctrl+Tab: {'✓' if CONFIG['use_keyboard'] else '✗'} (вес: {CONFIG['action_weight_ctrl_tab']})")
    print(f"  • Клики мыши: {'✓' if CONFIG['use_mouse_click'] else '✗'} (вес: {CONFIG['action_weight_mouse_click']})")
    print(f"  • Shift (безопасный): {'✓' if CONFIG['natural_behavior'] else '✗'} (вес: {CONFIG['action_weight_safe_key']})")
    print(f"  • Естественное поведение: {'✓' if CONFIG['natural_behavior'] else '✗'}")
    
    print()
    afterhours_mode_names = {
        'disabled': '🚫 Отключен',
        'before_only': '🌅 Только до работы',
        'before_and_after': '🌅🌙 До и после работы'
    }
    print(f"🌙 ВНЕРАБОЧИЙ РЕЖИМ: {afterhours_mode_names.get(CONFIG['afterhours_mode'], CONFIG['afterhours_mode'])}")
    if CONFIG['afterhours_mode'] != 'disabled':
        print(f"  • Всплески активности: {CONFIG['afterhours_burst_duration_min']}-{CONFIG['afterhours_burst_duration_max']} сек")
        print(f"  • Интервал между всплесками: {CONFIG['afterhours_burst_interval_min']}-{CONFIG['afterhours_burst_interval_max']} мин")
    
    print()
    print(f"🍽️ ДЕЙСТВИЯ ПОСЛЕ ОБЕДА:")
    if CONFIG.get('after_lunch_action', False):
        sequence_display = CONFIG.get('after_lunch_sequence', '')
        # Маскируем текст, но показываем специальные клавиши
        masked_sequence = ""
        i = 0
        while i < len(sequence_display):
            if sequence_display[i] == '{':
                end = sequence_display.find('}', i)
                if end != -1:
                    masked_sequence += sequence_display[i:end+1]
                    i = end + 1
                else:
                    masked_sequence += '*'
                    i += 1
            else:
                masked_sequence += '*'
                i += 1
        
        print(f"  • Ввод последовательности: ✓ ({masked_sequence})")
        print(f"  • Задержка после обеда: {CONFIG.get('after_lunch_delay', 5)} сек")
    else:
        print(f"  • Ввод последовательности: ✗ (отключено)")
    
    print()
    print(f"🔌 ПРИ ЗАВЕРШЕНИИ ПРОГРАММЫ:")
    if CONFIG.get('shutdown_on_exit', False):
        print(f"  • Действие: ⚠️  ВЫКЛЮЧЕНИЕ компьютера (принудительное)")
    elif CONFIG.get('lock_on_exit', True):
        print(f"  • Действие: 🔒 Блокировка компьютера")
    else:
        print(f"  • Действие: Просто завершение программы")
    
    print("=" * 70)
    
    # Проверяем текущий статус
    if is_work_hours():
        on_break, break_type = is_break_time()
        if on_break:
            print(f"☕ Текущий статус: Перерыв ({break_type})")
        else:
            print(f"💼 Текущий статус: Рабочее время - активность включена")
    else:
        if should_simulate_afterhours():
            time_indicator = "🌅 Перед работой" if is_before_work() else "🌙 После работы"
            print(f"{time_indicator} - режим всплесков активности")
        else:
            print(f"🌙 Внерабочее время - активность отключена")

    print()
    print("Для остановки нажмите Ctrl+C")
    print()

    # === СОХРАНЕНИЕ ИНФОРМАЦИОННОЙ ЧАСТИ В ЛОГ ===
    if CONFIG['verbose_logging']:
        log("=" * 70)
        log("ПРОГРАММА СИМУЛЯЦИИ АКТИВНОСТИ ЗАПУЩЕНА")
        log("=" * 70)
        log(f"Конфигурация: {get_config_filename()}")
        log(f"Отслеживание: Мышь + Тачпад + Клавиатура")
        log("")
        
        log("РАСПИСАНИЕ НА СЕГОДНЯ:")
        log(f"  • Рабочее время: {SCHEDULE['work_start']} - {SCHEDULE['work_end']}")
        log(f"  • Обед: {SCHEDULE['lunch_start']} - {SCHEDULE['lunch_end']} " +
            f"({time_str_to_minutes(SCHEDULE['lunch_end']) - time_str_to_minutes(SCHEDULE['lunch_start'])} мин)")
        
        if SCHEDULE['breaks']:
            log(f"  • Перерывы:")
            for i, brk in enumerate(SCHEDULE['breaks'], 1):
                log(f"    {i}. {brk['start']} - {brk['end']} ({brk['duration']} мин)")
        else:
            log(f"  • Перерывы: нет")
        
        log("")
        log("ОСНОВНЫЕ ПАРАМЕТРЫ:")
        log(f"  • Порог бездействия: {CONFIG['min_idle_time']}-{CONFIG['max_idle_time']} сек")
        log(f"  • Интервал между действиями: {CONFIG['min_action_interval']}-{CONFIG['max_action_interval']} сек")
        log(f"  • Серия нажатий стрелок: {CONFIG['min_key_presses']}-{CONFIG['max_key_presses']} раз")
        log(f"  • Макс. диапазон мыши: {CONFIG['max_mouse_range']} пикс")
        
        log("")
        log("ТИПЫ ДЕЙСТВИЙ:")
        log(f"  • Движение мыши: {'✓' if CONFIG['use_mouse_move'] else '✗'} (вес: {CONFIG['action_weight_mouse_move']})")
        log(f"  • Стрелки клавиатуры: {'✓' if CONFIG['use_keyboard'] else '✗'} (вес: {CONFIG['action_weight_keyboard']})")
        log(f"  • Ctrl+Tab: {'✓' if CONFIG['use_keyboard'] else '✗'} (вес: {CONFIG['action_weight_ctrl_tab']})")
        log(f"  • Клики мыши: {'✓' if CONFIG['use_mouse_click'] else '✗'} (вес: {CONFIG['action_weight_mouse_click']})")
        log(f"  • Shift (безопасный): {'✓' if CONFIG['natural_behavior'] else '✗'} (вес: {CONFIG['action_weight_safe_key']})")
        log(f"  • Естественное поведение: {'✓' if CONFIG['natural_behavior'] else '✗'}")
        
        log("")
        afterhours_mode_names = {
            'disabled': '🚫 Отключен',
            'before_only': '🌅 Только до работы',
            'before_and_after': '🌅🌙 До и после работы'
        }
        log(f"ВНЕРАБОЧИЙ РЕЖИМ: {afterhours_mode_names.get(CONFIG['afterhours_mode'], CONFIG['afterhours_mode'])}")
        if CONFIG['afterhours_mode'] != 'disabled':
            log(f"  • Всплески активности: {CONFIG['afterhours_burst_duration_min']}-{CONFIG['afterhours_burst_duration_max']} сек")
            log(f"  • Интервал между всплесками: {CONFIG['afterhours_burst_interval_min']}-{CONFIG['afterhours_burst_interval_max']} мин")
        
        log("")
        log("ДЕЙСТВИЯ ПОСЛЕ ОБЕДА:")
        if CONFIG.get('after_lunch_action', False):
            sequence_display = CONFIG.get('after_lunch_sequence', '')
            masked_sequence = ""
            i = 0
            while i < len(sequence_display):
                if sequence_display[i] == '{':
                    end = sequence_display.find('}', i)
                    if end != -1:
                        masked_sequence += sequence_display[i:end+1]
                        i = end + 1
                    else:
                        masked_sequence += '*'
                        i += 1
                else:
                    masked_sequence += '*'
                    i += 1
            
            log(f"  • Ввод последовательности: ✓ ({masked_sequence})")
            log(f"  • Задержка после обеда: {CONFIG.get('after_lunch_delay', 5)} сек")
        else:
            log(f"  • Ввод последовательности: ✗ (отключено)")
        
        log("")
        log("ПРИ ЗАВЕРШЕНИИ ПРОГРАММЫ:")
        if CONFIG.get('shutdown_on_exit', False):
            log(f"  • Действие: ⚠️  ВЫКЛЮЧЕНИЕ компьютера (принудительное)")
        elif CONFIG.get('lock_on_exit', True):
            log(f"  • Действие: 🔒 Блокировка компьютера")
        else:
            log(f"  • Действие: Просто завершение программы")
        
        log("=" * 70)
        
        # Текущий статус
        if is_work_hours():
            on_break, break_type = is_break_time()
            if on_break:
                log(f"Текущий статус: Перерыв ({break_type})")
            else:
                log(f"Текущий статус: Рабочее время - активность включена")
        else:
            if should_simulate_afterhours():
                time_indicator = "Перед работой" if is_before_work() else "После работы"
                log(f"Текущий статус: {time_indicator} - режим всплесков активности")
            else:
                log(f"Текущий статус: Внерабочее время - активность отключена")
        
        log("")
        log(f"Файл лога: {log_file_path}")
        log(f"Начальная позиция мыши: {initial_mouse_position}")
        log("=" * 70)

    try:
        keyboard_listener.join()
    except KeyboardInterrupt:
        print("\n\n🛑 Программа остановлена пользователем")
        if CONFIG['verbose_logging']:
            print(f"📄 Лог сохранён в файл: {log_file_path}")
            log("")
            log("=" * 70)
            log(f"Программа остановлена пользователем. Всего действий: {len(action_history)}")
            log("=" * 70)
        
        # Выключение или блокировка компьютера при ручной остановке
        if CONFIG.get('shutdown_on_exit', False):
            print("🔌 ВЫКЛЮЧЕНИЕ КОМПЬЮТЕРА...")
            print("⚠️  ВНИМАНИЕ: Компьютер будет выключен через 2 секунды!")
            time.sleep(2)
            shutdown_computer()
        elif CONFIG.get('lock_on_exit', True):
            print("🔒 Блокировка компьютера...")
            time.sleep(1)
            lock_computer()