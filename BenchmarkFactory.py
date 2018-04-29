from js9 import j
from BenchmarkClient import BenchmarkClient

JSConfigBase = j.tools.configmanager.base_class_configs

class BenchmarkFactory(JSConfigBase):
    def __init__(self):
        self.__jslocation__ = "j.tools.benchmark"
        JSConfigBase.__init__(self, BenchmarkClient)

    
    def test(self):
        nodes = [
            '192.168.193.232',
            '192.168.193.72',
            '192.168.193.111',
            '192.168.193.55',
            '192.168.193.2',
            '192.168.193.218',
            '192.168.193.75',
            '192.168.193.191',
            '192.168.193.56',
            '192.168.193.132',
        ]
        for node in nodes:
            j.clients.zero_os.get(instance=node, data={'host':node})
        client = self.get('test')
        client.reboot()
        client.nodes_wait()
        client.prepare()
        client.setupVMs()
        client.benchhmark_run()
        client.print_summary()

