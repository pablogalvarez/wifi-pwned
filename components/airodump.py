import subprocess

from common_functions import write_log

class Airodump:
    """Class for airodump-ng methods"""

    def exec(self, monitor_interface: str, args: list):
        airodump_arguments = ' '.join(args)
        command = f'airodump-ng {airodump_arguments} {monitor_interface}'
        try:
            # Run airodump during 2 minutes to get all networks
            subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        except Exception:
            write_log('[+] Networks captured correctly')
            
    def get_str_shell_command(self, monitor_interface: str, args: list):
        airodump_arguments = ' '.join(args)
        return f'airodump-ng {airodump_arguments} {monitor_interface}'