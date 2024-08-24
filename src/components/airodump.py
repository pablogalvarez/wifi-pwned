import subprocess
import time
import csv
import sys

from common_functions import write_log, get_config_field

from .aircrack import Aircrack

class Airodump:
    """Class for airodump-ng methods"""

    def get_str_shell_command(self, monitor_interface: str, args: list):
        airodump_arguments = ' '.join(args)
        return f'airodump-ng {airodump_arguments} {monitor_interface}'
    
    
    def capture_available_networks(self, monitor_interface: str, time_capturing: int = 120):
        networks_file_name = 'networks'
        command = f'airodump-ng --output-format csv -w src/files/{networks_file_name} {monitor_interface}'
        try:
            subprocess.run(command, shell=True, text=True, capture_output=True, timeout=time_capturing)
        except Exception:
            write_log('[+] Reachable networks captured')
            
        return networks_file_name

            
    def capture_handshake(self, monitor_interface: str, network_ssid: str, captured_networks_file_name: str):
        network_bssid = self.get_network_field_from_csv(network_ssid, 'bssid', captured_networks_file_name)
        network_channel = self.get_network_field_from_csv(network_ssid, 'channel', captured_networks_file_name)
        
        if not network_bssid or not network_channel:
            write_log(f'[!] Network with SSID {network_ssid} not found')
            sys.exit(1)
            
        captured_handshake_file_name = f'{network_ssid}-handshake'
        
        command = ['airodump-ng', '-c', network_channel, '--bssid', network_bssid, '-w', f'src/files/{captured_handshake_file_name}', '--output-format', 'pcap', monitor_interface]
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        aircrack: Aircrack = Aircrack()
        handshake_captured = False
        while not handshake_captured:
            handshake_captured = aircrack.check_captured_handshake(captured_handshake_file_name)
            time.sleep(15)
            
        process.terminate()
        try:
            process.wait(10)
        except Exception:
            process.kill()
            
        write_log(f'[+] Handshake for network {network_ssid} captured')
        
        return captured_handshake_file_name


    def get_network_field_from_csv(self, network_name: str, field: str, file_name: str):
        try:
            fields = {
                'bssid': 0,
                'channel': 3
            }
            with open(f'src/files/{file_name}-01.csv', newline='') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and len(row) >= 13 and row[13].strip() == network_name:  # row[13] -> ESSID
                        return row[fields.get(field)].strip()
            
            return None
        
        except FileNotFoundError:
            write_log(f'[!] File with name {file_name} not found as an airodump-ng output file')
            return None
        