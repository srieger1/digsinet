===================
Welcome to DigSiNet
===================

DigSiNet is a experimental environment to run `Network Digital Twins <https://datatracker.ietf.org/doc/draft-irtf-nmrg-network-digital-twin-arch/>`_ based primarily on `containerlab <https://containerlab.dev/>`_, with other platforms being worked on. DigSiNet leverages multiple twins that can utilize different network platforms, 
topologies and tools to specifically simulate distinct parts of the real network. In this approach, twins only share partial similarities of the real network and
multiple twins can be combined, hence why they are called *Digital Siblings*.

If you want to play around with DigSiNet, check our :doc:`getting_started` to learn how to setup a local environment. If you are interested in the 
technical details, you can find a section containing the technical details down below.

DigSiNet is still work-in-progress, so expect that some features might be broken or behaving unexpectedly. We try to provide a comprehensive documentation,
but can't guarantee to always be up to date. If you notice something that could be improved, please feel free to open an `Issue`

.. _Issue: https://github.com/srieger1/digsinet/issues

Technical Guide
---------------

Although DigSiNet is a very early implementation of the digital siblings approach,
we try to make our architecture and technical decisions as transparent as possible.
Below here, you can find various documentation regarding our project, from installing it locally
to the overall architecture. We also provide some information about implementation details and 
current shortcomings.

.. toctree::
    :maxdepth: 2

    installation
    getting_started
    design
    limitations
    implementation_reference/index
    contributing
    license
    future_work