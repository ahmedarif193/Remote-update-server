#!/usr/bin/python3
import json, sys, os, threading, time, io, errno

from werkzeug.wrappers import Request, Response
from werkzeug.serving import run_simple

from jsonrpc import JSONRPCResponseManager, dispatcher
import hashlib
import syslog

import tempfile

syslog.openlog("CMGP SERVER")

queue_cmd = [] 
queue_connected = [] 
PIDFILE="/var/run/cmgpserver.pid"
tmpdir = "/tmp/"
fifo_filename = os.path.join(tmpdir, 'cmgpserver')
print (fifo_filename)
if os.path.exists(fifo_filename) :
    os.remove(fifo_filename)
try:
    os.mkfifo(fifo_filename)
except OSError:
    print ("Failed to create FIFO")

def all_done():
    os.remove(PIDFILE)
    fifo.close()
    os.remove(fifo_filename)
    os.rmdir(tmpdir)
def writePidFile():
        pid = str(os.getpid())
        f = open(PIDFILE, 'w')
        f.write(pid)
        f.close()

def thread_function(name):
    time.sleep(1)
    while True :
        fifo = open(fifo_filename, 'r')
        # write stuff to fifo
        try:
            buffer = fifo.read()
        except OSError as err:
            if err.errno == errno.EAGAIN or err.errno == errno.EWOULDBLOCK:
                buffer = None
            else:
                raise  # something else has happened -- better reraise
        if buffer is None: 
            print(" nothin")
        else:
            c = buffer
            test = str(c)
            print(test)
            print(test.find('o') )
            if c.find('ListConnected') != -1:
                syslog.syslog(syslog.LOG_DEBUG, 'Connected Devices : ' + str(queue_connected))
            if c.find('DeviceList') != -1:
                #parameter = c.split('=')
                x = c.split('.')
                x.pop(0)
                queue_cmd.append(x[0]+'.'+x[1])

def md5(fname):
    hash_md5 = hashlib.md5()
    if os.path.exists(fname):
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
    return hash_md5.hexdigest()

def ServerLog(**kwargs):
    print("ServerLog")
    syslog.syslog(syslog.LOG_DEBUG, kwargs['id_device']+ " >> " + kwargs['message'])
    return "ok"

def CheckVersion(**kwargs):
    print("checkversion")
    print(kwargs)
    syslog.syslog(syslog.LOG_DEBUG, kwargs['id_device']+ " >> checkversion")
    with open('version_data.json') as json_file:
        data = json.load(json_file)
        data["md5"] = md5("/var/www/html/"+ data["filename"])
        if kwargs['id_device'] not in queue_connected:
            queue_connected.append(kwargs['id_device'])
        for i in queue_cmd :
            print('print ' + i)
            if kwargs['id_device'] in i:
                queue_cmd.remove(i)
                #cmd = str(i.split('.')[1].split('=')[0])
                #cmd_value = str(i.split('.')[1].split('=')[1])
                x = i.split('.')
                x.pop(0)
                data['cmd'] = x[0].strip()
                print('ok, send cmd'+ x[0])
    return data

@Request.application
def application(request):

    # Dispatcher is dictionary {<method_name>: callable}
    dispatcher["checkversion"] = CheckVersion
    dispatcher["ServerLog"] = ServerLog
    response = JSONRPCResponseManager.handle(
        request.get_data(cache=False, as_text=True), dispatcher)
    return Response(response.json, mimetype='application/json')


if __name__ == '__main__':
    writePidFile()
    x = threading.Thread(target=thread_function, args=(1,))
    x.start()
    run_simple('0.0.0.0', 9999, application)
    x._stop()
    all_done()
