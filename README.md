# DigSiNet

This project implements a proof-of-concept environment to run Network Digital Twins (NDT). It primarily uses [containerlab](https://containerlab.dev/), but can also use other platforms to build, manage and monitor the twins. The concept uses multiple twins that can leverage different platforms, topologies and tools to specifically simulate and emulate only parts of the functionality of the real network. As they only partially share characteristics with the real network and multiple ones can be used an combined with each sibling using a different platform being well-suited for its purpose, they are called siblings instead of twins. 

# Concept

DigSiNet's architecture currently consists of the following components: 

* Realnet
* Siblings
* Controllers
* Builders
* Interfaces
* Apps
* Queues

Details regarding the architecture and its components are also described in the working-draft of the documentation [https://srieger1.github.io/digsinet/](https://srieger1.github.io/digsinet/) and were published and presented in our paper at NOMS 2024-2024 IEEE Network Operations and Management Symposium [https://ieeexplore.ieee.org/document/10575632](https://ieeexplore.ieee.org/document/10575632). As DigSiNet is currently being used as a proof-of-concept to run NDT experiments, its architecture and compoments are still subject to change, as can also be observed from the current development branches [https://github.com/srieger1/digsinet/branches](https://github.com/srieger1/digsinet/branches).

# Requirements

- Python >=3.10
- [containerlab](https://containerlab.dev/)

# Installation

Easiest option to install and develop the project is to use the provided dev container in vscode.

Start by cloning the repo. The prototype contains a sample setup with two Arista cEOS switches. cEOS can be downloaded here: [Arista Support Software Download](https://www.arista.com/en/support/software-download). Import cEOS docker image as described for the corresponding containerlab kind [Arista cEOS](https://containerlab.dev/manual/kinds/ceos/).

Start DigSiNet by running:

```bash
sudo ./digsinet.py
```

The example starts digsinet.clab.yml by default to be used as the "real" network topology and two siblings. Each sibling can use an adapted topology and individual tools and platforms different from the real network. See digisinet.yml config file for examples and to change the setup.

Alternatively, a sample using [Nokia SR-Linux](https://containerlab.dev/manual/kinds/srl/) is provided in ```digsinet-srl.yml```. This config can be used by running:

```bash
sudo ./digsinet.py --config digsinet-srl.yml
```
