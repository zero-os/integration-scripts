from js9 import j
import threading

class Benchmark(threading.Thread):
    def __init__(self, address, port):
        threading.Thread.__init__(self)

        self.address = address
        self.port = port

        x = self.address.split('.')
        self.vmname = "node.%s.vm-%02d" % (x[3], port - 1000)
        self._sshclient = None

    def run(self):
        self.sshclient.execute('echo {script} > /tmp/run-benchmark.sh'.format(script=self.script))
        self.sshclient.execute('bash /tmp/run-benchmark.sh')
    
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

fio /root/fiofile-read > /tmp/benchmark-result-read
fio /root/fiofile-write > /tmp/benchmark-result-write
fio /root/fiofile-rand > /tmp/benchmark-result-rand
"""