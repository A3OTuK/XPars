import os
import sys
import logging
from datetime import datetime
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import threading
import queue
from urllib.parse import urlparse

# Настройка логирования
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('WDM').setLevel(logging.INFO)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class YouTubeSearcher:
    def __init__(self, result_callback=None, thread_count=3):
        self.stats = {
            "total_queries": 0,
            "total_channels_found": 0,
            "last_search_time": None
        }
        self.found_channels = set()
        self.channels_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.result_callback = result_callback
        self.thread_count = min(max(1, thread_count), 10)
        self.work_queue = queue.Queue()
        self._init_workspace()

        logger.info(f"Инициализирован YouTubeSearcher с {self.thread_count} потоками")

    def _init_workspace(self):
        """Создает необходимые директории для работы"""
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        self.results_dir = os.path.join(base_dir, "results")
        self.logs_dir = os.path.join(base_dir, "logs")
        os.makedirs(self.results_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)

    def setup_driver(self):
        """Настройка ChromeDriver с совместимостью для новых версий WDM"""
        try:
            chrome_options = Options()
            opts = [
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--log-level=3",
                "--disable-extensions",
                "--disable-notifications",
                "--mute-audio",
                "--window-size=1920,1080"
            ]

            for opt in opts:
                chrome_options.add_argument(opt)

            # Упрощенная инициализация ChromeDriverManager
            service = Service(
                ChromeDriverManager().install(),
                log_path=os.path.join(self.logs_dir, "chromedriver.log")
            )

            driver = webdriver.Chrome(
                service=service,
                options=chrome_options
            )

            driver.set_page_load_timeout(30)
            driver.implicitly_wait(5)

            return driver

        except Exception as e:
            logger.error(f"Ошибка инициализации ChromeDriver: {str(e)}")
            raise

    def get_channel_links(self, search_query, max_retries=3):
        """Поиск ссылок на YouTube каналы по запросу"""
        for attempt in range(max_retries):
            driver = None
            try:
                if self.stop_event.is_set():
                    return []

                logger.info(f"Поиск каналов (попытка {attempt + 1}): '{search_query}'")
                driver = self.setup_driver()

                search_url = f"https://www.youtube.com/results?search_query={search_query.replace(' ', '+')}&sp=EgIQAg%3D%3D"
                driver.get(search_url)

                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.ID, "content"))
                )

                self._scroll_to_bottom(driver)

                links = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a#video-title-link, a.yt-simple-endpoint"))
                )

                channel_links = set()
                for link in links:
                    if self.stop_event.is_set():
                        break
                    try:
                        href = link.get_attribute("href")
                        if href and ("/channel/" in href or "/user/" in href or "/@" in href):
                            normalized = self._normalize_channel_url(href)
                            if normalized:
                                channel_links.add(normalized)
                    except Exception as e:
                        logger.debug(f"Ошибка обработки ссылки: {str(e)}")

                logger.info(f"Найдено каналов: {len(channel_links)}")
                return list(channel_links)

            except Exception as e:
                logger.error(f"Ошибка поиска (попытка {attempt + 1}): {str(e)}")
                if attempt == max_retries - 1:
                    return []
                time.sleep(2)
                continue

            finally:
                if driver:
                    driver.quit()
        return []

    def continuous_search(self, query):
        """Непрерывный поиск YouTube каналов по заданному запросу"""
        try:
            while not self.stop_event.is_set():
                channel_links = self.get_channel_links(query)

                with self.channels_lock:
                    new_channels = [url for url in channel_links if url not in self.found_channels]
                    self.found_channels.update(new_channels)
                    self.stats["total_channels_found"] += len(new_channels)
                    self.stats["total_queries"] += 1
                    self.stats["last_search_time"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                for channel_url in new_channels:
                    if self.stop_event.is_set():
                        break

                    telegram_url = self._process_single_channel(channel_url)
                    if self.result_callback:
                        self.result_callback(channel_url, telegram_url)

                if not new_channels:
                    time.sleep(5)

        except Exception as e:
            logger.error(f"Ошибка в continuous_search: {str(e)}")

    def _process_single_channel(self, channel_url):
        """Обработка одного YouTube канала для поиска Telegram ссылки"""
        try:
            from TGPars import TelegramParser

            driver = self.setup_driver()
            parser = TelegramParser(driver)

            try:
                telegram_url = parser.parse_telegram_link(channel_url)
                logger.info(f"Обработан канал: {channel_url} -> {telegram_url or 'Not found'}")
                return telegram_url
            finally:
                driver.quit()

        except Exception as e:
            logger.error(f"Ошибка обработки канала {channel_url}: {str(e)}")
            return None

    def _normalize_channel_url(self, url):
        """Нормализация URL YouTube канала"""
        try:
            if "/@" in url:
                return url.split('?')[0]
            elif "/channel/" in url or "/user/" in url:
                parsed = urlparse(url)
                return f"{parsed.scheme}://{parsed.netloc}{parsed.path.split('/featured')[0].split('/videos')[0]}"
            return None
        except Exception as e:
            logger.debug(f"Ошибка нормализации URL: {str(e)}")
            return None

    def _scroll_to_bottom(self, driver):
        """Прокрутка страницы до конца для загрузки всех результатов"""
        last_height = driver.execute_script("return document.documentElement.scrollHeight")
        scroll_attempt = 0

        while not self.stop_event.is_set() and scroll_attempt < 3:
            driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(1.5)
            new_height = driver.execute_script("return document.documentElement.scrollHeight")

            if new_height == last_height:
                break

            last_height = new_height
            scroll_attempt += 1

    def stop(self):
        """Остановка всех операций поиска"""
        self.stop_event.set()
        logger.info("Поиск остановлен по команде пользователя")