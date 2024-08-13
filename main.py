import json
import sys

from common_functions import get_config_field, write_log

from components.airmon import Airmon
from components.airodump import Airodump

from csv_functions import get_required_network_information


SUCCESSFULL_PREFIX = '[+]'
ERROR_PREFIX = '[!]'


def check_config_file():
    try:
        with open('configuration.json') as f:
            configuration_fields = json.load(f)
            mandatory_fields = ['interface']
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

    # airmon: Airmon = Airmon()
    # airmon.check(kill=True)
    # monitor_interface: str = airmon.start(interface)
    monitor_interface = 'wlan0mon'

    # Capturing packets with airodump-ng
    airodump: Airodump = Airodump()

    # Exporting csv file to get all networks
    output_file_name = 'networks'
    args = ['--output-format csv', f'-w {output_file_name}']
    airodump.exec(monitor_interface, args)

    # Once airodump has stored all networks, I get the network bssid and its channel
    network_ssid = get_config_field('ssid')
    bssid, channel = get_required_network_information(output_file_name, network_ssid)
    if not bssid or not channel:
        write_log(f'[!] Network with SSID {network_ssid} not found')
    

