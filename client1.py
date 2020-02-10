#!/usr/bin/python3
import requests
import json
import random
import hashlib
import tarfile
import os
from pathlib import Path
import time, threading
import subprocess
import signal

url_server = 'http://ahmed-arif.com/'
post_server = "http://localhost:9999/"
url_post_server =  post_server +"jsonrpc"
headers = {'content-type': 'application/json'}
def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

id_device = 'DEVICE_DEMO'
global ssh_pid
ssh_pid = 0
payload_id = 0
def remote_log(message):
    payload = {"method": "ServerLog","params": {"id_device": id_device, "message": message }, "jsonrpc": "2.0", "id": payload_id,}
    response = requests.post(url_post_server, data=json.dumps(payload), headers=headers)

def runtime():
    
    # Example echo method
    payload_id = random.randint(1,101)
    print(payload_id)
    payload = {
        "method": "checkversion",
        "params": {"id_device": id_device},
        "jsonrpc": "2.0",
        "id": payload_id,
    }

    try:
        response = requests.post(url_post_server, data=json.dumps(payload), headers=headers)
    except:
        print("Server is not reachable...")
        return 1
    if response.status_code == 200:
        
        response = response.json()
        ret_id = response['id']
        if ret_id == payload_id :
            global ssh_pid
            print(response)
            remote_version_code = response['result']['version_code']
            current_version_code = int(Path("/etc/issue_version_code").read_text())
            cmd = response['result'].get('cmd')
            if cmd :
                cmd_split = cmd.split('=')
                if 'SSHTunnel' in cmd_split[0]:
                    if int(cmd_split[1]) == 1:
                        if ssh_pid == 0 :
                            proc = subprocess.Popen("cat", shell=True, preexec_fn=os.setsid)
                            print('ok')
                            ssh_pid = proc.pid
                            remote_log("starting Remote SSH Service .. on pid" + str(ssh_pid))
                        else:
                            remote_log("already running")
                            print("already running")
                    if int(cmd_split[1]) == 0:
                        if ssh_pid > 0 :
                            os.killpg(ssh_pid, signal.SIGTERM)
                            ssh_pid = 0
                            print("killing process")

                    print("execute the command")

            
            if remote_version_code == current_version_code :
                url_filename = response['result']['filename']
                print('process upgrade '  + url_filename)
                r = requests.get(url_server + url_filename)
                if r.status_code == 200 :
                    filename_tmp = '/tmp/'+ url_filename
                    with open(filename_tmp, 'wb') as f:
                        f.write(r.content)
                    archive_md5 = md5(filename_tmp)
                    print(archive_md5)

                    if archive_md5 == response['result']['md5'] :
                        remote_log("Download Done, upgrading ...")
                        print("Download Done, upgrading ...")
                        tar = tarfile.open(filename_tmp, "r:gz")
                        tar.extractall("/tmp/")
                        tar.close()
                        working_dir = "/tmp/" + os.path.splitext(os.path.splitext(url_filename)[0])[0]#remove file extension
                        if os.path.isdir(working_dir)  == True: 
                            print(working_dir) 
                        else:
                            message = "incorrect working dir, please make sure that the folder insides the archive have the same name as the archive itself"
                            remote_log(message)
                    else:
                        message = "the md5 " +  archive_md5 + "is not valid, trying later (" + response['result']['md5'] + ") in remote, http 404 page?"
                        payload = {"method": "ServerLog","params": {"id_device": id_device, "message": message }, "jsonrpc": "2.0", "id": payload_id,}
                        response = requests.post(url_post_server, data=json.dumps(payload), headers=headers)
                        print(message)
                else:
                    message = "error will downloading ... error code :" + str(r.status_code)
                    remote_log(message)
                    print(message)
    threading.Timer(2, runtime).start()
if __name__ == "__main__":
    runtime()