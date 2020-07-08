import multiprocessing as mp
import paramiko
import time
import re
import datetime
import sys
import json

#####  COMMON

# конектится к свичам и собирать инфу в файлы
connect  = False
# парсить файлы и собирать из них базу в csv
makebase = True


base = {}

bfn_tp = 'type'
bfn_dp = 'duplex'
bfn_sp = 'speed'
bfn_st = 'state'
bfn_vl = 'vlan'
bfn_ds = 'descr'
bfn_in = 'int'
bfn_l1 = 'log1'
bfn_l2 = 'log2'
bfn_l3 = 'log3'
bfn_l4 = 'log4'
bfn_mc = 'mac'

logkeys = [bfn_l1, bfn_l2, bfn_l3, bfn_l4]

com_term = 'terminal datadump'
com_inst = 'show interface status'
com_macs = 'show mac address-table'
com_run  = 'show run'
com_log  = 'show logg'

int_re = '(Fa|Gi|Te|fa|gi|te)'

LogNewColumn = 27


####################################################################################


def _BaseAddKey(dname, intkey, skey, sval, add):
    if dname not in base:
        base.update({dname: {}})
    if intkey not in base[dname].keys():
        base[dname].update({
            intkey: {
                bfn_tp: '',
                bfn_dp: '',
                bfn_sp: '',
                bfn_st: '',
                bfn_in: '',
                bfn_vl: '',
                bfn_ds: '',
                bfn_mc: '',
                bfn_l1: '',
                bfn_l2: '',
                bfn_l3: '',
                bfn_l4: ''
                }
        })
    if(skey in base[dname][intkey]):
        if(not add):
            base[dname][intkey].update({skey: sval})
        else:
            if(base[dname][intkey][skey]):
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
        return ''
    else:
        secs = str1.split('/')
        intkey = istr[0]
        for str1 in secs:
            strt = str1
            while len(strt) < 3: strt = '0' + strt
            intkey = intkey + strt
    return intkey


def _parseIntStr(str, hname):
    strs = str.split()
    if(len(strs) == 9):
        ints = _InterfaceFromStr(strs[0])
        if(ints):
            intk = _InterfaceToKey(ints)
            _BaseAddKey(hname, intk, bfn_in, ints   , '')
            _BaseAddKey(hname, intk, bfn_tp, strs[1], '')
            _BaseAddKey(hname, intk, bfn_dp, strs[2], '')
            _BaseAddKey(hname, intk, bfn_sp, strs[3], '')
            _BaseAddKey(hname, intk, bfn_st, strs[6], '')


def _parseIntCfg(str, hname, curk):
    if(str.startswith('interface ')):
        curk = _InterfaceFromStr(str[10:].strip())
        if(curk):
            curk = _InterfaceToKey(curk)
    else:
        if(curk):
            tmp = _Exstr(str, ' switchport access vlan ')
            if(tmp): _BaseAddKey(hname, curk, bfn_vl, tmp, '')
            tmp = _Exstr(str, ' switchport trunk allowed vlan add ')
            if(tmp): _BaseAddKey(hname, curk, bfn_vl, tmp, ',')
            tmp = _Exstr(str, ' description ')
            if(tmp): _BaseAddKey(hname, curk, bfn_ds, tmp, '')
    return curk


def _parseLog(str, hname):
    if('%LINK-W-Down' in str) or ('%LINK-I-Up' in str):
        ints = _InterfaceFromStr(str)
        if(ints):
            intk = _InterfaceToKey(ints)
            if(intk):
                for lk in logkeys:
                    if (len(base[hname][intk][lk].split('\n')) < LogNewColumn):
                        _BaseAddKey(hname, intk, lk, str.rstrip(), '\n')
                        break


def _parseMac(str, hname):
    strs = str.split()
    if(len(strs) == 4):
        ints = _InterfaceFromStr(strs[2])
        if(ints):
            intk = _InterfaceToKey(ints)
            _BaseAddKey(hname, intk, bfn_mc, strs[1], '')

####################################################################################

def sg500command(addr, channel, command, wait, showcomm=True):
    if(showcomm):
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
    sg500command(addr, channel, com_term        , 1  )
    sg500command(addr, channel, com_inst        , 5  )
    sg500command(addr, channel, com_macs        , 15 )
    sg500command(addr, channel, com_run         , 20 )
    sg500command(addr, channel, com_log         , 15 )
    print(addr, 'recv and decode')
    #
    lines = channel.recv(100000).decode('utf-8').split('\n')
    client.close()

    try:   f = open(addr+'.txt', 'w')
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
        try:   f = open(addr+'.txt', 'r')
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

            if(('#'+com_inst) in s): mode = 1
            if(('#'+com_run ) in s): mode = 2
            if(('#'+com_log ) in s): mode = 3
            if(('#'+com_macs) in s): mode = 4

            if(hostname != ''):
                if(mode == 1): _parseIntStr(s, hostname)
                if(mode == 2): curkey = _parseIntCfg(s, hostname, curkey)
                if(mode == 3): _parseLog(s, hostname)
                if(mode == 4): _parseMac(s, hostname)

        print(addr + ':', hostname)

    dt = datetime.datetime.now()
    fn = inv+'_' + dt.strftime('%Y.%m.%d_%H.%M.%S') + '.csv'

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
        cnt = 0
        for intr in lst:
            cnt += 1
            if(cnt == 1) or ((cnt%5) == 0) or (cnt == len(lst)): strt = device
            else: strt = ' '

            for key in base[device][intr]:
                if (firstln):
                    if (capt == ''): capt = 'hostname;'+key
                    else:            capt = capt + ';' + key

                if (key in logkeys): ts = '"' + base[device][intr][key] + '"'
                else:                ts = base[device][intr][key]

                strt = strt + ';' + ts
            if (firstln):
                f.write(capt + '\n')
                firstln = False
            f.write(strt + '\n')
    f.close()


def main(*args):
    inv = 'BDtest'

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
