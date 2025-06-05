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
import threading
import queue

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class YouTubeSearcher:
    def __init__(self, result_callback=None, thread_count=3):
        """
        Инициализация поисковика

        :param result_callback: функция для обработки результатов (youtube_url, telegram_url)
        :param thread_count: количество рабочих потоков
        """
        self.stats = {
            "total_queries": 0,
            "total_channels_found": 0,
            "last_search_time": None
        }
        self.found_channels = set()
        self.channels_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.result_callback = result_callback
        self.thread_count = thread_count
        self.work_queue = queue.Queue()
        self._init_workspace()

    def _init_workspace(self):
        """Инициализация рабочей директории"""
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        self.results_dir = os.path.join(base_dir, "results")
        os.makedirs(self.results_dir, exist_ok=True)

    def get_stats(self):
        """Возвращает статистику поиска"""
        return (
            f"Запросов: {self.stats['total_queries']}, "
            f"Каналов найдено: {self.stats['total_channels_found']}, "
            f"Последний поиск: {self.stats['last_search_time']}"
        )

    def continuous_search(self, query):
        """
        Непрерывный поиск каналов с немедленной обработкой

        :param query: поисковый запрос
        """
        logger.info(f"Начало непрерывного поиска по запросу: {query}")

        with self.channels_lock:
            self.stats["total_queries"] += 1
            self.stats["last_search_time"] = time.strftime("%Y-%m-%d %H:%M:%S")

        while not self.stop_event.is_set():
            try:
                # Получаем новые каналы
                channels = self.get_channel_links(query)
                if not channels or self.stop_event.is_set():
                    time.sleep(5)  # Пауза перед следующей попыткой
                    continue

                # Добавляем в очередь только новые каналы
                new_channels = []
                with self.channels_lock:
                    new_channels = [c for c in channels if c not in self.found_channels]
                    if new_channels:
                        self.found_channels.update(new_channels)
                        self.stats["total_channels_found"] += len(new_channels)

                # Добавляем в очередь на обработку
                for channel in new_channels:
                    if self.stop_event.is_set():
                        break
                    self.work_queue.put(channel)

                # Запускаем потоки обработки
                self._start_processing_threads()

                # Небольшая пауза перед следующим поиском
                time.sleep(10)

            except Exception as e:
                logger.error(f"Ошибка в continuous_search: {str(e)}")
                if not self.stop_event.is_set():
                    time.sleep(30)  # Длинная пауза при ошибке

    def _start_processing_threads(self):
        """Запускает потоки для обработки каналов"""
        threads = []
        for _ in range(min(self.thread_count, self.work_queue.qsize())):
            t = threading.Thread(
                target=self._process_channels_worker,
                daemon=True
            )
            t.start()
            threads.append(t)

        # Ожидаем завершения всех потоков
        for t in threads:
            t.join()

    def _process_channels_worker(self):
        """Рабочая функция для потоков обработки"""
        while not self.stop_event.is_set():
            try:
                channel_url = self.work_queue.get_nowait()
                self._process_single_channel(channel_url)
                self.work_queue.task_done()
            except queue.Empty:
                break

    def _process_single_channel(self, channel_url):
        """Обработка одного канала"""
        try:
            # Парсим Telegram ссылку
            driver = self.setup_driver()
            try:
                from TGPars import TelegramParser
                parser = TelegramParser(driver)
                tg_link = parser.parse_telegram_link(channel_url)

                # Вызываем callback если он есть
                if self.result_callback:
                    self.result_callback(channel_url, tg_link)

                # Логируем результат
                logger.info(f"Обработан канал: {channel_url}")
                if tg_link:
                    logger.info(f"Найдена Telegram ссылка: {tg_link}")

            finally:
                driver.quit()

        except Exception as e:
            logger.error(f"Ошибка обработки канала {channel_url}: {str(e)}")

    def get_channel_links(self, search_query, max_retries=3):
        """
        Поиск каналов YouTube по запросу

        :param search_query: поисковый запрос
        :param max_retries: максимальное количество попыток
        :return: список найденных каналов
        """
        for attempt in range(max_retries):
            driver = None
            try:
                if self.stop_event.is_set():
                    return []

                driver = self.setup_driver()
                search_url = f"https://www.youtube.com/results?search_query={search_query.replace(' ', '+')}=&sp=EgIQAg%253D%253D"
                driver.get(search_url)

                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.ID, "content"))
                )

                self._scroll_to_bottom(driver)

                links = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.TAG_NAME, "a"))
                )
                channel_links = set()

                for link in links:
                    if self.stop_event.is_set():
                        break

                    try:
                        href = link.get_attribute("href")
                        if href and ("/channel/" in href or "/user/" in href or "/@" in href):
                            # Нормализуем URL канала
                            if "/@" in href:
                                channel_links.add(href.split('?')[0])
                            elif "/channel/" in href or "/user/" in href:
                                base_url = href.split('/featured')[0].split('/videos')[0]
                                channel_links.add(base_url)
                    except Exception as e:
                        logger.debug(f"Ошибка обработки ссылки: {str(e)}")
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

    def _scroll_to_bottom(self, driver):
        """Прокрутка страницы до конца"""
        last_height = driver.execute_script("return document.documentElement.scrollHeight")
        while not self.stop_event.is_set():
            driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.documentElement.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def setup_driver(self):
        """Настройка и создание Chrome драйвера"""
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

    def stop(self):
        """Остановка всех операций поиска"""
        self.stop_event.set()
        logger.info("Получена команда остановки поиска")