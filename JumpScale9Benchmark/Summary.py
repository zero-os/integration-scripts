from js9 import j

class Summary():

    def __init__(self, nodes):
        self.logger = j.logger.get("cluster.summary")

        data = []
        for target in nodes:
            data.append(self.summary(target))

        self.cluster(data)

    def emptyval(self):
        return {
            'linear': {'read': 0, 'write': 0, 'rbw': 0, 'wbw': 0},
            'random': {'read': 0, 'write': 0, 'rbw': 0, 'wbw': 0}
        }

    def cluster(self, data):
        fs = self.emptyval()

        for result in data:
            node = self.emptyval()

            for value in result:
                node['linear']['read'] += value['read']['read']
                node['linear']['write'] += value['write']['write']
                node['linear']['rbw'] += value['read']['rbw']
                node['linear']['wbw'] += value['write']['wbw']

                node['random']['read'] += value['random']['read']
                node['random']['write'] += value['random']['write']
                node['random']['rbw'] += value['random']['rbw']
                node['random']['wbw'] += value['random']['wbw']

            nl = node['linear']
            nr = node['random']

            self.logger.debug("node linear: read [{:,} iops], write [{:,} iops]".format(nl['read'], nl['write']))
            self.logger.debug("node linear: read [%.1f KB/s], write [%.1f KB/s]" % (nl['rbw'], nl['wbw']))

            self.logger.debug("node random: read [{:,} iops], write [{:,} iops]".format(nr['read'], nr['write']))
            self.logger.debug("node random: read [%.1f KB/s], write [%.1f KB/s]" % (nr['rbw'], nr['wbw']))

            fs['linear']['read'] += nl['read']
            fs['linear']['write'] += nl['write']
            fs['random']['read'] += nr['read']
            fs['random']['write'] += nr['write']

        self.logger.info("---------------------------")
        self.logger.info("cluster linear: read [{:,} iops], write [{:,} iops]".format(fs['linear']['read'], fs['linear']['write']))
        self.logger.info("cluster random: read [{:,} iops], write [{:,} iops]".format(fs['random']['read'], fs['random']['write']))

    def report(self, cl, vm, filename):
        fullpath = "/mnt/vms/%s/tmp/%s" % (vm['uuid'], filename)

        while True:
            x = cl.bash('cat %s' % fullpath).get()
            data = x.stdout
            if '(all jobs)' in data:
                break

        return data.split("\n")

    def iops(self, lines):
        iops = {'read': None, 'write': None, 'rbw': None, 'wbw': None}

        for line in lines:
            if not 'iops=' in line:
                continue

            if line.startswith("  read :"):
                x = line.split(',')
                iops['read'] = int(x[2].strip()[5:])
                iops['rbw'] = float(x[1].strip()[3:].replace('KB/s', ''))

            if line.startswith("  write:"):
                x = line.split(',')
                iops['write'] = int(x[2].strip()[5:])
                iops['wbw'] = float(x[1].strip()[3:].replace('KB/s', ''))

        return iops

    def summary(self, target):
        cl = target.client

        cl.logger.debug("loading virtual machines list")
        results = []
        vms = cl.kvm.list()

        cl.logger.info("analyzing virtual machines reports")
        for vm in vms:
            vmread = self.report(cl, vm, "benchmark-result-read")
            vmwrite = self.report(cl, vm, "benchmark-result-write")
            vmrand = self.report(cl, vm, "benchmark-result-rand")

            values = {
                'read': self.iops(vmread),
                'write': self.iops(vmwrite),
                'random': self.iops(vmrand)
            }

            results.append(values)

        return results
