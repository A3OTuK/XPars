import os
import sys
import logging
import pandas as pd
from datetime import datetime
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from TGPars import TelegramParser

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class YouTubeSearcher:
    def __init__(self):
        # Инициализация stats ДО всех других атрибутов
        self.stats = {
            "total_queries": 0,
            "total_channels_found": 0,
            "last_search_time": None
        }

        # Остальная инициализация
        self.found_channels = set()
        self._init_workspace()

    def _init_workspace(self):
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        self.results_dir = os.path.join(base_dir, "results")
        os.makedirs(self.results_dir, exist_ok=True)

    def get_stats(self):
        return (
            f"Запросов: {self.stats['total_queries']}, "
            f"Каналов найдено: {self.stats['total_channels_found']}, "
            f"Последний поиск: {self.stats['last_search_time']}"
        )

    def save_results_to_excel(self, query, urls):
        try:
            if not urls:
                return None

            filename = f"{query[:30]}_{datetime.now().strftime('%Y%m%d')}.xlsx"
            file_path = os.path.join(self.results_dir, filename)

            data = [{"YouTube": url, "Telegram": "Not parsed yet"} for url in urls]
            df = pd.DataFrame(data)

            df.to_excel(file_path, index=False, engine='openpyxl')

            return file_path

        except Exception as e:
            logging.error(f"Ошибка сохранения: {str(e)}")
            return None

    def parse_telegram_links(self, file_path):
        try:
            driver = self.setup_driver()
            parser = TelegramParser(driver)

            df = pd.read_excel(file_path)
            for index, row in df.iterrows():
                if pd.isna(row['Telegram']) or row['Telegram'] == 'Not parsed yet':
                    tg_link = parser.parse_telegram_link(row['YouTube'])
                    df.at[index, 'Telegram'] = tg_link if tg_link else 'Not found'

            df.to_excel(file_path, index=False, engine='openpyxl')
        finally:
            driver.quit()

    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--mute-audio")

        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=chrome_options)

    def scroll_to_bottom(self, driver):
        last_height = driver.execute_script("return document.documentElement.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.documentElement.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def get_channel_links(self, search_query, max_retries=3):
        for attempt in range(max_retries):
            driver = None
            try:
                driver = self.setup_driver()
                search_url = f"https://www.youtube.com/results?search_query={search_query.replace(' ', '+')}=&sp=EgQIBRAB"
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

                return list(channel_links)
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
        self.stats["total_queries"] += 1
        self.stats["last_search_time"] = time.strftime("%Y-%m-%d %H:%M:%S")

        all_channels = self.get_channel_links(query)

        new_channels = [channel for channel in all_channels if channel not in self.found_channels]

        if new_channels:
            self.found_channels.update(new_channels)
            self.stats["total_channels_found"] += len(new_channels)

        file_path = self.save_results_to_excel(query, new_channels[:max_results])

        if file_path:
            self.parse_telegram_links(file_path)

        return new_channels[:max_results]
