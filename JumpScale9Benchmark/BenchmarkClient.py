from js9 import j
from NodeInstaller import NodeInstaller
from VMSetup import VMSetup
from Benchmark import Benchmark
from Summary import Summary
from time import sleep

TEMPLATE = """
ips = "all"
amount = 16
host = "10.1.0.2"
"""

JSConfigBase = j.tools.configmanager.base_class_config

class BenchmarkClient(JSConfigBase):

    def __init__(self, instance, data={}, parent=None, interactive=False):
        JSConfigBase.__init__(self, instance=instance, data=data,
                              parent=parent, template=TEMPLATE, interactive=interactive)
        self.ips = self.config.data['ips']
        self.amount = self.config.data['amount']
        self._nodes = None
        self.host = self.config.data['host']
    
    @property
    def nodes(self):
        """list of targeted nodes
        
        :return: list of nodes
        :rtype: zero_os client list
        """

        if not self._nodes:
            if self.ips.casefold() == 'all':
                self._nodes = self._get_all_nodes()
            #else:
                #TODO: get nodes from ips list comma separated
        return self._nodes

    @property
    def node_ips(self):
        return [node.addr for node in self.nodes]
    
    @property
    def sshkeyname(self):
        return j.tools.configmanager.keyname

    def _get_all_nodes(self):
        instances = j.clients.zero_os.list()
        nodes = [j.clients.zero_os.sal.get_node(instance) for instance in instances]
        return nodes
    
    def reboot(self):
        """ reboot all targeted nodes
        
        """

        for node in self.nodes:
            self.logger.debug("rebooting node {}".format(node.addr))
            node.reboot()

    def prepare(self):
        """prebare targeted nodes
        
        """

        sshkey = j.clients.sshkey.get(self.sshkeyname)
        pubkey = sshkey.pubkey
        installers = []
        for node in self.nodes:
            self.logger.debug("preparing node {}".format(node.addr))
            install = NodeInstaller(node.client, sshkey.pubkey, self.amount, self.host)
            install.start()
            installers.append(install)

        for installer in installers:
            installer.join()

    def setupVMs(self):
        """ creating vms
        
        """

        installers = []
        for i in range(1, self.amount + 1):
            port = 1000 + i

            self.logger.debug("creating hosts configuration: vm-port-%d" % port)
            for ip in self.node_ips:
                installer = VMSetup(ip, port)
                installer.start()
                installers.append(installer)

        for installer in installers:
            installer.join()    

    def benchhmark_run(self):
        """run benchmark on the created vms
        
        """

        installers = []
        for i in range(1, self.amount + 1):
            port = 1000 + i
    
            self.logger.debug("running benchmark on: vm-port-%d" % port)
            for ip in self.node_ips:
                installer = Benchmark(ip, port)
                installer.start()
                installers.append(installer)

        for installer in installers:
            installer.join()
            
    def print_summary(self):
        Summary(self.node_ips)
    
    def nodes_wait(self):
        self.logger.debug("waiting for nodes to come alive")
        for node in self.nodes:
            while not node.is_running():
                sleep(1)
            self.logger.debug("{} is running".format(node.addr))
        return