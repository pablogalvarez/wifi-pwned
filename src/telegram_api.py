import requests


class TelegramBot:
    
    def __init__(self, api_token: str, chat_id: str):
        self.base_url = f'https://api.telegram.org/bot{api_token}'
        self.chat_id = chat_id
                
        
    def send_message(self, message: str):
        url = f'{self.base_url}/sendMessage'
        data = {
            'chat_id': self.chat_id,
            'text': message
        }
        requests.post(url, data=data)