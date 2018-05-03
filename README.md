# integration-scripts
Integration and performance testing for Zero-OS

# Requirements
- At least one node running Zero-OS
- Your nodes needs to runs in `development` mode
- You don't **necessary** need zerotier network if you can reach nodes locally
- Have some time, benchmark can take more than 15 min
- Jumpscale

## Installation
Clone this repo in `$codedir/github/zero-os/integration-scripts`

Install it using `pip3`:
```bash
cd $codedir/github/zero-os/integration-scripts
pip3 install -e .
```

# Configuration
This module uses the Jumpscale Configuration Manager.
[More information about configuration]

## Examples
Running the full cycle test (reboot, prepare node, setup vm, run tests, summary)
```python
j.tools.benchmark.test()
```

Or do steps separatly:
```
client = j.tools.benchmark.get('test')
client.reboot()
client.prepare()
...
```
