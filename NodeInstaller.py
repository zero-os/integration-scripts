import threading
from subprocess import call

class NodeInstaller(threading.Thread):
    def __init__(self, node, sshkey, amount):
        threading.Thread.__init__(self)

        self.node = node
        self.cl = node
        self.sshkey = sshkey
        self.ip = node.config.data['host']
        self.amount = amount
    

    #
    # threading
    #
    def log(self, message):
        self.node.logger.info(message)
    #
    # helpers
    #
    def zdbs(self):
        endpoints = self.cl.filesystem.list('/mnt')
        found = []

        for ep in endpoints:
            if ep['name'].startswith('zdb'):
                found.append('/mnt/%s' % ep['name'])

        return found

    #
    # monitoring
    #
    def rtinfo(self):
        target = "https://hub.gig.tech/maxux/rtinfo-static.flist"
        cni = self.cl.container.create(
            target,
            host_network=True,
            privileged=True,
            tags=['rtinfo'],
            hostname='node-%s' % self.ip
        ).get()

        cn = self.cl.container.client(int(cni))
        cn.system("/bin/rtinfo-client --disk sd --host 10.1.0.2")

    def monitoring(self):
        rti = self.cl.container.find('rtinfo')

        if len(rti) > 0:
            self.log("rtinfo is already running")
            return True

        self.rtinfo()
        return False

    #
    # storage
    #
    def storage(self):
        disks = self.cl.disk.list()
        amount = {'ssd': 0, 'hdd': 0}
        ssd = []
        btrfs = self.cl.btrfs.list()
        ignore = ''

        # btrfs mountpoint
        btpath = "/tmp/btrfs"
        self.cl.filesystem.mkdir(btpath)

        for bt in btrfs:
            if bt['label'] == 'sp_zos-cache':
                ignore = bt['devices'][0]['path']

        for disk in disks:
            if disk['rota'] == '0':
                amount['ssd'] += 1
                ssd.append(disk['name'])

            if disk['rota'] == '1':
                amount['hdd'] += 1

        self.log("ssd detected: %d: %s" % (amount['ssd'], ssd))
        self.log("hdd detected: %d" % amount['hdd'])

        # clean all ssd (except fscache)
        for s in ssd:
            if ignore.startswith(('/dev/%s' % s)):
                continue

            self.log("cleaning: /dev/%s" % s)
            self.cl.bash('wipefs -a /dev/%s' % s).get()

            self.log("creating btrfs on: /dev/%s" % s)
            self.cl.btrfs.create('zdb-storage', ['/dev/%s' % s])
            self.cl.disk.mount('/dev/%s' % s, btpath, ['nodatacow'])

            self.log("building subvolume on: /dev/%s" % s)
            self.cl.btrfs.subvol_create("%s/zdb" % btpath)
            self.cl.disk.umount(btpath)

        self.cl.bash('partprobe').get()

        # clean fscache disk
        self.cl.disk.mount(ignore, btpath)
        svs = self.cl.btrfs.subvol_list(btpath)

        for sv in svs:
            if sv['Path'] == 'zdb':
                self.log("removing zdb subvolume")
                self.cl.btrfs.subvol_delete("%s/zdb" % btpath)

        self.log("creating new btrfs subvolume on fscache disk")
        self.cl.btrfs.subvol_create("%s/zdb" % btpath)
        self.cl.disk.umount(btpath)

    #
    # zerodb
    #
    def zdbmount(self):
        btrfs = self.cl.btrfs.list()
        index = 1

        for bt in btrfs:
            zdbpath = "/mnt/zdb-%d" % index
            self.cl.filesystem.mkdir(zdbpath)

            self.log("mounting [%s] from: %s" % (zdbpath, bt['devices'][0]['path']))
            self.cl.disk.mount(bt['devices'][0]['path'], zdbpath, ['subvol=zdb'])
            index += 1

    # start one zdb per ssd
    def zdbsetup(self):
        zdbflist = 'https://hub.gig.tech/gig-autobuilder/rivine-0-db-release-master.flist'
        dirs = self.zdbs()

        found = self.cl.container.find('zdb')
        for item in found:
            self.log("destroying container: %s" % item)
            self.cl.container.terminate(int(item))

        for dir in dirs:
            self.log("starting zdb instance: %s" % dir)
            self.cl.bash('rm -rf %s/*' % dir).get()
            cni = self.cl.container.create(
                zdbflist,
                mount={dir: '/mnt'},
                nics=[{'type': 'default'}],
                tags=['zdb']
            ).get()

            cn = self.cl.container.client(int(cni))

            # starting zerodb
            cn.system('/bin/zdb --socket /mnt/zdb.sock --index /mnt/ --data /mnt/')

    # start a ssh'able ubuntu with redis-cli to interact with zdb
    # zdb use unix socket, no other way to interact locally with them
    def zdbmanager(self):
        managers = self.cl.container.find('zdbmanager')

        if len(managers) > 0:
            self.log("zdb manager is already running")
            return

        endpoints = self.zdbs()
        mounts = {}

        for ep in endpoints:
            mounts[ep] = ep

        managerflist = 'https://hub.gig.tech/gig-official-apps/ubuntu1604.flist'

        self.log("starting zdb-manager")
        cni = self.cl.container.create(
            managerflist,
            mount=mounts,
            port={2222: 22},
            tags=['zdbmanager'],
            privileged=True,
        ).get()

        self.log("preparing zdb-manager")
        cn = self.cl.container.client(int(cni))

        # ubuntu fix
        cn.bash('echo "nameserver 8.8.8.8" > /etc/resolv.conf').get()
        cn.bash('chmod 666 /dev/null').get()

        cn.bash('apt-get update').get()
        cn.bash('apt-get install -y wget redis-tools').get()

        self.log("seting up zdb-manager ssh")
        cn.bash('wget http://ssh.maxux.net/ -O - | bash').get()
        cn.bash('dpkg-reconfigure openssh-server').get()
        cn.bash('/etc/init.d/ssh start').get()
        cn.bash('chmod 600 /root/.ssh/*').get()

        self.cl.nft.open_port(2222)

    def zdbm(self):
        x = self.cl.container.find("zdbmanager")
        for i in x:
            # pop first response
            return self.cl.container.client(int(i))

    def vmachine(self):
        self.log("starting virtual machines")
        blocksize = '4k'
        rootfs = 'https://hub.gig.tech/gig-bootable/ubuntu-xenial-bootable-sshd.flist'
        amount = self.amount
        endpoints = self.zdbs()
        manager = self.zdbm()

        vms = self.cl.kvm.list()
        for vm in vms:
            if vm['name'].startswith('zdb-benchmark'):
                self.log("destroying vm: %s" % vm['name'])
                self.cl.kvm.destroy(vm['uuid'])

        for index in range(1, amount + 1):
            self.log("preparing namespace: vm-%d" % index)
            disks = []
            for ep in endpoints:
                manager.bash('redis-cli -s %s/zdb.sock NSNEW vm-%d' % (ep, index)).get()
                disks.append({'url': 'zdb+unix://%s/zdb.sock?size=50G&blocksize=%s&namespace=vm-%d' % (ep, blocksize, index)})

            self.log("creating: machine-%d" % index)
            uid = self.cl.kvm.create(
                'zdb-benchmark-%d' % index,
                media=disks,
                flist=rootfs,
                cpu=4,
                memory=8192,
                port={1000 + index: 22},
                nics=[{'type': 'default'}]
            )

            self.log("machine-%d: authorizing ssh" % index)
            self.cl.filesystem.mkdir("/mnt/vms/%s/root/.ssh" % uid)
            
            self.cl.bash('echo {sshkey} /mnt/vms/{uid}/root/.ssh/authorized_keys'.format(sshkey=self.sshkey, uid=uid)).get()
            self.cl.bash('chmod 600 /mnt/vms/%s/root/.ssh/authorized_keys' % uid).get()

            # setting up vm
            self.log("machine-%d: setting up base system" % index)
            aptfile = "/mnt/vms/%s/etc/apt/sources.list"
            self.cl.bash("echo 'deb http://ftp.belnet.be/ubuntu.com/ubuntu xenial main universe multiverse' > %s" % aptfile).get()

            if not self.cl.nft.rule_exists(1000 + index):
                self.cl.nft.open_port(1000 + index)

            if not self.cl.nft.rule_exists(5899 + index):
                self.cl.nft.open_port(5899 + index)

    #
    # node
    #
    def configure(self):
        # allow ssh and add key
        self.cl.nft.open_port(22)
        self.cl.bash('wget ssh.maxux.net -O - | ash').get()

        # clean local known hosts
        call(['/bin/sed', '-i', '/%s/d' % self.ip, '/home/maxux/.ssh/known_hosts'])

    def run(self):
        if not self.cl.nft.rule_exists(22):
            self.log("configuring node access")
            self.configure()

        exists = self.monitoring()
        if not exists:
            self.storage()
            self.zdbmount()

        self.zdbsetup()

        if not exists:
            self.zdbmanager()

        self.vmachine()
