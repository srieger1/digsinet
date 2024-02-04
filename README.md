# DigSiNet

This project implements a proof-of-concept environment to run Network Digital Twins (NDT). It primarily uses [containerlab](https://containerlab.dev/), but can also use other platforms to build, manage and monitor the twins. The concept uses multiple twins that can leverage different platforms, topologies and tools to specifically simulate and emulate only parts of the functionality of the real network. As they only partially share characteristics with the real network and multiple ones can be used an combined, they are called siblings instead of twins. 

# Concept

t.b.w.

* realnet
* siblings
* Controllers
* Builders
* Interfaces
* Apps
* Queues

# Requirements

- Python >=3.10

# Installation

Start by cloning the repo. The prototype contains a sample setup with two Arista cEOS switches. cEOS can be downloaded here: [Arista Support Software Download](https://www.arista.com/en/support/software-download). Import cEOS docker image as described for the corresponding containerlab kind [Arista cEOS](https://containerlab.dev/manual/kinds/ceos/).

Start DigSiNet by running:

```bash
sudo ./digsinet-start.py
```

The example starts digsinet.clab.yml by default to be used as the "real" network topology and two siblings. Each sibling can use an adapted topology and individual tools and platforms different from the real network. See digisinet.yml config file for examples and to change the setup.

Alternatively, a sample using [Nokia SR-Linux](https://containerlab.dev/manual/kinds/srl/) is provided in ```digsinet-srl.yml```. This config can be used by running:

```bash
sudo ./digsinet-start.py --config digsinet-srl.yml
```