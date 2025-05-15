from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import os
import time


class YouTubeSearcher:
    def __init__(self):
        self.driver = None
        self.processed_urls = set()
        self._init_driver()
        self._load_processed_urls()

    def _init_driver(self):
        """Инициализация Chrome в headless-режиме"""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        self.driver = webdriver.Chrome(service=Service('chromedriver.exe'), options=options)

    def _load_processed_urls(self):
        """Загрузка обработанных URL из текстового файла"""
        if os.path.exists('processed_urls.txt'):
            with open('processed_urls.txt', 'r') as f:
                self.processed_urls = set(line.strip() for line in f if line.strip())

    def _save_urls(self, new_urls):
        """Добавление новых URL в файл"""
        with open('processed_urls.txt', 'a') as f:
            for url in new_urls:
                f.write(f"{url}\n")

    def _scroll_page(self, scroll_times=3):
        """Прокрутка страницы для загрузки контента"""
        for _ in range(scroll_times):
            self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(1.5)

    def search(self, query, max_results=10):
        """
        Поиск новых YouTube-каналов
        Возвращает список новых URL
        """
        try:
            # Формируем URL поиска с фильтром по каналам
            search_url = f"https://www.youtube.com/results?search_query={query}&sp=EgIQAg%253D%253D"
            self.driver.get(search_url)

            # Ожидаем загрузки результатов
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-channel-renderer"))
            )

            # Прокручиваем для загрузки больше результатов
            self._scroll_page()

            # Собираем все ссылки на каналы
            new_urls = []
            channels = self.driver.find_elements(By.CSS_SELECTOR, "ytd-channel-renderer")[:max_results]

            for channel in channels:
                try:
                    url = channel.find_element(By.CSS_SELECTOR, "a.yt-simple-endpoint").get_attribute("href")
                    if url and url not in self.processed_urls:
                        new_urls.append(url)
                        self.processed_urls.add(url)
                except:
                    continue

            # Сохраняем новые URL
            if new_urls:
                self._save_urls(new_urls)
                self._save_search_log(query, len(new_urls))

            return new_urls

        except Exception as e:
            print(f"Ошибка при поиске: {str(e)}")
            return []
        finally:
            if self.driver:
                self.driver.quit()

    def _save_search_log(self, query, found_count):
        """Логгирование поисковых запросов"""
        log_entry = f"{datetime.now().strftime('%Y-%m-%d %H:%M')} | Запрос: '{query}' | Найдено: {found_count}\n"
        with open('search_log.txt', 'a', encoding='utf-8') as f:
            f.write(log_entry)

    def get_stats(self):
        """Простая статистика"""
        total = len(self.processed_urls)
        today = datetime.now().strftime('%Y-%m-%d')
        today_count = sum(1 for _ in open('processed_urls.txt') if today in _) if os.path.exists(
            'processed_urls.txt') else 0
        return f"Всего URL: {total} | Сегодня: {today_count}"