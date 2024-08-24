import subprocess
import sys

from common_functions import write_log


def send_through_scp(scp_information: dict, file_name: str):
    if scp_information.get('user') and scp_information.get('host') and scp_information.get('path') and scp_information.get('key_path'):
        user = scp_information.get('user')
        host = scp_information.get('host')
        path = scp_information.get('path')
        key_path = scp_information.get('key_path')
        
        command = f'scp -i {key_path} src/files/{file_name}.hc22000 {user}@{host}:{path}'
        output = subprocess.run(command, shell=True, capture_output=True, text=True)
        if output.stderr:
            write_log(f'[!] Error transfering over scp {file_name}.hc22000')
            sys.exit(1)
        
        write_log(f'[+] {file_name} sent through SCP')
        
    else:
        write_log("[!] You must specify fields 'user' and 'host' to use scp")