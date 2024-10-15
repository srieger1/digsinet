"""
Configuration Settings for DigSiNet.

The classes in this module define the structure of the
Configuration file used by DigSiNet.
"""

from dataclasses import dataclass
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from config.kafka import KafkaSettings
from config.rabbit import RabbitSettings
import yaml


class TopologyType(BaseModel):
    """
    Specifies the Topology Type to use.

    Attributes:
        type (str): The topology type.
        Currently only Containerlab is available.
        file (str): The path to the file containing the topology definition.
    """

    type: str
    file: str


@dataclass
class TopologyAdjustmentRemove(BaseModel):
    """
    Topology Adjustment that removes a node from the topology

    Attributes:
        node_name (str): The name of the node to remove.
    """

    node_name: str = Field(..., alias="node-name")


@dataclass
class TopologyAdjustmentAdd(BaseModel):
    """
    Topology Adjustment that adds a node to the topology.

    Attributes:
        kind (str): The kind of node, for example cEOS or SRLinux.
        image (str): The name of the container image to use.
    """

    kind: str
    image: str


@dataclass
class TopologyAdjustmentAddLink(BaseModel):
    """
    Topology Adjustment that adds a link between nodes to the topology.

    Attributes:
        node_source (str): source node
        node_destination (str): destination node
    """

    node_source: str
    node_destination: str


@dataclass
class TopologyAdjustmentRemoveLink(BaseModel):
    """
    Topology Adjustment that removes a link between nodes to the topology.

    Attributes:
        node_source (str): source node
        node_destination (str): destination node
    """

    node_source: str
    node_destination: str


class InterfaceSettings(BaseModel):
    """
    Interface settings that specify what data should be polled

    Attributes:
        nodes (str): Regex specifying what nodes to poll
        datatype (str): what type of data to poll
        paths (List[str]): gNMI paths to watch
        strip (List[str]): a common prefix to strip from gnmi paths
    """

    nodes: str
    datatype: str
    paths: List[str]
    strip: List[str]


class RealnetSettings(BaseModel):
    """
    Settings for the physical network to create digital siblings from.

    Attributes:
        apps (Optional[List[str]]): applications running for the realnet.
        interfaces (Dict[str, InterfaceSettings]):
         interface settings for the realnet
    """

    apps: Optional[List[str]]
    interfaces: Dict[str, InterfaceSettings]


class TopologyAdjustment(BaseModel):
    """
    Represents all possible topology adjustments
     that a sibling can make to the realnet.
    """

    node_remove: Optional[TopologyAdjustmentRemove] = Field(
        alias="node-remove", default=None
    )
    node_add: Optional[Dict[str, TopologyAdjustmentAdd]] = Field(
        alias="node-add", default=None
    )
    link_remove: Optional[List[TopologyAdjustmentRemoveLink]] = Field(
        alias="link-remove", default=None
    )
    link_add: Optional[List[TopologyAdjustmentAddLink]] = Field(
        alias="link-remove", default=None
    )


class SiblingSettings(BaseModel):
    """
    Settings specifying how a digital sibling should operate.

    Attributes:
        topology_adjustments (Optional[TopologyAdjustment]):
        adjustments the sibling does to the realnet.
        interfaces (Dict[str, InterfaceSettings]):
        interfaces for the sibling to use
        controller (str): controller assigned to this sibling
        autostart (bool): whether to autostart this sibling
    """

    topology_adjustments: Optional[TopologyAdjustment] = Field(
        ..., alias="topology-adjustments"
    )
    interfaces: Dict[str, InterfaceSettings]
    controller: str
    autostart: bool


class ControllerSettings(BaseModel):
    """
    Settings specifying how a sibling controller should operate.

    Attributes:
        module (str): module containing the controller logic
        builder (str): name of the builder for the controller to use
        interfaces (List[str]): interfaces available to the controller
        apps (List[str]): applications associated with this controller
    """

    module: str
    builder: str
    interfaces: List[str]
    apps: List[str]


class BuilderSettings(BaseModel):
    """
    Settings for toplogy builders

    Attributes:
        module (str): module name where the builder logic is located
    """

    module: str


class InterfaceCredentials(BaseModel):
    """
    Credentials for a network interface

    Attributes:
        module (str): module name where the interface logis is located
        port (int): network port number for the interface
        username (str): username for authentication
        password (str): password for authentication
    """

    module: str
    port: int
    username: str
    password: str


class AppSettings(BaseModel):
    """
    Configuration for apps

    Attributes:
        module (str): module where app logic is located
    """

    module: str


class Settings(BaseModel):
    """
    Main Settings class.
    Contains all possible configuration options for DigSiNet.

    Attributes:
        topology_name (str): name of the topology.
        topology (TopologyType): Type of topology.
        sync_interval (int):
        synchronization interval in milliseconds.
        sibling_timeout (int):
        timeout for siblings in milliseconds.
        realnet (RealnetSettings):
        Settings for the realnet.
        siblings (Dict[str, SiblingSettings]):
        Settings for the individual siblings grouped by name.
        controllers (Dict[str, ControllerSettings]):
        Settings for the controllers, grouped by controller name.
        builders (Dict[str, BuilderSettings]):
        Settings for the builders, grouped by builder name.
        interface_credentials (Dict[str, InterfaceCredentials]):
        Credential data for interfaces, grouped by name.
        apps (Dict[str, AppSettings]):
        Configuration for applications, grouped by app name.
    """

    topology_name: str = Field(..., alias="name")
    topology: TopologyType
    sync_interval: int = Field(..., alias="interval")
    sibling_timeout: int = Field(..., alias="create_sibling_timeout")
    realnet: RealnetSettings
    siblings: Dict[str, SiblingSettings]
    controllers: Dict[str, ControllerSettings]
    builders: Dict[str, BuilderSettings]
    interface_credentials: Dict[str, InterfaceCredentials] = Field(
        ..., alias="interfaces"
    )
    apps: Dict[str, AppSettings]
    kafka: Optional[KafkaSettings] = None
    rabbit: Optional[RabbitSettings] = None


def read_config(config_file: str) -> Settings:
    """
    Reads the config file and tries to parse it into Settings,
    throwing errors if the format is not as specified.
    """
    with open(config_file) as file:
        data = yaml.safe_load(file)
        config = Settings(**data)
        if validate_config(config):
            return config
        else:
            raise Exception(
                "configuration error: "
                "either kafka or rabbitmq settings must be provided"
            )


def validate_config(config: Settings) -> bool:
    if config.kafka is None and config.rabbit is None:
        return False
    else:
        return True
