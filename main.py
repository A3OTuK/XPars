import tkinter as tk
from tkinter import ttk, font as tkfont, messagebox
from Search import YouTubeSearcher
from Update import Updater
from datetime import datetime
import os
import logging
import sys
import threading
import queue
from tkinter.scrolledtext import ScrolledText

# Конфигурация приложения
APP_NAME = "XPARSER"
APP_VERSION = "0.91"

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log', mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        self.text_widget.config(state="normal")
        self.text_widget.insert("end", msg + "\n")
        self.text_widget.see("end")
        self.text_widget.config(state="disabled")


class XParserApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION}")

        # Проверка режима работы
        self.is_frozen = getattr(sys, 'frozen', False)
        logger.info(f"Режим работы: {'EXE' if self.is_frozen else 'скрипт'}")

        # Инициализация модуля обновлений
        self.updater = Updater(current_version=APP_VERSION)

        # Переменные состояния
        self.search_tags = ""
        self.search_running = False
        self.search_thread = None
        self.thread_count = 3
        self.result_queue = queue.Queue()
        self.searcher = None

        # Настройка шрифтов
        self.main_font = tkfont.Font(family="Helvetica", size=12)
        self.button_font = tkfont.Font(family="Helvetica", size=12, weight="bold")
        self.title_font = tkfont.Font(family="Helvetica", size=14, weight="bold")

        # Создание интерфейса
        self._setup_ui()
        self._center_window()
        self._setup_logging()

        # Запуск обработчика очереди
        self.root.after(100, self._process_result_queue)
        logger.info(f"{APP_NAME} v{APP_VERSION} запущен")

    def _setup_ui(self):
        """Настройка интерфейса"""
        self.tab_control = ttk.Notebook(self.root)

        # Вкладка поиска
        tab_frame = ttk.Frame(self.tab_control)
        self.tab_control.add(tab_frame, text="Поиск")
        frame = ttk.Frame(tab_frame)
        frame.pack(expand=True, fill="both", padx=20, pady=20)

        # Панель управления
        control_frame = ttk.Frame(frame)
        control_frame.pack(fill="x", pady=(0, 10))

        # Кнопки управления
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(side="left")

        self.search_btn = tk.Button(
            btn_frame,
            text="НАЧАТЬ ПОИСК",
            font=self.button_font,
            width=15,
            height=2,
            bg="black",
            fg="white",
            command=self.start_search
        )
        self.search_btn.pack(side="left", padx=(0, 10))

        self.stop_btn = tk.Button(
            btn_frame,
            text="ОСТАНОВИТЬ",
            font=self.button_font,
            width=15,
            height=2,
            bg="#ff4444",
            fg="white",
            state="disabled",
            command=self.stop_search
        )
        self.stop_btn.pack(side="left")

        # Настройка потоков
        thread_frame = ttk.Frame(control_frame)
        thread_frame.pack(side="right", padx=10)

        ttk.Label(thread_frame, text="Потоки:", font=self.main_font).pack(side="left")

        self.thread_spinbox = tk.Spinbox(
            thread_frame,
            from_=1,
            to=10,
            width=3,
            font=self.main_font,
            command=self._update_thread_count
        )
        self.thread_spinbox.pack(side="left", padx=5)
        self.thread_spinbox.delete(0, "end")
        self.thread_spinbox.insert(0, "3")

        # Область результатов
        results_frame = ttk.Frame(frame)
        results_frame.pack(fill="both", expand=True)

        self.results_text = ScrolledText(
            results_frame,
            wrap=tk.WORD,
            height=12,
            padx=10,
            pady=10,
            font=tkfont.Font(size=10)
        )
        self.results_text.pack(fill="both", expand=True)
        self.results_text.config(state="disabled")

        # Логи
        log_frame = ttk.Frame(frame)
        log_frame.pack(fill="both", expand=True)

        self.log_text = ScrolledText(
            log_frame,
            wrap=tk.WORD,
            height=8,
            padx=10,
            pady=10,
            font=tkfont.Font(size=10),
            state="disabled"
        )
        self.log_text.pack(fill="both", expand=True)

        # Вкладка конфигурации
        self._setup_config_tab()

        # Вкладка о программе
        self._setup_about_tab()

        self.tab_control.pack(expand=1, fill="both")

    def _setup_config_tab(self):
        """Вкладка конфигурации"""
        tab_frame = ttk.Frame(self.tab_control)
        self.tab_control.add(tab_frame, text="Конфигурация")

        frame = ttk.Frame(tab_frame)
        frame.pack(expand=True, fill="both", padx=20, pady=20)

        ttk.Label(frame, text="Теги для поиска (через запятую):", font=self.main_font).pack(pady=(0, 5))

        self.tags_entry = tk.Text(
            frame,
            height=5,
            width=40,
            wrap=tk.WORD,
            padx=10,
            pady=10,
            font=self.main_font
        )
        self.tags_entry.pack(fill="x")

        ttk.Button(
            frame,
            text="Сохранить настройки",
            command=self.save_config
        ).pack(pady=20)

    def _setup_about_tab(self):
        """Вкладка о программе"""
        tab_frame = ttk.Frame(self.tab_control)
        self.tab_control.add(tab_frame, text="О программе")

        frame = ttk.Frame(tab_frame)
        frame.pack(expand=True, fill="both", padx=20, pady=20)

        ttk.Label(frame, text=f"{APP_NAME}", font=self.title_font, justify="center").pack(pady=5)
        ttk.Label(frame, text=f"Версия: {APP_VERSION}", font=self.main_font, justify="center").pack(pady=5)

        tk.Button(
            frame,
            text="ПРОВЕРИТЬ ОБНОВЛЕНИЯ",
            font=self.button_font,
            width=25,
            height=2,
            bg="black",
            fg="white",
            command=self.check_for_updates
        ).pack(pady=20)

        ttk.Label(
            frame,
            text="Автоматический парсер YouTube каналов\nс извлечением Telegram ссылок",
            font=tkfont.Font(size=10),
            justify="center"
        ).pack(pady=10)

        ttk.Label(
            frame,
            text="© 2025\nA3otuk",
            font=tkfont.Font(size=9),
            justify="center"
        ).pack(pady=5)

    def _setup_logging(self):
        """Настройка вывода логов в интерфейс"""
        text_handler = TextHandler(self.log_text)
        text_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(text_handler)

    def _process_result_queue(self):
        """Обработка очереди результатов"""
        try:
            while True:
                result = self.result_queue.get_nowait()
                self._display_result(result)
                self._save_to_file(result)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._process_result_queue)

    def _display_result(self, result):
        """Отображение результата"""
        self.results_text.config(state="normal")
        self.results_text.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] YouTube: {result['youtube_url']}\n")
        self.results_text.insert("end", f"Telegram: {result['telegram_url']}\n\n")
        self.results_text.see("end")
        self.results_text.config(state="disabled")

    def _save_to_file(self, result):
        """Сохранение результата в файл"""
        try:
            os.makedirs("results", exist_ok=True)
            filename = f"results/results_{datetime.now().strftime('%Y%m%d')}.txt"

            with open(filename, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().strftime('%H:%M:%S')}] YouTube: {result['youtube_url']}\n")
                f.write(f"Telegram: {result['telegram_url']}\n\n")
        except Exception as e:
            logger.error(f"Ошибка сохранения: {str(e)}")

    def _update_thread_count(self):
        """Обновление количества потоков"""
        try:
            self.thread_count = int(self.thread_spinbox.get())
            if self.thread_count < 1 or self.thread_count > 10:
                raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка", "Введите число от 1 до 10")
            self.thread_spinbox.delete(0, "end")
            self.thread_spinbox.insert(0, "3")
            self.thread_count = 3

    def start_search(self):
        """Запуск поиска"""
        if self.search_running:
            return

        self.search_running = True
        self.search_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.results_text.config(state="normal")
        self.results_text.delete(1.0, tk.END)
        self.results_text.config(state="disabled")

        search_query = self.tags_entry.get("1.0", tk.END).strip()
        if not search_query:
            messagebox.showwarning("Ошибка", "Введите теги для поиска")
            self.stop_search()
            return

        self._update_thread_count()

        logger.info(f"Запуск поиска по запросу: {search_query}")
        logger.info(f"Используется потоков: {self.thread_count}")

        # Создаем поисковик с callback'ом
        self.searcher = YouTubeSearcher(
            result_callback=lambda y, t: self.result_queue.put({
                'youtube_url': y,
                'telegram_url': t or "Not found"
            }),
            thread_count=self.thread_count
        )

        # Запускаем в отдельном потоке
        self.search_thread = threading.Thread(
            target=self.searcher.continuous_search,
            args=(search_query,),
            daemon=True
        )
        self.search_thread.start()

    def stop_search(self):
        """Остановка поиска"""
        if not self.search_running:
            return

        self.search_running = False
        self.search_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

        if self.searcher:
            self.searcher.stop()

        logger.info("Поиск остановлен пользователем")

    def save_config(self):
        """Сохранение настроек"""
        try:
            self.search_tags = self.tags_entry.get("1.0", tk.END).strip()
            if not self.search_tags:
                raise ValueError("Теги не могут быть пустыми")

            messagebox.showinfo("Сохранено", "Настройки успешно сохранены!")
            logger.info(f"Сохранены теги: '{self.search_tags[:20]}...'")
        except ValueError as e:
            logger.error(f"Ошибка валидации: {str(e)}")
            messagebox.showerror("Ошибка", str(e))
        except Exception as e:
            logger.error(f"Ошибка сохранения: {str(e)}", exc_info=True)
            messagebox.showerror("Ошибка", f"Неизвестная ошибка: {str(e)}")

    def check_for_updates(self):
        """Проверка обновлений"""
        self.updater.show_update_dialog(self.root)

    def _center_window(self):
        """Центрирование окна"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'+{x}+{y}')


if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = XParserApp(root)
        root.mainloop()
    except Exception as e:
        logger.critical(f"FATAL ERROR: {str(e)}", exc_info=True)
        messagebox.showerror("Critical Error", f"Error: {str(e)}\nSee debug.log")