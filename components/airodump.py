import subprocess
import threading

from common_functions import write_log

class Airodump:
    """Class for airodump-ng methods"""

    def exec(self, monitor_interface: str, args: list):
        airodump_arguments = ' '.join(args)
        command = f'airodump-ng {airodump_arguments} {monitor_interface}'
        try:
            subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        except Exception:
            print('Terminada captura de paquetes')