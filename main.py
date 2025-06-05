import tkinter as tk
from tkinter import ttk, font as tkfont, messagebox, scrolledtext
from Search import YouTubeSearcher
from Update import Updater
from datetime import datetime
import os
import logging
import sys
import threading
import queue
import pandas as pd

# Конфигурация приложения
APP_NAME = "XPARSER"
APP_VERSION = "0.92"

# Настройка глобального логгера
def setup_logging():
    os.makedirs("logs", exist_ok=True)
    log_file = f"logs/debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logging.getLogger('WDM').setLevel(logging.INFO)
    return log_file

# Инициализация логгера и сохранение пути к лог-файлу
log_file = setup_logging()
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

        # Шрифты
        self.main_font = tkfont.Font(family="Helvetica", size=12)
        self.button_font = tkfont.Font(family="Helvetica", size=12, weight="bold")
        self.title_font = tkfont.Font(family="Helvetica", size=14, weight="bold")

        # Состояние
        self.search_running = False
        self.search_thread = None
        self.searcher = None
        self.result_queue = queue.Queue()
        self.excel_path = None
        self.thread_count = 3

        # Инициализация интерфейса
        self._setup_ui()
        self._center_window()
        self._setup_logging()
        self.root.after(100, self._process_result_queue)

        logger.info(f"{APP_NAME} v{APP_VERSION} запущен")

    def _setup_logging(self):
        """Настройка вывода логов в интерфейс"""
        if hasattr(self, 'log_text'):
            text_handler = TextHandler(self.log_text)
            text_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            logger.addHandler(text_handler)
            logging.getLogger('WDM').addHandler(text_handler)

    def _setup_ui(self):
        """Инициализация пользовательского интерфейса"""
        self.tab_control = ttk.Notebook(self.root)

        # Вкладка поиска
        search_frame = ttk.Frame(self.tab_control)
        self.tab_control.add(search_frame, text="Поиск")

        # Панель управления
        control_frame = ttk.Frame(search_frame)
        control_frame.pack(fill="x", pady=10)

        # Кнопки
        self.search_btn = tk.Button(
            control_frame,
            text="НАЧАТЬ ПОИСК",
            font=self.button_font,
            width=20,
            height=2,
            bg="black",
            fg="white",
            command=self.start_search
        )
        self.search_btn.pack(side="left", padx=5)

        self.stop_btn = tk.Button(
            control_frame,
            text="ОСТАНОВИТЬ",
            font=self.button_font,
            width=20,
            height=2,
            bg="#ff4444",
            fg="white",
            state="disabled",
            command=self.stop_search
        )
        self.stop_btn.pack(side="left", padx=5)

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

        # Текстовые поля
        self.results_text = scrolledtext.ScrolledText(
            search_frame,
            wrap=tk.WORD,
            height=15,
            font=tkfont.Font(size=10)
        )
        self.results_text.pack(fill="both", expand=True, padx=10, pady=5)
        self.results_text.config(state="disabled")

        # Текстовое поле для логов
        self.log_text = scrolledtext.ScrolledText(
            search_frame,
            wrap=tk.WORD,
            height=8,
            font=tkfont.Font(size=10)
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=5)
        self.log_text.config(state="disabled")

        # Вкладка конфигурации
        config_frame = ttk.Frame(self.tab_control)
        self.tab_control.add(config_frame, text="Конфигурация")

        ttk.Label(config_frame, text="Теги для поиска (через запятую):",
                  font=self.main_font).pack(pady=(10, 5))

        self.tags_entry = tk.Text(
            config_frame,
            height=5,
            width=50,
            wrap=tk.WORD,
            font=self.main_font
        )
        self.tags_entry.pack(padx=10, pady=5)

        ttk.Button(
            config_frame,
            text="Сохранить настройки",
            command=self.save_config
        ).pack(pady=10)

        # Вкладка "О программе"
        about_frame = ttk.Frame(self.tab_control)
        self.tab_control.add(about_frame, text="О программе")

        content_frame = ttk.Frame(about_frame)
        content_frame.pack(expand=True, fill="both", padx=20, pady=20)

        ttk.Label(
            content_frame,
            text=f"{APP_NAME}",
            font=self.title_font,
            justify="center"
        ).pack(pady=5)

        ttk.Label(
            content_frame,
            text=f"Версия: {APP_VERSION}",
            font=self.main_font,
            justify="center"
        ).pack(pady=5)

        tk.Button(
            content_frame,
            text="ПРОВЕРИТЬ ОБНОВЛЕНИЯ",
            font=self.button_font,
            width=25,
            height=2,
            bg="black",
            fg="white",
            command=self.check_for_updates
        ).pack(pady=20)

        ttk.Label(
            content_frame,
            text="Автоматический парсер YouTube каналов\nс извлечением Telegram ссылок",
            font=tkfont.Font(size=10),
            justify="center"
        ).pack(pady=10)

        ttk.Label(
            content_frame,
            text="© 2025\nA3otuk",
            font=tkfont.Font(size=9),
            justify="center"
        ).pack(pady=5)

        self.tab_control.pack(expand=1, fill="both")

    def _center_window(self):
        """Центрирование окна на экране"""
        self.root.update_idletasks()
        width = 800
        height = 600
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def _process_result_queue(self):
        """Обработка очереди результатов"""
        try:
            while True:
                result = self.result_queue.get_nowait()
                self._display_result(result)
                self._save_to_excel(result)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._process_result_queue)

    def _display_result(self, result):
        """Отображение результата в интерфейсе"""
        self.results_text.config(state="normal")
        self.results_text.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] YouTube: {result['youtube_url']}\n")
        self.results_text.insert("end", f"Telegram: {result['telegram_url']}\n\n")
        self.results_text.see("end")
        self.results_text.config(state="disabled")

    def _save_to_excel(self, result):
        """Сохранение результатов в Excel файл"""
        try:
            os.makedirs("results", exist_ok=True)

            # Если файл еще не создан
            if self.excel_path is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                self.excel_path = f"results/results_{timestamp}.xlsx"

                # Создаем новый DataFrame
                df = pd.DataFrame([{
                    'YouTube URL': result['youtube_url'],
                    'Telegram URL': result['telegram_url'],
                    'Дата': datetime.now().strftime('%Y-%m-%d'),
                    'Время': datetime.now().strftime('%H:%M:%S')
                }])

                # Сохраняем в новый файл
                df.to_excel(
                    self.excel_path,
                    sheet_name='Результаты',
                    index=False,
                    engine='openpyxl'
                )
                logger.info(f"Создан новый Excel файл: {self.excel_path}")
            else:
                # Если файл уже существует, читаем его и дописываем данные
                try:
                    # Читаем существующие данные
                    existing_df = pd.read_excel(self.excel_path, engine='openpyxl')

                    # Создаем DataFrame с новыми данными
                    new_data = {
                        'YouTube URL': result['youtube_url'],
                        'Telegram URL': result['telegram_url'],
                        'Дата': datetime.now().strftime('%Y-%m-%d'),
                        'Время': datetime.now().strftime('%H:%M:%S')
                    }

                    # Объединяем старые и новые данные
                    updated_df = pd.concat([existing_df, pd.DataFrame([new_data])], ignore_index=True)

                    # Перезаписываем файл с обновленными данными
                    updated_df.to_excel(
                        self.excel_path,
                        sheet_name='Результаты',
                        index=False,
                        engine='openpyxl'
                    )
                except Exception as e:
                    logger.error(f"Ошибка при дописывании в Excel: {str(e)}")
                    # Если не удалось дописать, создаем новый файл
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    self.excel_path = f"results/results_{timestamp}.xlsx"
                    self._save_to_excel(result)  # Рекурсивный вызов для создания нового файла

        except Exception as e:
            logger.error(f"Ошибка сохранения в Excel: {str(e)}")

    def _update_thread_count(self):
        """Обновление количества потоков"""
        try:
            self.thread_count = int(self.thread_spinbox.get())
            if not 1 <= self.thread_count <= 10:
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

        query = self.tags_entry.get("1.0", "end-1c").strip()
        if not query:
            messagebox.showwarning("Ошибка", "Введите теги для поиска")
            return

        self.search_running = True
        self.search_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.results_text.config(state="normal")
        self.results_text.delete(1.0, "end")
        self.results_text.config(state="disabled")
        self.excel_path = None  # Сброс для создания нового файла

        self._update_thread_count()

        self.searcher = YouTubeSearcher(
            result_callback=lambda y, t: self.result_queue.put({
                'youtube_url': y,
                'telegram_url': t or "Not found"
            }),
            thread_count=self.thread_count
        )

        self.search_thread = threading.Thread(
            target=self.searcher.continuous_search,
            args=(query,),
            daemon=True
        )
        self.search_thread.start()

        logger.info(f"Запущен поиск: '{query}'")

    def stop_search(self):
        """Остановка поиска"""
        if not self.search_running:
            return

        self.search_running = False
        self.search_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

        if self.searcher:
            self.searcher.stop()

        logger.info("Поиск остановлен")

    def save_config(self):
        """Сохранение настроек"""
        try:
            tags = self.tags_entry.get("1.0", "end-1c").strip()
            if not tags:
                raise ValueError("Теги не могут быть пустыми")

            messagebox.showinfo("Сохранено", "Настройки успешно сохранены!")
            logger.info(f"Сохранены теги: '{tags[:50]}...'")
        except ValueError as e:
            messagebox.showerror("Ошибка", str(e))
            logger.error(f"Ошибка сохранения: {str(e)}")

    def check_for_updates(self):
        """Проверка обновлений"""
        self.updater = Updater(current_version=APP_VERSION)
        self.updater.show_update_dialog(self.root)

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = XParserApp(root)
        root.mainloop()
    except Exception as e:
        logger.critical(f"Критическая ошибка: {str(e)}", exc_info=True)
        messagebox.showerror("Ошибка", f"Программа завершена с ошибкой:\n{str(e)}\n\nПодробности в логах: {log_file}")