"""
Вспомогательный модуль с общими функциями.
Содержит утилиты для работы со временем, системные функции и т.д.
"""

import time
import random
import os
import sys
import platform
import subprocess
from subprocess import CalledProcessError
import tkinter as tk
from tkinter import messagebox
from threading import Timer
from datetime import datetime
from typing import List, Tuple, Union


def time_str_to_minutes(time_str: str) -> int:
    """
    Конвертирует строку времени 'HH:MM' в минуты с начала дня.

    Args:
        time_str (str): Время в формате 'HH:MM'

    Returns:
        int: Количество минут с начала дня (0-1439)

    Example:
        time_str_to_minutes('09:30') -> 570
        time_str_to_minutes('14:15') -> 855
    """
    h, m = map(int, time_str.split(':'))
    return h * 60 + m


def minutes_to_time_str(minutes: int) -> str:
    """
    Конвертирует минуты с начала дня в строку 'HH:MM'.

    Args:
        minutes (int): Количество минут с начала дня

    Returns:
        str: Время в формате 'HH:MM'

    Example:
        minutes_to_time_str(570) -> '09:30'
        minutes_to_time_str(855) -> '14:15'
    """
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def get_current_time_minutes() -> int:
    """
    Возвращает текущее время в минутах с начала дня.

    Returns:
        int: Количество минут с начала дня (0-1439)
    """
    now = datetime.now()
    return now.hour * 60 + now.minute


def parse_key_sequence(sequence: str) -> List[str]:
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


def lock_computer() -> Tuple[bool, str]:
    """Блокирует компьютер в зависимости от операционной системы"""
    system = platform.system()

    try:
        if system == "Windows":
            # Windows: использует rundll32 для блокировки
            subprocess.call(['rundll32.exe', 'user32.dll,LockWorkStation'])
            return True, "🔒 Компьютер заблокирован (Windows)"
        elif system == "Darwin":  # macOS
            # macOS: использует pmset для блокировки экрана
            subprocess.call(['/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession', '-suspend'])
            return True, "🔒 Компьютер заблокирован (macOS)"
        elif system == "Linux":
            # Linux: пробует различные методы блокировки
            try:
                # Попытка 1: gnome-screensaver
                subprocess.call(['gnome-screensaver-command', '--lock'])
            except Exception:
                try:
                    # Попытка 2: xdg-screensaver
                    subprocess.call(['xdg-screensaver', 'lock'])
                except Exception:
                    try:
                        # Попытка 3: loginctl
                        subprocess.call(['loginctl', 'lock-session'])
                    except Exception:
                        return False, "⚠️ Не удалось заблокировать компьютер (Linux)"
            return True, "🔒 Компьютер заблокирован (Linux)"
        else:
            return False, f"⚠️ Блокировка не поддерживается для ОС: {system}"
    except Exception as e:
        return False, f"⚠️ Ошибка при блокировке компьютера: {e}"


def shutdown_computer() -> Tuple[bool, str]:
    """Принудительно выключает компьютер без запроса подтверждения"""
    system = platform.system()

    try:
        if system == "Windows":
            # Windows: принудительное выключение через shutdown
            subprocess.call(['shutdown', '/s', '/f', '/t', '0'])
            return True, "🔌 Компьютер выключается (Windows)"
        elif system == "Darwin":  # macOS
            # macOS: принудительное выключение
            try:
                subprocess.run(['sudo', 'shutdown', '-h', 'now'], check=True)
                return True, "🔌 Компьютер выключается (macOS)"
            except CalledProcessError:
                return False, "⚠️ Не удалось выключить компьютер (macOS): требуется sudo без пароля или команда недоступна"
            except FileNotFoundError:
                return False, "⚠️ Не удалось выключить компьютер (macOS): команда shutdown не найдена"
        elif system == "Linux":
            # Linux: принудительное выключение
            try:
                subprocess.call(['systemctl', 'poweroff'])
            except Exception:
                try:
                    subprocess.call(['shutdown', '-h', 'now'])
                except Exception:
                    return False, "⚠️ Не удалось выключить компьютер (Linux)"
            return True, "🔌 Компьютер выключается (Linux)"
        else:
            return False, f"⚠️ Выключение не поддерживается для ОС: {system}"
    except Exception as e:
        return False, f"⚠️ Ошибка при выключении компьютера: {e}"