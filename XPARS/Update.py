import requests
import webbrowser
from tkinter import messagebox
import logging
from packaging import version

class Updater:
    def __init__(self, current_version="0.3"):
        self.current_version = current_version
        self.github_repo = "A3OTuK/XPars"  # Ваш репозиторий
        self.latest_version = None
        self.update_url = None
        self.logger = logging.getLogger(__name__)

    def check_for_updates(self):
        """Проверка обновлений с обработкой ошибок"""
        try:
            response = requests.get(
                f"https://api.github.com/repos/{self.github_repo}/releases/latest",
                timeout=10
            )

            if response.status_code == 404:
                return False, "Репозиторий не найден. Проверьте настройки обновлений"
            response.raise_for_status()

            release_data = response.json()
            self.latest_version = release_data['tag_name']
            self.update_url = release_data['html_url']

            if version.parse(self.latest_version) > version.parse(self.current_version):
                return True, f"Доступна новая версия {self.latest_version}"
            return False, f"У вас актуальная версия {self.current_version}"

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ошибка сети: {str(e)}")
            return False, "Ошибка подключения к GitHub"
        except Exception as e:
            self.logger.error(f"Неизвестная ошибка: {str(e)}")
            return False, "Ошибка при проверке обновлений"

    def show_update_dialog(self, parent):
        """Показать диалог обновления"""
        has_update, msg = self.check_for_updates()

        if has_update:
            if messagebox.askyesno(
                    "Доступно обновление",
                    f"{msg}\nХотите перейти на страницу загрузки?",
                    parent=parent
            ):
                webbrowser.open(self.update_url)
        else:
            messagebox.showinfo("Проверка обновлений", msg, parent=parent)