import concurrent.futures
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import logging

logger = logging.getLogger(__name__)

class YouTubeSearcher:
    def __init__(self):
        self.stats = {
            "total_queries": 0,
            "total_channels_found": 0,
            "last_search_time": None
        }
        self.found_channels_file = "found_channels.txt"
        self.found_channels = self._load_found_channels()

    def _load_found_channels(self):
        """Загрузка уже найденных каналов из файла"""
        if not os.path.exists(self.found_channels_file):
            return set()

        with open(self.found_channels_file, "r", encoding="utf-8") as file:
            return {line.strip() for line in file if line.strip()}

    def _save_found_channels(self, new_channels):
        """Сохранение новых каналов в файл"""
        with open(self.found_channels_file, "a", encoding="utf-8") as file:
            for channel in new_channels:
                file.write(f"{channel}\n")

    def setup_driver(self):
        """Настройка драйвера Chrome в headless режиме"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--log-level=3')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-notifications')

        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=chrome_options)

    def scroll_to_bottom(self, driver):
        """Скролл страницы до конца"""
        last_height = driver.execute_script("return document.documentElement.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.documentElement.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def get_channel_links(self, search_query, max_retries=3):
        """Поиск ссылок на каналы по запросу"""
        for attempt in range(max_retries):
            driver = None
            try:
                driver = self.setup_driver()
                search_url = f"https://www.youtube.com/results?search_query={search_query.replace(' ', '+')}&sp=EgQIBRAB"
                driver.get(search_url)

                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.ID, "content"))
                )

                self.scroll_to_bottom(driver)

                links = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.TAG_NAME, "a"))
                )
                channel_links = set()

                for link in links:
                    try:
                        href = link.get_attribute("href")
                        if href and "@" in href:
                            channel_links.add(href)
                            logger.info(f"Найден канал: {href}")
                    except Exception as e:
                        logger.error(f"Ошибка при обработке ссылки: {str(e)}")
                        continue

                return channel_links

            except Exception as e:
                logger.error(f"Попытка {attempt + 1} не удалась: {str(e)}")
                if attempt == max_retries - 1:
                    return set()
                time.sleep(2)
                continue
            finally:
                if driver:
                    driver.quit()

        return set()

    def search(self, query, max_results=10):
        """Основной метод поиска"""
        self.stats["total_queries"] += 1
        self.stats["last_search_time"] = time.strftime("%Y-%m-%d %H:%M:%S")

        # Получаем все каналы по запросу
        all_channels = self.get_channel_links(query)

        # Фильтруем уже найденные каналы
        new_channels = [channel for channel in all_channels if channel not in self.found_channels]

        # Обновляем список найденных каналов
        if new_channels:
            self._save_found_channels(new_channels)
            self.found_channels.update(new_channels)
            self.stats["total_channels_found"] += len(new_channels)

        return new_channels[:max_results]

    def get_stats(self):
        """Получение статистики поиска"""
        return (
            f"Запросов: {self.stats['total_queries']}, "
            f"Каналов найдено: {self.stats['total_channels_found']}, "
            f"Последний поиск: {self.stats['last_search_time']}"
        )
