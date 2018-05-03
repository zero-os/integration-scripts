from js9 import j
import threading
import time

# gevent fix
import gevent.hub
gevent.hub.Hub.backend = "poll"


class VMSetup(threading.Thread):
    def __init__(self, address, port):
        threading.Thread.__init__(self)

        self.address = address
        self.port = port

        x = self.address.split('.')
        self.vmname = "node.%s.vm-%02d" % (x[3], port - 1000)
        self._sshclient = None

    def run(self):
        time.sleep(0.2 * (self.port - 1000))

        # temporary fix
        self.sshclient.execute("wget https://gist.githubusercontent.com/maxux/07d9243698162421c324f51d145952e2/raw/163122299979d26c4d300390632256e5bd1113d9/ssh-inside.sh -O /tmp/ssh-inside.sh 2>&1 | grep saved")
        self.sshclient.execute("bash /tmp/ssh-inside.sh %s 2>&1 | grep '\[.\]'" % self.vmname)

    @property
    def sshclient(self):
        if not self._sshclient:
            sshkeyname = j.tools.configmanager.keyname
            self._sshclient = j.clients.ssh.new(self.address, port=self.port, instance=self.vmname, keyname=sshkeyname, timeout=240)

        return self._sshclient

    @property
    def script(self):
        return """
#!/bin/bash
# id=0

# set hostname if provided
[[ ! -z $1 ]] && hostname "$1"

# rtinfo vm
if [ ! -e /tmp/rtinfo-client-static-x64 ]; then
    wget https://arya.maxux.net/build/rtinfo/rtinfo-client-static-x64 -O /tmp/rtinfo-client-static-x64
    chmod +x /tmp/rtinfo-client-static-x64
    /tmp/rtinfo-client-static-x64 --host 10.1.0.2 --port 10888 --disk vd --daemon
fi

apt-get update
apt-get install -y fio vim

cat > /root/fiofile-read << EOF
[global]
direct=1
ioengine=libaio
size=4g
iodepth=8
thread
group_reporting=1
directory=/mnt/benchmark

[job0]
rw=read

EOF

cat > /root/fiofile-write << EOF
[global]
direct=1
ioengine=libaio
size=4g
iodepth=8
thread
group_reporting=1
directory=/mnt/benchmark

[job]
rw=write

EOF

cat > /root/fiofile-rand << EOF
[global]
direct=1
ioengine=libaio
size=4g
iodepth=8
thread
group_reporting=1
directory=/mnt/benchmark

[job0]
rw=randrw

EOF

# amount of ssd and node id
nssd=$(ls /dev/vd* | wc -l)
nid=$(hostname | cut -d'-' -f2)

# grab disk name based on nodeid
did=$(($(($nid % nssd)) + 1))
dsk=$(ls /dev/vd* | sed -n "${did}{p;q}")

mkdir -p /mnt/benchmark
umount /mnt/benchmark || true
mkfs.ext4 $dsk
mount $dsk /mnt/benchmark

# preallocate benchmark datafile
fio --create_only=1 /root/fiofile-read
"""
