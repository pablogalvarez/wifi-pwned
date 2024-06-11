import json
import sys

from common_functions import get_config_field, write_log

from components.airmon import Airmon


SUCCESSFULL_PREFIX = '[+]'
ERROR_PREFIX = '[!]'


def check_config_file():
    try:
        with open('configuration.json') as f:
            configuration_fields = json.load(f)
            mandatory_fields = ['interface', 'ssid']
            abort_program = False
            for field in mandatory_fields:
                if not field in configuration_fields:
                    write_log(f'{ERROR_PREFIX} Configuration file "configuration.json" is uncomplete. Field "{field}" not found')
                    abort_program = True
            if abort_program:
                sys.exit(1)
            
    except FileNotFoundError:
        write_log(f'{ERROR_PREFIX} Configuration file "configuration.json" does not exists')
        sys.exit(1)


if __name__ == '__main__':
    # Check if configuration file exists and it has every mandatory key
    check_config_file()
    
    # Setting interface in monitor mode
    interface = get_config_field('interface')

    airmon: Airmon = Airmon()
    airmon.check(kill=True)
    airmon.start(interface)