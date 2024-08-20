import datetime
import json

def write_log(description: str) -> None:
    with open('wifi-pwned.log', 'a') as f:
        now: str = datetime.datetime.strftime(datetime.datetime.now(), '%d/%m/%Y %H:%M:%S')
        f.write(f'{now} {description}\n')


def get_config_field(field: str) -> str:
    with open('configuration.json') as f:
        config_fields = json.load(f)
        return config_fields.get(field)