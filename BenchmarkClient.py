from js9 import j
from NodeInstaller import NodeInstaller
from VMSetup import VMSetup
from Benchmark import Benchmark
from Summary import Summary
from time import sleep

TEMPLATE = """
ips = "all"
amount = 16
"""

JSConfigBase = j.tools.configmanager.base_class_config

class BenchmarkClient(JSConfigBase):

    def __init__(self, instance, data={}, parent=None, interactive=False):
        JSConfigBase.__init__(self, instance=instance, data=data,
                              parent=parent, template=TEMPLATE, interactive=interactive)
        self.ips = self.config.data['ips']
        self.amount = self.config.data['amount']
        self._nodes = None
    
    @property
    def nodes(self):
        if not self._nodes:
            if self.ips.casefold() == 'all':
                self._nodes = self._get_all_nodes()
            #else:
                #TODO: get nodes from ips list comma separated
        return self._nodes

    @property
    def node_ips(self):
        return [node.config.data['host'] for node in self.nodes]
    
    @property
    def sshkeyname(self):
        return j.tools.configmanager.keyname

    def _get_all_nodes(self):
        instances = j.clients.zero_os.list()
        nodes = [j.clients.zero_os.get(instance) for instance in instances]
        return nodes
    
    def reboot(self):
        for node in self.nodes:
            self.logger.debug("rebooting node {}".format(node.config.data['host']))
            node.bash("reboot")

    def prepare(self):
        sshkey = j.clients.sshkey.get(self.sshkeyname)
        pubkey = sshkey.pubkey
        for node in self.nodes:
            self.logger.debug("preparing node {}".format(node.config.data['host']))
            install = NodeInstaller(node, sshkey.pubkey, self.amount)
            install.start()

    def setupVMs(self):
        for i in range(1, self.amount + 1):
            port = 1000 + i

            self.logger.log("creating hosts configuration: vm-port-%d" % port)
            for ip in self.node_ips:
                VMSetup(ip, port).start()

    def benchhmark_run(self):
        for i in range(1, self.amount + 1):
            port = 1000 + i
    
            self.logger.log("running benchmark on: vm-port-%d" % port)
            for ip in self.node_ips:
                Benchmark(ip, port).start()

    def print_summary(self):
        Summary(self.node_ips)
    
    def nodes_wait(self):
        self.logger.debug("waiting for nodes to come alive")
        for node in self.nodes:
            while not node.running():
                sleep(1)
        return
