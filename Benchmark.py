import threading

class Benchmark(threading.Thread):
    def __init__(self, address, port):
        threading.Thread.__init__(self)

        self.address = address
        self.port = port

        x = self.address.split('.')
        self.vmname = "node.%s.vm-%02d" % (x[3], port - 1000)
        self._prefab = None

    def run(self):
        self.prefab.core.upload('run-benchmark.sh', '/tmp/run-benchmark.sh')
        self.prefab.core.run('bash /tmp/run-benchmark.sh')
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

fio /root/fiofile-read > /tmp/benchmark-result-read
fio /root/fiofile-write > /tmp/benchmark-result-write
fio /root/fiofile-rand > /tmp/benchmark-result-rand
"""