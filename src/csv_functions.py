import csv

from common_functions import write_log


def get_required_network_information(file_name: str, network_name: str):
    try:
        with open(f'src/files/{file_name}-01.csv', newline='') as f:
            reader = csv.reader(f)
            for row in reader:
                if row and len(row) >= 13 and row[13].strip() == network_name:  # row[13] -> ESSID
                    return row[0].strip(), row[3].strip()
        
        return None, None
    
    except FileNotFoundError:
        write_log(f'[!] File with name {file_name} not found as an airodump-ng output file')
        return None, None