import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from urllib.parse import unquote, urlparse, parse_qs
import time
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class TelegramParser:
    def __init__(self):
        """Инициализация парсера."""
        self.driver = self.setup_driver()

    def setup_driver(self):
        """Настраивает и возвращает драйвер Chrome в headless режиме."""
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--mute-audio")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-notifications")
        return webdriver.Chrome(options=chrome_options)

    def parse_telegram_link(self, channel_url):
        """Парсит Telegram-ссылку из описания YouTube-канала."""
        try:
            self.driver.get(channel_url)
            time.sleep(2)  # Ждем загрузки страницы

            # Переход на вкладку "О канале"
            try:
                about_button = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//*[contains(text(), "О канале") or contains(text(), "About")]'))
                )
                about_button.click()
                time.sleep(1)
            except (NoSuchElementException, TimeoutException):
                pass

            # Поиск ссылок через редирект YouTube
            try:
                links = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a[href*="redirect"]'))
                )
                for link in links:
                    href = link.get_attribute("href")
                    if "youtube.com/redirect" in href:
                        parsed_url = urlparse(href)
                        query_params = parse_qs(parsed_url.query)
                        if "q" in query_params:
                            decoded_url = unquote(query_params["q"][0])
                            if "t.me" in decoded_url or "telegram.me" in decoded_url:
                                return decoded_url
            except TimeoutException:
                pass

            # Поиск ссылок в описании канала
            try:
                description = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '#description, .description'))
                )
                matches = re.finditer(r'(?:@|t\.me\/)([a-zA-Z0-9_]{5,})', description.text)
                for m in matches:
                    return f"https://t.me/{m.group(1)}"
            except TimeoutException:
                pass

            return None
        except Exception as e:
            logger.error(f"Ошибка при обработке {channel_url}: {str(e)}")
            return None

    def close(self):
        """Закрывает драйвер."""
        self.driver.quit()