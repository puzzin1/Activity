"""
Конфигурация pytest для автоматического мокирования pynput.

Этот модуль настраивает моки для pynput, чтобы тесты могли выполняться
без X-сервера или других системных зависимостей.
"""

import sys
from unittest.mock import MagicMock, Mock


def pytest_configure(config):
    """
    Автоматически мокирует pynput и tkinter при запуске тестов.

    Это предотвращает ошибки при импорте модулей, которые используют pynput и tkinter.
    """
    # Мок для tkinter
    tkinter_mock = MagicMock()
    sys.modules['tkinter'] = tkinter_mock
    sys.modules['tkinter.messagebox'] = tkinter_mock

    # Создаем мок для pynput.mouse
    pynput_mouse = MagicMock()
    pynput_mouse.Button = Mock()
    pynput_mouse.Button.left = 'left'
    pynput_mouse.Button.right = 'right'

    # Создаем мок для контроллера мыши
    mouse_controller_mock = MagicMock()
    mouse_controller_mock.position = (0, 0)
    mouse_controller_mock.click = MagicMock()
    pynput_mouse.Controller = MagicMock(return_value=mouse_controller_mock)

    # Создаем мок для pynput.keyboard
    pynput_keyboard = MagicMock()
    pynput_keyboard.Key = Mock()
    pynput_keyboard.Key.enter = 'enter'
    pynput_keyboard.Key.tab = 'tab'
    pynput_keyboard.Key.space = 'space'
    pynput_keyboard.Key.shift = 'shift'
    pynput_keyboard.Key.ctrl_l = 'ctrl_l'
    pynput_keyboard.Key.ctrl_r = 'ctrl_r'
    pynput_keyboard.Key.alt_l = 'alt_l'
    pynput_keyboard.Key.alt_r = 'alt_r'
    pynput_keyboard.Key.up = 'up'
    pynput_keyboard.Key.down = 'down'
    pynput_keyboard.Key.left = 'left'
    pynput_keyboard.Key.right = 'right'
    pynput_keyboard.KeyCode = MagicMock

    # Создаем мок для контроллера клавиатуры
    keyboard_controller_mock = MagicMock()
    keyboard_controller_mock.press = MagicMock()
    keyboard_controller_mock.release = MagicMock()
    keyboard_controller_mock.type = MagicMock()
    pynput_keyboard.Controller = MagicMock(return_value=keyboard_controller_mock)

    # Регистрируем моки в sys.modules
    sys.modules['pynput'] = MagicMock()
    sys.modules['pynput'].mouse = pynput_mouse
    sys.modules['pynput'].keyboard = pynput_keyboard
    sys.modules['pynput.mouse'] = pynput_mouse
    sys.modules['pynput.keyboard'] = pynput_keyboard
