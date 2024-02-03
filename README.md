# DigSiNet

This project implements a minimalistic proof-of-concept environment to run Network Digital Twins (NDT). It primarily uses [containerlab](https://containerlab.dev/). The concept uses multiple twins that can use different platforms and topologies to specifically minic and emulate only parts of the functionality of the real network. As they only partially share characteristics with the real network and multiple one can be used an combined, they are called siblings instead of twins. 

# Concept

t.b.w.

* realnet
* siblings
* Controllers
* Builders
* Interfaces
* Apps

# Requirements

- Python >=3.10

# Installation

Start by cloning the repo. The prototype contains a sample setup with two Arista cEOS switches. cEOS can be downloaded here: [Arista Support Software Download](https://www.arista.com/en/support/software-download). Import cEOS docker image as described for the corresponding containerlab kind [Arista cEOS](https://containerlab.dev/manual/kinds/ceos/).

Run DigSiNet be using:

```bash
sudo ./digsinet-start.py
```

The sample starts digsinet.clab.yml to be used as the "real" network topology and three siblings. Each sibling can use adapted topology and individual tools and platforms. See digisinet.yml config file for examples and to change the setup.

Alternatively, a sample using [Nokia SR-Linux](https://containerlab.dev/manual/kinds/srl/) is provided in ```digsinet-srl.yml```. This config can be used by running:

```bash
sudo ./digsinet-start.py --config digsinet-srl.yml
```