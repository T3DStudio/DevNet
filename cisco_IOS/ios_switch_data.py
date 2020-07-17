from netmiko import ConnectHandler
from netmiko.ssh_exception import NetMikoTimeoutException
import multiprocessing as mp
import time
import re
import datetime
import sys
import json

MaxProcess = 20

cmd_hostname = 'show run | include hostname'
cmd_shintst  = 'show inter status'
cmd_shmav    = 'show mac addr'
cmd_ipdtra   = 'show ip device tracking all'
cmd_log      = 'show log | i %'

base = {}

_ip = 'ip'
_vl = 'vlan'
_st = 'state'
_mc = 'mac'
_ds = 'descr'
_in = 'int'
_ac = 'act'
_sp = 'speed'
_l1 = 'log page 1'
_l2 = 'log page 2'
_l3 = 'log page 3'
_l4 = 'log page 4'

forder = [_in, _vl, _st, _mc, _ip, _ds, _ac, _l1, _l2, _l3, _l4]

logkeys = [_l1, _l2, _l3, _l4]

LogNewColumn = 27


# base = {'FDCXX' : {'int' : {_ip: '', ...}}}
# Po|po
int_re = '(Fa|fa|Gi|gi|Te|te)'
int_mc = '([0-9a-fA-F]{4}\.){2}[0-9a-fA-F]{4}'

#####  COMMON

def _BaseAddKey(dname, intkey, skey, sval, add):
    if dname not in base:
        base.update({dname: {}})
    if intkey not in base[dname].keys():
        base[dname].update({intkey: {} })
        for k in forder:
            base[dname][intkey].update({k: ''})
    if skey in base[dname][intkey]:
        if not add:
            base[dname][intkey].update({skey: sval})
        else:
            if base[dname][intkey][skey]:
                base[dname][intkey].update({skey: base[dname][intkey][skey] + add + sval})
            else:
                base[dname][intkey].update({skey: sval})

def _RegexGet(str, pat):
    match = re.search(pat, str)
    return match[0] if match else ''

def _Exstr(str, prefix):
    if str.startswith(prefix):
        return str[len(prefix):]
    return ''

def _InterfaceFromStr(str):
    tmp = _RegexGet(str+' ', '(?='+int_re+').*?(?=(\s))')
    return tmp.replace(_RegexGet(tmp, '(?<='+int_re+').*?(?=\d)'), '')

def _InterfaceToKey(istr):
    str1 = ''
    for ch in istr:
        if ch.isdigit() or ch == '/':
            str1 = str1 + ch
    if str1 == '':
        return '0'
    else:
        secs = str1.split('/')
        intkey = istr[0]
        for str1 in secs:
            intkey = intkey + str1.zfill(3)
    return intkey

#################################### PARSE COMMANDS

def _ParseIntStatus(raw_out, dname):
    splt_out = raw_out.splitlines()
    for raw_str in splt_out:
        _inter = _InterfaceFromStr(raw_str)
        _intst = _RegexGet(raw_str, '(connected|notconnect)')
        _intds = _RegexGet(raw_str, '(?<=\d ).*(?=(connected|notconnect))')
        _intvl = _RegexGet(raw_str, '(?<=(connected |notconnect)).*?(\d{1,}|trunk|routed)')

        if (_inter == '') or (_intst == '') or (_intvl == ''): continue

        _inkey = _InterfaceToKey(_inter)
        if(_inkey == '0'): continue

        _BaseAddKey(dname, _inkey, _in, _inter, False)

        if _intst == 'connected' : _BaseAddKey(dname, _inkey, _st, 'True' , False)
        if _intst == 'notconnect': _BaseAddKey(dname, _inkey, _st, 'False', False)

        _BaseAddKey(dname, _inkey, _ds, _intds.strip(), False)
        _BaseAddKey(dname, _inkey, _vl, _intvl.strip(), False)


def _ParseMacs(raw_out, dname):
    splt_out = raw_out.splitlines()
    for raw_str in splt_out:
        _inter = _InterfaceFromStr(raw_str)
        _inmac = _RegexGet(raw_str, int_mc)
        _intvl = _RegexGet(raw_str, '.*(?=('+int_mc+'))')

        if (_inter == '') or (_inmac == '') or (_intvl == ''): continue

        _inkey = _InterfaceToKey(_inter)
        if(_inkey == '0'): continue

        _BaseAddKey(dname, _inkey, _vl, _intvl.strip(), False)
        _BaseAddKey(dname, _inkey, _mc, _inmac        , False)


