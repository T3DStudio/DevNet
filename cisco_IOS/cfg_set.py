from netmiko import ConnectHandler
from netmiko.ssh_exception import NetMikoTimeoutException
import multiprocessing as mp
import time
import re
import datetime
import sys
import json

#####  COMMON

def main_func(device, condata, commands):
    print(device)

    try:
        net_connect = ConnectHandler(**condata)
    except NetMikoTimeoutException:
        print(device, ': NetMikoTimeoutException')
        return

    for c in commands:
        tmp = net_connect.send_config_set(c)
        print(tmp)

    print(net_connect.send_command('wr'))


def main(*args):
    inv = 'BD'

    with open('cfg_set_inv.json') as json_file:
        data = json.load(json_file)

    login   = data[inv]['login'  ]
    passw   = data[inv]['pass'   ]
    port    = data[inv]['port'   ]
    devices = data[inv]['devices']
    dev_type= data[inv]['devtype']


    commands = [
        'snmp-server group monitor v3 priv read SNMP_READ',
        'snmp-server group prime_read v3 priv',
        'snmp-server group prime_write v3 priv',
        'snmp-server group write-group v3 priv read SNMP_WRITE write SNMP_WRITE',
        'snmp-server view SNMP_READ iso included',
        'snmp-server view SNMP_WRITE iso included',
        'snmp-server host 172.20.33.30 version 3 priv prime_read',
        'snmp-server host 172.20.33.30 version 3 priv prime_write',
    ]

    processes = list()
    with mp.Pool(10) as pool:
        for device in devices:
            condata = {
                'device_type': dev_type,
                'ip'         : device,
                'username'   : login,
                'password'   : passw,
                'port'       : port
            }
            processes.append(pool.apply_async(main_func, args=(device, condata, commands )))

        for process in processes:
            process.get()

if __name__ == '__main__':
    _, *scripts_args = sys.argv

    main(*scripts_args)
