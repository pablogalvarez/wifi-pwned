import subprocess
from time import sleep

from common_functions import write_log

def execute(interface: str, bssid: str) -> None:
    monitor_interface = f'{interface}mon'
    
    command = 'ip link show'
    run = subprocess.run(command, shell=True, capture_output=True, text=True)
    if not run.stderr and run.stdout:
        if monitor_interface in run.stdout:
            command = f'airodump-ng {monitor_interface} -w APs --output-format csv'
            run = subprocess.run(command, shell=True, capture_output=True, text=True)
        else:
            write_log(f'Monitor interface with {interface} as source has not been created')
    else:
        write_log(f'Error executing "{command}"')