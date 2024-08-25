import subprocess
import sys

from common_functions import get_config_field, write_log

class Airmon:
    """Class for airmon methods"""

    def start(self, interface: str, channel: str | None = None, frequency: int | None = None) -> str:
        """Method to execute airmon-ng start

        It is important to know it is not possible to use channel and frequency at the same time.

        Args:
            interface (str): network interface
            channel (str): especify a channel
            frequency (str): specify a frequency in MHz

        Returns:
            this function returns a string containing the new monitor mode interface
        """
        if channel and frequency:
            write_log('ERROR. No se pueden especificar los parametros "channel" y "frequency" a la vez en Airmon.start()')
            sys.exit(1)

        elif channel:
            command = f'airmon-ng start {interface} {channel}'

        elif frequency:
            command = f'airmon-ng start {interface} {frequency}'

        else:
            command = f'airmon-ng start {interface}'

        run = subprocess.run(command, shell=True, capture_output=True, text=True)
        if run.stderr:
            write_log(f'ERROR. Ha fallado al ejecutar el comando "{command}"')
            return ''
        else:
            write_log(f'Interfaz de red "{interface}" configurada en modo monitor')
            return f'{interface}mon'

    
    def stop(self, interface: str):
        """Method to execute airmon-ng stop
        
        Args:
            interface (str): network interface

        """
        command = f'airmon-ng stop {interface}'
        run = subprocess.run(command, shell=True, capture_output=True, text=True)
        if run.stderr:
            write_log(f'ERROR. Ha fallado al ejecutar el comando "{command}"')
        else:
            write_log(f'Interfaz de red "{interface}" quitada del modo monitor')

    
    def check(self, kill: bool = False):
        """Method to execute airmon-ng check
        
        Args:
            kill (bool): if kill is set to True, command executed will be airmon-ng check kill

        """
        if kill:
            command = 'airmon-ng check kill'
        else:
            command = 'airmon-ng check'
        
        run = subprocess.run(command, shell=True, capture_output=True, text=True)
        if run.stderr:
            write_log(f'ERROR. Ha fallado al ejecutar el comando "{command}"')
        else:
            write_log(f'Preparacion para poner la interfaz de red en modo monitor hecha con exito')
            
    
    def start_monitor_mode(self):
        interface: str = get_config_field('interface')
        self.check(kill=True)
        monitor_interface: str = self.start(interface)
        
        if not monitor_interface:
            write_log(f'[!] Something went wrong setting interface {interface} in monitor mode')
            sys.exit(1)
        
        return monitor_interface
    
    def stop_monitor_mode(self, monitor_interface: str):
        self.stop(monitor_interface)
        
