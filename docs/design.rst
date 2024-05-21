Design
======
DigSiNet follows a modular design, consisting of three main parts:

* Controllers
* Interfaces
* Applications

Interfaces
------------
Interfaces sit between controllers and the real network and are responsible for retrieving and manipulating information
from on the real network. DigSiNet is using gNMI as the primary communication protocol, but implementing
other protocols is possible by subclassing the Interface class in interfaces/.

Controllers
------------
Controllers translate an abstract, declarative specification of a real network into a suitable topology
for a given network emulation tool. Currently, DigSiNet only supports topologies in Containerlab, but implementing
other network emulators is possible via the exposed topology builders in builders/.

Applications
--------------
Applications can consume information from one or multiple siblings to gain insights on the network.
They are also able to leverage gNMI to perform changes on the real network based on insights gained over siblings.
An interface for writing custom applications is provided in apps/.