import json
import sys

from common_functions import write_log

from components.airmon import Airmon
from components import airodump


def load_configuration_parameters() -> tuple[str | None, str | None, str | None]:
    try:
        with open('configuration.json') as f:
            main_configuration: dict = json.load(f)

            return main_configuration.get('dictionary'), main_configuration.get('interface'), main_configuration.get('bssid')
    except FileNotFoundError:
        write_log('Configuration file not found')
        sys.exit(1)

    
if __name__ == '__main__':
    WIFI_CRACK_DICTIONARY, INTERFACE, BSSID = load_configuration_parameters()
    
    """Setting interface in monitor mode"""
    # airmon: Airmon = Airmon(INTERFACE)
    # airmon.start_airmon()

    airodump.execute(INTERFACE, BSSID)
    
