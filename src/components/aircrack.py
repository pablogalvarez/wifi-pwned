import subprocess

from common_functions import write_log

class Aircrack:
    """Class for aircrack-ng methods"""

    def exec(self, args: list):
        """Execute the aircrack command with the arguments passed through parameters.

        Args:
            args (list): arguments for aircrack-ng.

        Returns:
            str: output of aircrack-ng command.
        """
        
        aircrack_arguments = ' '.join(args)
        command = f'aircrack-ng {aircrack_arguments}'
        output = subprocess.run(command, shell=True, capture_output=True, text=True)
        return output
        
    def check_captured_handshake(self, file_name: str):
        """Check if a handshake has been captured.

        Args:
            file_name (str): file name where the handshake will be written.

        Returns:
            boolean: returns True if handshake was captured, otherwise False.
        """
        
        args = [f'src/files/{file_name}-01.cap']
        output = self.exec(args)
        return '1 handshake' in output.stdout