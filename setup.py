from setuptools import setup
from setuptools.command.install import install as _install
from setuptools.command.develop import develop as _develop
import os 
def _post_install(libname, libpath):
    from js9 import j
    # add this plugin to the config
    c = j.core.state.configGet('plugins', defval={})
    c[libname] = "%s/github/zero-os/integration-scripts/JumpScale9Benchmark" % j.dirs.CODEDIR
    j.core.state.configSet('plugins', c)
    j.tools.jsloader.generate()


class install(_install):

    def run(self):
        _install.run(self)
        libname = self.config_vars['dist_name']
        libpath = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), libname)
        self.execute(_post_install, (libname, libpath),
                     msg="Running post install task")

class develop(_develop):

    def run(self):
        _develop.run(self)
        libname = self.config_vars['dist_name']
        libpath = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), libname)
        self.execute(_post_install, (libname, libpath),
                     msg="Running post install task")

setup(
    name='JumpScale9Benchmark',
    version='1.0.0',
    description='Benchmark tool for zeroos',
    url='https://github.com/zero-os/integration-scripts',
    author='GreenItGlobe',
    author_email='info@gig.tech',
    license='Apache',
    
    cmdclass={
        'install': install,
        'develop': develop,
    },
)
