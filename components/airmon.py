import subprocess
import sys

from common_functions import write_log

class Airmon:
    """Class for airmon methods"""

    def __init__(self, interface: str | None):
        if interface:
            self.interface = interface
        else:
            command = "airmon-ng | awk '{print $2}' | sed '1,3d'"
            run = subprocess.run(command, shell=True, capture_output=True, text=True)
            if not run.stderr and run.stdout:
                self.interface = run.stdout.strip()
            else:
                write_log('Error setting a network interface. Check network interfaces with "ip link show"')
                sys.exit(1)

    
    def start_airmon(self):
        command = f"airmon-ng check kill && airmon-ng start {self.interface}"
        run = subprocess.run(command, shell=True, capture_output=True, text=True)
        if not run.stderr and run.stdout:
            write_log('Network interface set in monitor mode')
        else:
            write_log('Error setting network interface in monitor mode')
            sys.exit(1)
