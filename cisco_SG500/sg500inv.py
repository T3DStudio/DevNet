import multiprocessing as mp
import paramiko
import time
import re
import datetime
import sys
import json

#####  COMMON

# get config from switch and save it to file
connect  = False
# read files and make csv table
makebase = True


com_inv = 'show inventory'

bfn_idsc = 'description'
bfn_ipid = 'PID'
bfn_ivid = 'VID'
bfn_isnn = 'SN'

base = {}

#####################################

def _BaseAddKey(dname, intkey, skey, sval, add):
    if dname not in base:
        base.update({dname: {}})
    if intkey not in base[dname].keys():
        base[dname].update({
            intkey: {
                bfn_idsc: '',
                bfn_ipid: '',
                bfn_ivid: '',
                bfn_isnn: ''
            }
        })
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

def _parseInv(str, hname, curkey):
    tmp = _RegexGet(str, '(?<=NAME: ").*?(?=")')
    if str == '':
        curkey = ''
    elif tmp:
        curkey = tmp

    if curkey != '':
        tmp = _RegexGet(str, '(?<=DESCR: ").*?(?=")')
        if tmp: _BaseAddKey(hname, curkey, bfn_idsc, tmp, False)

        tmp = _RegexGet(str, '(?<=PID: ).*?(?=VID)')
        if tmp: _BaseAddKey(hname, curkey, bfn_ipid, tmp, False)

        tmp = _RegexGet(str, '(?<=VID: ).*?(?= )')
        if tmp: _BaseAddKey(hname, curkey, bfn_ivid, tmp, False)

        tmp = _RegexGet(str, '(?<=SN: ).*')
        if tmp: _BaseAddKey(hname, curkey, bfn_isnn, tmp, False)

    return curkey


#####  MAIN

def sg500command(addr, channel, command, wait, showcomm=True):
    if showcomm:
        print(addr+': ', command)
    channel.send(command + "\n")
    if wait > 0:
        time.sleep(wait)

def sg500start(addr, comdata):
    print(addr+':', '---- Start ---------------')

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(hostname=addr, port=comdata['port'])
    except Exception as exception:
        print(addr+': ', str(exception))

    try:
        client.get_transport().auth_none(comdata['login'])
        channel = client.invoke_shell()
    except Exception as exception:
        print(str(exception))
        return

    time.sleep(0.5)
    sg500command(addr, channel, comdata['login'], 0.5, False)
    sg500command(addr, channel, comdata['passw'], 1  , False)
    sg500command(addr, channel, com_inv         , 3  )
    print(addr, 'recv and decode')
    #
    lines = channel.recv(100000).decode('utf-8').split('\n')
    client.close()

    try:   f = open(addr+'_inv.txt', 'w')
    except IOError:
        print('Could not open ' + addr + '!')
        exit(1)
    for ln in lines:
        tmp = ln.rstrip()
        f.write("%s\n" % tmp)
    f.close()

    print(addr + ':', '---- End ----------------')


def _writeBase(inv, devices):
    for addr in devices:
        try:   f = open(addr+'_inv.txt', 'r')
        except IOError:
            print('Could not open ' + addr + '!')
            continue
        result = f.readlines()
        f.close()

        hostname = ''
        mode     = 0
        curkey   = ''


        for ln in result:
            s = ln.rstrip()
            if hostname == '':
                if '#' in s:
                    hostname = _RegexGet(s, '.*(?=#)')

            if ('#'+com_inv ) in s: mode = 1

            if hostname != '':
                if mode == 1:
                    curkey = _parseInv(s, hostname, curkey)

        print(addr + ':', hostname)

    dt = datetime.datetime.now()
    fn = inv+'_inv_' + dt.strftime('%Y.%m.%d_%H.%M.%S') + '.csv'

    try:
        f = open(fn, 'w')
    except IOError:
        print('Could not open ' + fn + '!')
        exit(1)

    firstln = True
    capt = ''
    for device in base:
        lst = list(base[device].keys())
        lst.sort()
        for intr in lst:
            strt = device+';'+intr

            for key in base[device][intr]:
                if firstln:
                    if capt == '': capt = 'hostname;#;'+key
                    else:          capt = capt + ';' + key

                ts = base[device][intr][key]

                strt = strt + ';' + ts

            if firstln:
                f.write(capt + '\n')
                firstln = False
            f.write(strt + '\n')
    f.close()


def main(*args):
    inv = 'BD'

    with open('mpsg500.json') as json_file:
        data = json.load(json_file)

    login   = data[inv]['login'  ]
    passw   = data[inv]['pass'   ]
    port    = data[inv]['port'   ]
    devices = data[inv]['devices']

    if(connect):
        processes = list()
        with mp.Pool(10) as pool:
            comdata = {
                'login': login,
                'passw': passw,
                'port' : port
            }
            for device in devices:
                processes.append(pool.apply_async(sg500start, args=(device, comdata, )))

            for process in processes:
                process.get()

    if(makebase):
        _writeBase(inv, devices)


if __name__ == '__main__':
    _, *scripts_args = sys.argv

    main(*scripts_args)
