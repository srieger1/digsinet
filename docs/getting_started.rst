Getting Started 
===============
This page highlights some examples that we provide to try out DigSiNet.
We currently have two working examples: One that uses Nokia SR-Linux and one
using Arista cEOS. The latter one requires that you have a container image for
cEOS locally available. Please refer to the section :doc:`installation` for instructions
on how to obtain an image for cEOS.

At the time of writing, DigSiNet unfortunately requires to be run as root. This is because
containerlab, being a dependeny of DigSiNet to build the sibling topologies, also requires root permissions.

If you want to customize the configuration, you can refer to :doc:`configuration`.

Running the cEOS sample
-----------------------
From the root of the DigSiNet directory, simply run the following command:

.. tabs::

    .. group-tab:: Linux/macOS

        .. code-blocK:: text

            $ sudo ./digsinet.py 

Per default, DigSiNet looks for a file called *digsinet.yml* that contains the configuration.

Running the SR-Linux sample
---------------------------
You can override the location of the configuration file:

.. tabs::

    .. group-tab:: Linux/macOS

        .. code-blocK:: text

            $ sudo ./digsinet.py --config digsinet-srl.yml
