Configuration
=============
DigSiNet consumes a configuration file. If no arguments are provided, it looks for a file called
digsinet.yml. This default can be overriden by using the --config flag. You can find a sample configuration 
file in the repository.

Structure
-----------
.. code-block:: yaml

    name: toplogy-name
    # Configure a network topology representing a "real network". Used in testing
    topology:
        type: containerlab
        # File containing the container lab topology
        file: ./digsinet.clab.yml
    # Interval in which to sync / poll for topology changes in seconds
    interval: 1
    # Timeout for the initial sibling creation
    create_sibling_timeout: 60

    realnet:
        apps:
        # Interfaces to use for querying the toplogy
        interfaces:
        # Use gNMI to query for topology information. Could also be another interface type later in development
        gnmi:
            # The name pattern for gNMI to find nodes
            nodes: "ceos(.*)"
            # The type of data to query
            datatype: "config"
            # paths to monitor with gNMI
            paths: 
                - "openconfig:interfaces/interface[name=Ethernet1]"
            # Prefix to strip from the paths
            strip:
                - "openconfig:interfaces/interface[name=Management0]"

    # The Siblings that DigSiNet should create
    siblings:
        # Name of the sibling, should be a descriptive name. Can be repeated as often as needed
        sibling1:

        # Toplogy Adjustments - Siblings can be run on a modified topology.
            topology-adjustments:
                # Removes the node with the name 'ceos2'
                node-remove: "ceos2"
                # Add a node
                node-add:
                    # With name "ceos3"
                    ceos3:
                        # As a cEOS node
                        kind: ceos
                        # based on this image
                        image: ceos:latest
            # Add a link between nodes by specifying nodename:interfacename
            link-add:
                - endpoints: ["ceos1:eth1", "ceos3:eth1"]

    # Controllers that DigSiNet should use
    controllers:
        # Name of the Controller
        controller1:
            # Module containing controller logic. This value would look in controllers/c1.py for the controller logic
            module: "controllers.c1"
            # The builder to use, as specified in the builder section below
            builder: "containerlab"
            # Interfaces to use for communication
            interfaces:
                - gnmi
            # Applications that are associated with this builder
            apps:
                - ci
    
    # Topology builders that are available
    builders:
        # "Name of the builder"
        containerlab:
            # Path to the module containing the builder logic. This would look in builders/containerlab.py
            module: "builders.containerlab"
    
    # Available interfaces for information exchange
    interfaces:
        # Name of the interface
        gnmi:
            # Module containing the interface logic. This would look in interfaces/gnmi.py for the interface logic
            module: "interfaces.gnmi"
            # gNMI port to use
            port: 6030
            # Username to authenticate against network device
            username: "admin"
            # Password to authenticate against network device
            password: "admin"

    # Applications to run in the current setup
    apps:
        # Name of the application
        app1:
            # Module containing the Application code. This would look in apps/app1.py.
            module: "apps/app1"