def _ParseIp(raw_out, dname):
    splt_out = raw_out.splitlines()
    for raw_str in splt_out:
        _inter = _InterfaceFromStr(raw_str)
        _inmac = _RegexGet(raw_str, int_mc)
        _intip = _RegexGet(raw_str, '(\d{1,3}\.){3}\d{1,3}')
        _intac = _RegexGet(raw_str, '(ACTIVE|INACTIVE)')

        if (_inter == '') or (_inmac == '') or (_intip == ''): continue

        _inkey = _InterfaceToKey(_inter)
        if (_inkey == '0'): continue

        _BaseAddKey(dname, _inkey, _ip, _intip, False)
        _BaseAddKey(dname, _inkey, _ac, _intac, False)


def _ParseLog(raw_out, dname):
    splt_out = raw_out.splitlines()
    for raw_str in splt_out:
        if('%LINK-3-UPDOWN' in raw_str):
            _inter = _InterfaceFromStr(_RegexGet(raw_str, '(?<=Interface).*(?=,)'))
            _mtime = _RegexGet(raw_str, '.*(?=%)')
            _state = _RegexGet(raw_str, '(?<= to ).*')

            if (_inter == '') or (_mtime == '') or (_state == ''): continue

            _inkey = _InterfaceToKey(_inter)
            if (_inkey == '0'): continue

            for lk in logkeys:
                if (len(base[dname][_inkey][lk].split('\n')) < LogNewColumn):
                    _BaseAddKey(dname, _inkey, lk, _mtime+_state, '\n')
                    break



#################################### MAIN

def _writeBase(inv, mbase):
    dt = datetime.datetime.now()
    fn = inv+'_' + dt.strftime('%Y.%m.%d_%H.%M.%S') + '.csv'

    try:
        f = open(fn, 'w')
    except IOError:
        print('Could not open ' + fn + '!')
        exit(1)

    firstln = True
    capt = ''
    for device in mbase:
        lst = list(mbase[device].keys())
        lst.sort()
        cnt = 0
        for intr in lst:
            cnt += 1
            if(cnt == 1) or ((cnt%5) == 0) or (cnt == len(lst)): strt = device
            else: strt = ' '

            for key in mbase[device][intr]:
                if (firstln):
                    if (capt == ''): capt = 'hostname;'+key
                    else:            capt = capt + ';' + key

                if (key in logkeys): ts = '"' + mbase[device][intr][key] + '"'
                else:                ts = mbase[device][intr][key]

                strt = strt + ';' + ts
            if (firstln):
                f.write(capt + '\n')
                firstln = False
            f.write(strt + '\n')
    f.close()




def main_func(device, condata, mbase):

    print(device, 'START')

    try:
        net_connect = ConnectHandler(**condata)
    except NetMikoTimeoutException:
        print(device, ': NetMikoTimeoutException')
        return

    # hostname
    tmp = net_connect.send_command(cmd_hostname)
    hostname = _Exstr(tmp, 'hostname ')
    print(device, hostname)

    # int status
    tmp = net_connect.send_command(cmd_shintst)
    _ParseIntStatus(tmp, hostname)

    # macs
    tmp = net_connect.send_command(cmd_shmav)
    _ParseMacs(tmp, hostname)

    # ip dev tra
    tmp = net_connect.send_command(cmd_ipdtra)
    _ParseIp(tmp, hostname)

    # log
    tmp = net_connect.send_command(cmd_log)
    _ParseLog(tmp, hostname)

    net_connect.disconnect()
    print(device, 'END')

    mbase.update(base)


def main(*args):
    inv = 'BD_test'

    with open('cfg_set_inv.json') as json_file:
        data = json.load(json_file)

    login   = data[inv]['login'  ]
    passw   = data[inv]['pass'   ]
    port    = data[inv]['port'   ]
    devices = data[inv]['devices']
    dev_type= data[inv]['devtype']

    manager = mp.Manager()
    mbase = manager.dict()
    processes = list()
    with mp.Pool(MaxProcess) as pool:
        for device in devices:
            condata = {
                'device_type': dev_type,
                'ip'         : device,
                'username'   : login,
                'password'   : passw,
                'port'       : port
            }
            processes.append(pool.apply_async(main_func, args=(device, condata, mbase, )))

        for process in processes:
            process.get()

    _writeBase(inv, mbase)


if __name__ == '__main__':
    _, *scripts_args = sys.argv

    main(*scripts_args)

