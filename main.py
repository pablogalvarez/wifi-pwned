import json

from common_functions import write_log

WIFI_CRACK_DICTIONARY: str = ''
INTERFACE: str | None = None
SSID: str | None = None


with open('configuration.json') as f:
    main_configuration: dict = json.load(f)
    try:
        if 'dictionary' in main_configuration and main_configuration['dictionary']:
            WIFI_CRACK_DICTIONARY = main_configuration['dictionary']
        else:
            raise SystemExit
    except SystemExit:
        write_log('Dictionary for cracking passphrase not specified in configuration')


    if 'interface' in main_configuration and main_configuration['interface']:
        INTERFACE = main_configuration['interface']
    
