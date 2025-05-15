import tkinter as tk
from tkinter import ttk, font as tkfont, messagebox
from Search import YouTubeSearcher
from Update import Updater
from datetime import datetime
import os
import logging
from logging.handlers import RotatingFileHandler
from Search import YouTubeSearcher

# Конфигурация приложения
APP_NAME = "XPARSER"
APP_VERSION = "0.3"  # Обновленная версия

# Настройка логирования
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('ErrLogs.txt', maxBytes=102400, backupCount=3),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class XParserApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION}")  # Используем новое название
        self.root.geometry("650x550")

        # Инициализация модуля обновлений
        self.updater = Updater(current_version=APP_VERSION)

        # Конфигурационные переменные
        self.search_tags = ""
        self.max_results = 10

        # Настройка шрифтов
        self.main_font = tkfont.Font(family="Helvetica", size=12)
        self.button_font = tkfont.Font(family="Helvetica", size=12, weight="bold")
        self.title_font = tkfont.Font(family="Helvetica", size=14, weight="bold")

        # Создание интерфейса
        self._setup_ui()
        self._center_window()
        logger.info(f"{APP_NAME} v{APP_VERSION} запущен")

    def _setup_ui(self):
        """Настройка основного интерфейса с вкладками"""
        self.tab_control = ttk.Notebook(self.root)

        # Вкладка поиска
        self._setup_search_tab()

        # Вкладка конфигурации
        self._setup_config_tab()

        # Вкладка о программе
        self._setup_about_tab()

        self.tab_control.pack(expand=1, fill="both")

    def _setup_about_tab(self):
        """Вкладка с информацией о программе"""
        tab_frame = ttk.Frame(self.tab_control)
        self.tab_control.add(tab_frame, text="О программе")

        frame = ttk.Frame(tab_frame)
        frame.pack(expand=True, fill="both", padx=20, pady=20)

        # Название программы и версия
        ttk.Label(
            frame,
            text=f"{APP_NAME}",
            font=self.title_font,
            justify="center"
        ).pack(pady=5)

        ttk.Label(
            frame,
            text=f"Версия: {APP_VERSION}",
            font=self.main_font,
            justify="center"
        ).pack(pady=5)

        # Кнопка проверки обновлений
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

        # Дополнительная информация
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

    def _setup_search_tab(self):
        """Вкладка поиска"""
        tab_frame = ttk.Frame(self.tab_control)
        self.tab_control.add(tab_frame, text="Поиск")

        frame = ttk.Frame(tab_frame)
        frame.pack(expand=True, fill="both", padx=20, pady=20)

        # Кнопка поиска
        self.search_btn = tk.Button(
            frame,
            text="НАЧАТЬ ПОИСК",
            font=self.button_font,
            width=20,
            height=2,
            bg="black",
            fg="white",
            command=self.start_search
        )
        self.search_btn.pack(pady=10)

        # Область результатов
        self.results_text = tk.Text(
            frame,
            wrap=tk.WORD,
            height=22,
            padx=10,
            pady=10,
            font=tkfont.Font(size=10)
        )
        self.results_text.pack(fill="both", expand=True)

        # Скроллбар
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")
        self.results_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.results_text.yview)

    def check_for_updates(self):
        """Проверка обновлений программы"""
        self.updater.show_update_dialog(self.root)

    def _setup_config_tab(self):
        """Вкладка конфигурации"""
        tab_frame = ttk.Frame(self.tab_control)
        self.tab_control.add(tab_frame, text="Конфигурация")

        frame = ttk.Frame(tab_frame)
        frame.pack(expand=True, fill="both", padx=20, pady=20)

        # Макс. количество результатов
        ttk.Label(frame, text="Макс. количество результатов:", font=self.main_font).pack(pady=(0, 5))

        validate_cmd = (self.root.register(self._validate_number), '%P')
        self.max_results_entry = ttk.Entry(
            frame,
            font=self.main_font,
            width=10,
            validate='key',
            validatecommand=validate_cmd
        )
        self.max_results_entry.pack()
        self.max_results_entry.insert(0, str(self.max_results))

        # Теги для поиска
        ttk.Label(frame, text="Теги для поиска (через запятую):", font=self.main_font).pack(pady=(20, 5))

        self.tags_entry = tk.Text(
            frame,
            height=5,
            width=40,
            wrap=tk.WORD,
            padx=10,
            pady=10,
            font=self.main_font
        )
        self.tags_entry.pack()
        self.tags_entry.insert("1.0", self.search_tags)

        # Кнопка сохранения
        ttk.Button(
            frame,
            text="Сохранить настройки",
            command=self.save_config
        ).pack(pady=20)

    def _validate_number(self, new_value):
        """Валидация ввода - только цифры"""
        return new_value.isdigit() or new_value == ""

    def _center_window(self):
        """Центрирование окна на экране"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'+{x}+{y}')

    def start_search(self):
        """Запуск поиска каналов"""
        self.results_text.delete(1.0, tk.END)

        try:
            # Получаем параметры
            search_query = self.tags_entry.get("1.0", tk.END).strip()
            if not search_query:
                messagebox.showwarning("Ошибка", "Введите теги для поиска")
                return

            max_results = int(self.max_results_entry.get())

            # Логируем начало поиска
            logger.info(f"Начало поиска: '{search_query}', max {max_results}")

            # Выводим информацию
            self.results_text.insert(tk.END, f"Поиск запущен: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            self.results_text.insert(tk.END, f"Запрос: {search_query}\n")
            self.results_text.insert(tk.END, f"Лимит результатов: {max_results}\n\n")
            self.results_text.update()

            # Выполняем поиск
            searcher = YouTubeSearcher()
            found_urls = searcher.search(search_query, max_results)

            # Выводим результаты
            self.results_text.insert(tk.END, "\n=== РЕЗУЛЬТАТЫ ===\n\n")

            if not found_urls:
                self.results_text.insert(tk.END, "Новых каналов не найдено\n")
            else:
                for url in found_urls:
                    self.results_text.insert(tk.END, f"{url}\n")

            # Сохраняем в файл
            self._save_results(found_urls, search_query)

            # Статистика
            stats = searcher.get_stats()
            self.results_text.insert(tk.END, f"\nСтатистика: {stats}\n")
            self.results_text.insert(tk.END, "\nПоиск завершен!\n")

        except ValueError as e:
            logger.error(f"Ошибка ввода: {str(e)}")
            messagebox.showerror("Ошибка", "Некорректное число результатов")
        except Exception as e:
            logger.error(f"Ошибка поиска: {str(e)}", exc_info=True)
            messagebox.showerror("Ошибка", f"Ошибка при поиске: {str(e)}")

    def _save_results(self, urls, query):
        """Сохранение результатов в файл"""
        if not urls:
            return

        try:
            os.makedirs("results", exist_ok=True)
            filename = f"results/{datetime.now().strftime('%Y%m%d_%H%M')}_{query[:15]}.txt"

            with open(filename, 'w', encoding='utf-8') as f:
                f.write("\n".join(urls))

            self.results_text.insert(tk.END, f"\nРезультаты сохранены в: {filename}\n")
            logger.info(f"Результаты сохранены в {filename}")
        except Exception as e:
            logger.error(f"Ошибка сохранения: {str(e)}")
            self.results_text.insert(tk.END, "\nОшибка при сохранении результатов\n")

    def save_config(self):
        """Сохранение настроек поиска"""
        try:
            # Проверяем число результатов
            max_results = self.max_results_entry.get().strip()
            if not max_results.isdigit() or int(max_results) <= 0:
                raise ValueError("Лимит должен быть положительным числом")

            self.max_results = int(max_results)

            # Проверяем теги
            self.search_tags = self.tags_entry.get("1.0", tk.END).strip()
            if not self.search_tags:
                raise ValueError("Теги не могут быть пустыми")

            messagebox.showinfo("Сохранено", "Настройки успешно сохранены!")
            logger.info(f"Сохранены настройки: lim={self.max_results}, tags='{self.search_tags[:20]}...'")

        except ValueError as e:
            logger.error(f"Ошибка валидации: {str(e)}")
            messagebox.showerror("Ошибка", str(e))
        except Exception as e:
            logger.error(f"Ошибка сохранения: {str(e)}", exc_info=True)
            messagebox.showerror("Ошибка", f"Неизвестная ошибка: {str(e)}")


if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = XParserApp(root)  # Используем новое имя класса
        root.mainloop()
    except Exception as e:
        logger.critical(f"Критическая ошибка в {APP_NAME} v{APP_VERSION}: {str(e)}", exc_info=True)
        messagebox.showerror("Ошибка", f"Произошла критическая ошибка в {APP_NAME} v{APP_VERSION}. Проверьте ErrLogs.txt")