import os
import time
import logging
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class YouTubeSearcher:
    def __init__(self):
        """Инициализация класса."""
        self.stats = {
            "total_queries": 0,
            "total_channels_found": 0,
            "last_search_time": None,
        }
        self.results_dir = "results"
        self.found_channels = set()  # Множество для хранения уже найденных каналов
        os.makedirs(self.results_dir, exist_ok=True)  # Создаем папку для результатов

    def save_results_to_excel(self, query, urls):
        """
        Сохраняет результаты поиска в Excel-файл.
        :param query: Поисковый запрос.
        :param urls: Список ссылок на каналы.
        :return: Путь к сохраненному файлу или None в случае ошибки.
        """
        if not urls:
            return None

        try:
            # Формируем имя файла на основе запроса
            query_safe = "".join([c for c in query if c.isalnum() or c in (" ", "_")]).strip()[:50]
            filename = f"{query_safe}.xlsx"
            file_path = os.path.join(self.results_dir, filename)

            # Формируем данные для записи
            date_str = datetime.now().strftime("%d.%m.%Y %H:%M")  # Формат "число.месяц.год часы:минуты"
            new_data = pd.DataFrame({
                "Результаты": [date_str] + urls  # Дата в первой ячейке, ссылки ниже
            })

            # Если файл уже существует, загружаем старые данные
            if os.path.exists(file_path):
                old_data = pd.read_excel(file_path, header=None)
                # Убедимся, что старые данные имеют ту же структуру
                old_data.columns = ["Результаты"]
                combined_data = pd.concat([old_data, new_data], ignore_index=True)
            else:
                combined_data = new_data

            # Сохраняем в Excel
            combined_data.to_excel(file_path, index=False, header=False)
            logger.info(f"Результаты сохранены в {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Ошибка при сохранении в Excel: {str(e)}", exc_info=True)
            return None

    def setup_driver(self):
        """Настраивает и возвращает драйвер Chrome в headless режиме."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-notifications")

        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=chrome_options)

    def scroll_to_bottom(self, driver):
        """Прокручивает страницу до конца."""
        last_height = driver.execute_script("return document.documentElement.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.documentElement.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def get_channel_links(self, search_query, max_retries=3):
        """
        Ищет ссылки на каналы по заданному запросу.
        :param search_query: Поисковый запрос.
        :param max_retries: Максимальное количество попыток.
        :return: Список ссылок на каналы.
        """
        for attempt in range(max_retries):
            driver = None
            try:
                driver = self.setup_driver()
                search_url = f"https://www.youtube.com/results?search_query={search_query.replace(' ', '+')}&sp=EgQIBRAB"
                driver.get(search_url)

                # Ждем загрузки страницы
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.ID, "content"))
                )

                # Прокручиваем страницу до конца
                self.scroll_to_bottom(driver)

                # Ищем все ссылки на странице
                links = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.TAG_NAME, "a"))
                )
                channel_links = set()

                # Извлекаем ссылки на каналы
                for link in links:
                    try:
                        href = link.get_attribute("href")
                        if href and "@" in href:  # Ссылки на каналы содержат "@"
                            channel_links.add(href)
                            logger.info(f"Найден канал: {href}")
                    except Exception as e:
                        logger.error(f"Ошибка при обработке ссылки: {str(e)}")
                        continue

                return list(channel_links)  # Возвращаем список ссылок
            except Exception as e:
                logger.error(f"Попытка {attempt + 1} не удалась: {str(e)}")
                if attempt == max_retries - 1:
                    return []
                time.sleep(2)
                continue
            finally:
                if driver:
                    driver.quit()

        return []

    def search(self, query, max_results=10):
        """
        Основной метод для выполнения поиска.
        :param query: Поисковый запрос.
        :param max_results: Максимальное количество результатов.
        :return: Список новых каналов.
        """
        self.stats["total_queries"] += 1
        self.stats["last_search_time"] = time.strftime("%Y-%m-%d %H:%M:%S")

        # Получаем все каналы по запросу
        all_channels = self.get_channel_links(query)

        # Фильтруем уже найденные каналы
        new_channels = [channel for channel in all_channels if channel not in self.found_channels]

        # Обновляем список найденных каналов
        if new_channels:
            self.found_channels.update(new_channels)
            self.stats["total_channels_found"] += len(new_channels)

        # Сохраняем результаты в Excel
        self.save_results_to_excel(query, new_channels[:max_results])
        return new_channels[:max_results]

    def get_stats(self):
        """Возвращает статистику поиска."""
        return (
            f"Запросов: {self.stats['total_queries']}, "
            f"Каналов найдено: {self.stats['total_channels_found']}, "
            f"Последний поиск: {self.stats['last_search_time']}"
        )
