import threading

class VMSetup(threading.Thread):
    def __init__(self, address, port):
        threading.Thread.__init__(self)

        self.address = address
        self.port = port

        x = self.address.split('.')
        self.vmname = "node.%s.vm-%02d" % (x[3], port - 1000)
        self._prefab = None

    def run(self):
        self.prefab.core.file_write('/tmp/ssh-inside.sh', self.script)
        self.prefab.core.run('bash -x /tmp/ssh-inside.sh %s' % self.vmname)
        self.logger.log("%s: done" % self.vmname)
    
    @property
    def prefab(self):
        if not self._prefab:
            sshkeyname = j.tools.configmanager.keyname
            sshclient = j.client.ssh.new(self.address, port=self.port, instance=self.vmname, keyname=sshkeyname)
            self._prefab = sshclient.executor().prefab
        return self._prefab

    @property
    def script(self):
        return """
#!/bin/bash
# id=0

# set hostname if provided
[[ ! -z $1 ]] && hostname "$1"

# dumb vm with wrong sources filename
[[ -e /etc/apt/source.list ]] && mv /etc/apt/source.list /etc/apt/sources.list

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

# for disk in /dev/vd*; do
#     mkdir -p /mnt/ssd-$id
#     umount /mnt/ssd-$id || true
#
#     mkfs.ext4 $disk
#     mount $disk /mnt/ssd-$id
#
#     echo "[job-$id]" >> /root/fiofile
#     echo "directory=/mnt/ssd-$id" >> /root/fiofile
#     echo "" >> /root/fiofile
#
#    id=$(($id + 1))
# done

# preallocate benchmark datafile
fio --create_only=1 /root/fiofile-read
"""