import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QMessageBox
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings, QWebEnginePage
from PyQt6.QtCore import QUrl, QTimer

# --- Определяем директорию для данных (Application Support) ---
DATA_DIR = Path.home() / "Library" / "Application Support" / "Chess"
DATA_DIR.mkdir(parents=True, exist_ok=True)

class ChessAuthPage(QWebEnginePage):
    """Страница, разрешающая только chess.com и авторизацию OAuth"""
    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)
    
    def is_url_allowed(self, url_str):
        if url_str.startswith(("about:", "data:", "blob:")):
            return True
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url_str)
            hostname = parsed.hostname or ""
            path = parsed.path
            
            if hostname.endswith(".chess.com") or hostname == "chess.com":
                return True
            if hostname in ["accounts.google.com", "oauth2.googleapis.com"]:
                return True
            if hostname in ["www.facebook.com", "m.facebook.com", "facebook.com"]:
                if any(p in path for p in ["/login/", "/dialog/oauth", "/v2.0/dialog/oauth"]):
                    return True
                return False
            if hostname in ["appleid.apple.com", "idmsa.apple.com"]:
                if any(p in path for p in ["/auth/", "/appleauth/", "/sign-in"]):
                    return True
                if path.startswith("/auth") or "authorize" in path.lower():
                    return True
                return False
            return False
        except Exception:
            return False
    
    def acceptNavigationRequest(self, url, navigation_type, is_main_frame):
        url_str = url.toString()
        if not is_main_frame:
            return True
        if self.is_url_allowed(url_str):
            return True
        QMessageBox.warning(
            None,
            "Доступ запрещен",
            "Разрешены только:\n"
            "• Все поддомены chess.com\n"
            "• Авторизация через Google\n"
            "• Авторизация через Facebook (только OAuth)\n"
            "• Авторизация через Apple (только OAuth)"
        )
        self.runJavaScript("window.stop();", lambda: None)
        if not self.url().toString().endswith("chess.com"):
            self.setUrl(QUrl("https://www.chess.com"))
        return False

class ChessBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chess.com - Изолированный браузер")
        self.setGeometry(100, 100, 1400, 900)
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Создаем профиль с данными в DATA_DIR
        self.profile = QWebEngineProfile("chess_isolated_profile", self)
        self.profile.setPersistentStoragePath(str(DATA_DIR))
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
        
        self.web_view = QWebEngineView()
        self.page = ChessAuthPage(self.profile, self.web_view)
        self.web_view.setPage(self.page)
        
        # Настройки WebEngine
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        
        self.web_view.titleChanged.connect(self.update_title)
        self.web_view.loadFinished.connect(self.on_load_finished)
        
        layout.addWidget(self.web_view)
        self.web_view.setUrl(QUrl("https://www.chess.com"))
        
        # Таймер автосохранения (Qt WebEngine уже сохраняет cookies и localStorage)
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.autosave_data)
        self.autosave_timer.start(30000)
    
    def autosave_data(self):
        pass  # Qt WebEngine уже делает сохранение автоматически
    
    def update_title(self, title):
        current_url = self.web_view.url().toString()
        if self.page.is_url_allowed(current_url):
            self.setWindowTitle(f"{title} ✓")
        else:
            self.setWindowTitle(f"{title} ⚠ (Заблокировано)")
    
    def on_load_finished(self, success):
        if not success:
            current_url = self.web_view.url().toString()
            if not self.page.is_url_allowed(current_url):
                self.web_view.setUrl(QUrl("https://www.chess.com"))
    
    def closeEvent(self, event):
        self.autosave_timer.stop()
        self.web_view.stop()
        self.profile.clearHttpCache()
        QTimer.singleShot(100, lambda: None)
        print(f"Данные сохранены в {DATA_DIR}")
        event.accept()

if __name__ == "__main__":
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu-compositing --allow-running-insecure-content"
    app = QApplication(sys.argv)
    app.setApplicationName("Chess.com Изолированный")
    browser = ChessBrowser()
    browser.show()
    sys.exit(app.exec())
