"""gNMI interface"""

from event.eventbroker import EventBroker
from interfaces.interface import Interface
from config import Settings, InterfaceSettings, InterfaceCredentials

import re
import copy

from multiprocessing import Queue, Semaphore
from pygnmi.client import gNMIclient
from deepdiff import DeepDiff, grep


class gnmi(Interface):
    """
    gNMI interface
    """

    port = None
    username = None
    password = None

    target_topo = None

    config: Settings
    interface_config: InterfaceCredentials
    topology_interface_config: InterfaceSettings
    toplogy_prefix: str

    hostWriteSemaphores = dict[Semaphore]()

    def __init__(
        self,
        config: Settings,
        target_topology: str,
        logger,
        topology_prefix: str,
        topology_name: str,
    ):
        """
        Constructor
        """
        super().__init__(
            config, target_topology, logger, topology_prefix, topology_name
        )

        self.port = config.interface_credentials.get("gnmi").port
        self.username = config.interface_credentials.get("gnmi").username
        self.password = config.interface_credentials.get("gnmi").password

        self.target_topo = target_topology
        self.config = config

        if config.interface_credentials.get("gnmi") is not None:
            self.interface_config = config.interface_credentials.get("gnmi")

        self.topology_interface_config = super().getTopologyInterfaceConfig(
            target_topology
        )
        self.topology_prefix = topology_prefix

    def _checkNode(self, nodes, node_name):
        """
        Check if the node exists in the model and
        if it matches the regex defined in
        the gnmi-sync config for the siblings
        return its hostname.

        :param nodes: The model of the network topology.
        :param node_name: The name of the node.
        :return: The hostname of the node or None
        if node does not exist or should not be updated.

        """
        # if the gNMI data for the node's name exists in the model
        if nodes is not None and len(nodes) > 0 and nodes.get(node_name) is not None:
            # if the node matches the regex
            # defined in the gnmi-sync config for the siblings
            if re.fullmatch(self.topology_interface_config.nodes, node_name):
                # TODO: hostname is still limited to
                #  containerlab syntax (clab_prefix-topology_name-node_name)
                if self.target_topo == "realnet":
                    host = (
                        self.topology_prefix
                        + "-"
                        + self.topology_name
                        + "-"
                        + node_name
                    )
                else:
                    host = (
                        self.topology_prefix
                        + "-"
                        + self.topology_name
                        + "_"
                        + self.target_topo
                        + "-"
                        + node_name
                    )

                if self.hostWriteSemaphores.get(host) is None:
                    self.hostWriteSemaphores[host] = Semaphore(1)

                return host

    # TODO: remove queues parameter
    def getNodesUpdate(
        self,
        nodes: dict,
        queues: dict[Queue],
        broker: EventBroker,
        diff: bool = False,
    ):
        """
        Get gNMI data from the real network.

        :param nodes: The model of the network topology.
        :param queues: The queues to send the updates to.
        :param broker: The event broker to send the updates to.
        :param diff: Whether to calculate and only
        report back differential data or not.
        :return: The updated model of the network topology nodes' paths.

        """
        if nodes is not None and len(nodes) > 0:
            for node in nodes:
                use_diff = "differential" if diff else ""
                self.logger.debug(
                    f"<-- Getting {use_diff} gNMI data " f"from {self.target_topo}..."
                )
                host = self._checkNode(nodes, node)
                if host is not None:
                    try:
                        with gNMIclient(
                            target=(host, self.port),
                            username=self.username,
                            password=self.password,
                            insecure=True,
                        ) as gc:
                            for path in self.topology_interface_config.paths:
                                if diff is True:
                                    nodes[node] = self._process_diff(
                                        node, path, nodes[node], gc, broker
                                    )
                                else:
                                    nodes[node] = self._process_no_diff(
                                        node, path, nodes[node], gc, broker
                                    )
                    except Exception as e:
                        self.logger.error(
                            f"Error getting gNMI data from {host}"
                            f" in topology {self.target_topo}: {str(e)}"
                        )
        else:
            self.logger.warning(
                f"Warning: No nodes to get gNMI data"
                f" from in topology {self.target_topo}..."
            )
        return nodes

    def _process_diff(self, node, path, node_paths, gc, broker: EventBroker):
        if node_paths.get(path) is not None:
            old_node_path_data = copy.deepcopy(node_paths[path])
        else:
            old_node_path_data = None
        node_path_data = gc.get(
            path=[path], datatype=self.topology_interface_config.datatype
        )
        node_paths[path] = copy.deepcopy(node_path_data)
        diff = self._calculate_diff(old_node_path_data, node_path_data)
        self._send_update_to_queues(node, path, node_path_data, diff, broker)
        return node_paths

    def _process_no_diff(self, node, path, node_paths, gc, broker: EventBroker):
        node_path_data = gc.get(
            path=[path], datatype=self.topology_interface_config.datatype
        )
        node_paths[path] = copy.deepcopy(node_path_data)
        self._send_update_to_queues(node, path, node_path_data, None, broker)
        return node_paths

    def _calculate_diff(self, old_data, new_data):
        # TODO evaluate gNMIclient show_diff?
        if new_data | grep("Hello World! update for node"):
            # if the new data contains the "Hello World! update
            # for node" string, return an empty diff
            # this excludes hello_world app updates from the diff
            return {}

        node_data_diff = DeepDiff(
            old_data,
            new_data,
            ignore_order=True,
            exclude_regex_paths="\\['timestamp'\\]",
        )
        return node_data_diff.tree

    def _send_update_to_queues(self, node, path, node_data, diff, broker: EventBroker):
        # if differential data exists and is empty
        # don't send updates the queues
        if diff is not None and len(diff) > 0:
            for channel in broker.get_sibling_channels():
                broker.publish(
                    channel,
                    {
                        "type": "gNMI notification",
                        "source": self.target_topo,
                        "node": node,
                        "path": path,
                        "data": node_data,
                        "diff": diff,
                    },
                )

    def setNodeUpdate(
        self, nodes: dict, node_name: str, path: str, notification_data: dict
    ):
        host = self._checkNode(nodes, node_name)

        if host is not None:
            self.logger.debug(
                f"--> Syncing gNMI data to node "
                f"{node_name} in topology {self.target_topo}: "
                f"{str(notification_data)}..."
            )
            try:
                with gNMIclient(
                    target=(host, self.port),
                    username=self.username,
                    password=self.password,
                    insecure=True,
                ) as gc:
                    # for each notification in the notification data
                    for notification in notification_data["notification"]:
                        # if the notification is an update
                        if notification.get("update"):
                            for update in notification["update"]:
                                self.hostWriteSemaphores[host].acquire()
                                # turn update to replace,
                                # pygnmi get delivers updates,
                                # but updating, e.g.
                                # ip address in interface config
                                # requires replacing it
                                # otherwise we get gRPC errors
                                result = gc.set(
                                    replace=[(str(path), dict(update["val"]))]
                                )
                                self.hostWriteSemaphores[host].release()
                                self.logger.debug("gNMI set result: " + str(result))
                        else:
                            self.logger.info(
                                "Unsupported gNMI notification type: "
                                + str(notification)
                            )
            except Exception as e:
                self.logger.error(
                    f"Error syncing gNMI data to {host} "
                    f"in topology {self.target_topo}: {str(e)}"
                )

    def set(self, nodes: dict, node_name: str, op: str, data: dict):
        host = self._checkNode(nodes, node_name)

        if host is not None:
            self.logger.debug(
                f"--> Setting gNMI data on node {node_name} "
                f"in topology {self.target_topo}: {str(data)}..."
            )
            try:
                with gNMIclient(
                    target=(host, self.port),
                    username=self.username,
                    password=self.password,
                    insecure=True,
                ) as gc:
                    # for each notification in the notification data
                    self.hostWriteSemaphores[host].acquire()
                    match op:
                        case "update":
                            result = gc.set(update=data)
                        case "replace":
                            result = gc.set(replace=data)
                        case "delete":
                            result = gc.set(delete=data)
                        case _:
                            raise Exception("Unsupported gNMI operation: " + op)
                    self.hostWriteSemaphores[host].release()
                    self.logger.debug("gNMI set result: " + str(result))
            except Exception as e:
                self.logger.error(
                    f"Error setting gNMI data on {host}"
                    f" in topology {self.target_topo}: {str(e)}"
                )
