import json
import sys

from common_functions import write_log

from components.airmon import Airmon

if __name__ == '__main__':
    
    """Setting interface in monitor mode"""
    try:
        with open('configuration.json') as f:
            configuration_params: dict = json.load(f)
            interface = configuration_params.get('interface')

    except FileNotFoundError:
        write_log('Fichero de configuracion no encontrado "configuration.json"')
        sys.exit(1)

    airmon: Airmon = Airmon()
    airmon.check(kill=True)
    airmon.start(interface)