import subprocess
import sys

from common_functions import write_log


def send_through_scp(scp_information: dict, file_name: str):
    """This functions send the handshake file through scp. The configured server information must be specified in 'configuration.json' file. The following fields 
    are mandatory:
        - user: indicates the remote user
        - host: indicates the remote host
        - path: indicates the remote path where the file will be placed.
        - key_path: this field is very important to establish the connection. You have to specify the path where the private key (previosly generated and 
        configured in remote host) to connect to the remote host is placed.

    Args:
        scp_information (dict): dictionary which contains the necessary information.
        file_name (str): the readable hashcat file name
    """
    
    if scp_information.get('user') and scp_information.get('host') and scp_information.get('path') and scp_information.get('key_path'):
        remote_user = scp_information.get('user')
        remote_host = scp_information.get('host')
        remote_path = scp_information.get('path')
        key_path = scp_information.get('key_path')
        
        file_path = f'src/files/{file_name}.hc22000'
        command = ['scp', '-i', key_path, '-o', 'StrictHostKeyChecking=no', '-o' ,'UserKnownHostsFile=/dev/null', file_path, f'{remote_user}@{remote_host}:{remote_path}']
        try:
            subprocess.run(command, capture_output=True, text=True)
            write_log(f'[+] {file_name} sent through SCP')
        
        except subprocess.CalledProcessError as e:
            write_log(f'[!] Error transfering over scp {file_name}.hc22000')
            sys.exit(1)
    else:
        write_log("[!] You must specify fields 'user', 'host', 'path' and 'key_path' to use scp")
        sys.exit(1)