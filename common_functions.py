import datetime

def write_log(description: str) -> None:
    with open('wifi-pwned.log', 'a') as f:
        now: str = datetime.datetime.strftime(datetime.datetime.now(), '%d/%m/%Y %H:%i')
        f.write(f'{now} {description}\n')