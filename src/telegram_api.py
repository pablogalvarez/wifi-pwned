import requests

from common_functions import get_config_field


class TelegramBot:
    
    def __init__(self, api_token: str):
        self.base_url = f'https://api.telegram.org/bot{api_token}'
        
        # Getting chat id
        url = f'{self.base_url}/getUpdates'
        response = requests.get(url)
        if response.status_code == 200:
            response_data: list = response.json().get('result')
            if len(response_data) > 0:
                first_message = response_data[0]
                if 'message' in first_message and 'chat' in first_message.get('message') and 'id' in first_message.get('message').get('chat'):
                    self.chat_id = first_message.get('message').get('chat').get('id')
                
        
    def send_message(self, message: str):
        url = f'{self.base_url}/sendMessage'
        data = {
            'chat_id': self.chat_id,
            'text': message
        }
        requests.post(url, data=data)