import json
import sys

from common_functions import write_log

from components.airmon import Airmon


def load_configuration_parameters() -> tuple[str | None, str | None, str | None]:
    with open('configuration.json') as f:
        main_configuration: dict = json.load(f)

        dictionary: str = ''
        interface: str | None = None
        bssid: str | None = None
        if 'dictionary' in main_configuration and main_configuration['dictionary']:
            dictionary = main_configuration['dictionary']
        else:
            write_log('Dictionary for cracking passphrase not specified in configuration')
            sys.exit(1)


        if 'interface' in main_configuration and main_configuration['interface']:
            interface = main_configuration['interface']

        if 'bssid' in main_configuration and main_configuration['bssid']:
            bssid = main_configuration['bssid']

        return dictionary, interface, bssid

    
if __name__ == '__main__':
    WIFI_CRACK_DICTIONARY, INTERFACE, BSSID = load_configuration_parameters()
    
    """Setting interface in monitor mode"""
    airmon: Airmon = Airmon(INTERFACE)
    airmon.start_airmon()
    
