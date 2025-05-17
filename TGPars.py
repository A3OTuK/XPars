import re
from urllib.parse import urlparse, parse_qs, unquote
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging

class TelegramParser:
    def __init__(self, driver):
        self.driver = driver
        self.timeout = 15  # Максимальное время ожидания элементов
        self.logger = logging.getLogger(__name__)

        # Паттерны для поиска Telegram ссылок
        self.patterns = [
            r'(https?://t\.me/[a-zA-Z0-9_\-]+)',  # Стандартные ссылки
            r'(https?://telegram\.me/[a-zA-Z0-9_\-]+)',
            r'@([a-zA-Z0-9_\-]{5,32})',  # Username
            r't\.me/([a-zA-Z0-9_\-]{5,32})',
            r'telegram\.me/([a-zA-Z0-9_\-]{5,32})'
        ]

    def parse_telegram_link(self, channel_url):
        self.logger.info(f"Начинаем парсинг канала: {channel_url}")

        # Вариант 1: Проверка редиректов
        tg_link = self._find_telegram_link_via_redirect(channel_url)
        if tg_link:
            return tg_link

        # Вариант 2: Раздел "О канале"
        tg_link = self._find_telegram_link_via_about_section(channel_url)
        if tg_link:
            return tg_link

        # Вариант 3: Основное описание
        tg_link = self._find_telegram_link_via_channel_description(channel_url)
        if tg_link:
            return tg_link

        self.logger.warning("Telegram ссылка не найдена")
        return None

    def _find_telegram_link_via_redirect(self, channel_url):
        try:
            self.driver.get(channel_url)
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )

            redirect_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/redirect"]')
            for link in redirect_links:
                href = link.get_attribute('href')
                if 'youtube.com/redirect' in href:
                    parsed = urlparse(href)
                    params = parse_qs(parsed.query)
                    if 'q' in params:
                        decoded = unquote(params['q'][0])
                        if any(x in decoded for x in ['t.me/', 'telegram.me/']):
                            self.logger.info(f"Найдена ссылка в редиректе: {decoded}")
                            return self._normalize_link(decoded)
        except TimeoutException:
            self.logger.debug("Редирект-ссылки не найдены")
        return None

    def _find_telegram_link_via_about_section(self, channel_url):
        try:
            about_url = channel_url.rstrip('/') + '/about'
            self.driver.get(about_url)
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )

            self._click_show_more()

            links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href]')
            for link in links:
                href = link.get_attribute('href')
                if href and any(x in href for x in ['t.me/', 'telegram.me/']):
                    self.logger.info(f"Найдена ссылка в 'О канале': {href}")
                    return self._normalize_link(href)
        except Exception as e:
            self.logger.debug(f"Ошибка парсинга 'О канале': {str(e)}")
        return None

    def _find_telegram_link_via_channel_description(self, channel_url):
        try:
            self.driver.get(channel_url)
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )

            self._click_show_more()

            try:
                description = self.driver.find_element(By.CSS_SELECTOR, '#description')
                desc_text = description.text
            except NoSuchElementException:
                description = self.driver.find_element(By.CSS_SELECTOR, 'yt-formatted-string.description')
                desc_text = description.text

            for pattern in self.patterns:
                match = re.search(pattern, desc_text)
                if match:
                    link = match.group(1)
                    normalized = self._normalize_link(link)
                    self.logger.info(f"Найдена ссылка в описании: {normalized}")
                    return normalized
        except Exception as e:
            self.logger.debug(f"Ошибка парсинга описания: {str(e)}")
        return None

    def _click_show_more(self):
        try:
            show_more = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button#expand, paper-button#more'))
            )
            show_more.click()
            time.sleep(1)
        except TimeoutException:
            pass

    def _normalize_link(self, link):
        if not link.startswith('http'):
            if link.startswith('@'):
                link = f"https://t.me/{link[1:]}"
            else:
                link = f"https://t.me/{link}"
        return link.split('?')[0].rstrip('/')
