import subprocess

from common_functions import write_log

class Aircrack:
    """Class for aircrack-ng methods"""

    def exec(self, args: list):
        aircrack_arguments = ' '.join(args)
        command = f'aircrack-ng {aircrack_arguments}'
        output = subprocess.run(command, shell=True, capture_output=True, text=True)
        return output
        
    def check_captured_handshake(self, file_name: str):
        args = [f'src/files/{file_name}-01.cap']
        output = self.exec(args)
        return '1 handshake' in output.stdout