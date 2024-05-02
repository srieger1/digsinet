Installation
============

Python Version
--------------
DigSiNet requires that you use a Python version that is greater or equal to 
version 3.10. Please refer to the `Python Documentation` in order to install a 
compatible version.

.. _Python Documentation: https://www.python.org/downloads

Dependencies
------------
Before installing DigSiNet, make sure that you provide all necessary dependencies.
At the current point of writing, the Dependencies are:

* `Docker`_ DigSiNet currently uses containerized network operating systems for Siblings.
* `Containerlab`_ Provides a CLI for orchestrating and managing container based networking labs. DigSiNet uses containerlab to build Siblings.

.. _Docker: https://docs.docker.com/get-docker/
.. _Containerlab: https://containerlab.dev/install/

Optional Dependencies
---------------------
Dependencies here are not necessary for running DigSiNet, but 
may allow to run more of the provided examples. This is because some examples
rely on container images that are not publicly available, but you can usually retrieve them
yourself.

* `Arista cEOS Container Image`_ Some examples use cEOS from Arista. The container image is not publicly available, but you can create an account at Arista and download it from there.

.. _Arista cEOS Container Image: https://www.arista.com/en/login

Virtual Environments
--------------------
We recommend using a virtual environment (venv) to manage the package
dependencies of DigSiNet. Virtual environments greatly simplify dealing with
python dependencies by providing an isolated group of python packages specifically for
one application.

Fortunately, Python comes with the functionality to create virtual environments
by default.

.. _install_create_venv:

Create venv
~~~~~~~~~~~
Create a folder for DigSiNet and initialize a new virtual environment in it:

.. tabs::

    .. group-tab:: Linux/macOS

        .. code-block:: text

            $ mkdir digsinet
            $ cd digsinet
            $ python3 -m venv .venv


.. _install-activate-venv:

Activate venc
~~~~~~~~~~~~~
Before we can continue with the installation, we need to explicitly
activate the previously created virtual environment:

.. tabs::

    .. group-tab:: Linux/macOS

        .. code-block:: text
            
            $ source .venv/bin/activate

You will see that the virtual environment is activated by 
looking at your command prompt.

Install DigSiNet
~~~~~~~~~~~~~~~~
You will need to clone the DigSiNet repository from GitHub:

.. tabs::

    .. group-tab:: Linux/macOS

        .. code-block:: text

            $ git clone https://github.com/srieger1/digsinet .

After you have successfully cloned the repository, you can install 
required packages:

.. tabs::

    .. group-tab:: Linux/macOS

        .. code-block:: text

            $ pip install -r ./requirements.txt

You are now ready to run DigSiNet. We provide some example configurations to play
around with. You can find more information in our :doc:`getting_started`.
            