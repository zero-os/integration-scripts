# integration-scripts
integration and performance testing for zero-os

## installation
clone this repo in $codedir/github/zero-os/integration-scripts
install using pip3 like this 
```bash
cd $codedir/github/zero-os/integration-scripts
pip3 install -e .
```

## examples
```python
j.tools.benchmark.test()
# (OR)
client = j.tools.benchmark.get('test')
client.reboot()
client.prepare()
```