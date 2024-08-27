import datetime
import json

def write_log(description: str) -> None:
    """Write logs in file wifi-pwned.log

    Args:
        description (str): message to write.
    """
    
    with open('wifi-pwned.log', 'a') as f:
        now: str = datetime.datetime.strftime(datetime.datetime.now(), '%d/%m/%Y %H:%M:%S')
        f.write(f'{now} {description}\n')


def get_config_field(field: str):
    """Get the a field from 'configuration.json' file.

    Args:
        field (str): key to search.

    Returns:
        str | dict: returns the value of the key(field).
    """
    
    with open('src/configuration.json') as f:
        config_fields: dict = json.load(f)
        return config_fields.get(field)