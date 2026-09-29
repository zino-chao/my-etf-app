import requests
import json

class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def send_message(self, text: str, web_app_url: str = None):
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        if web_app_url:
            reply_markup = {
                "inline_keyboard": [[{"text": "📱 開啟資產儀表板", "url": web_app_url}]]
            }
            payload["reply_markup"] = json.dumps(reply_markup)

        resp = requests.post(self.api_url, data=payload)
        return resp.json()
