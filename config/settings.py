from dataclasses import dataclass
from pydantic import BaseModel
from typing import List


class TopologyType(BaseModel):
    type: str
    file: str


@dataclass
class TopologyAdjustmentRemove(BaseModel):
    node_name: str


@dataclass
class TopologyAdjustmentAdd(BaseModel):
    node_name: str
    kind: str
    image: str


@dataclass
class TopologyAdjustmentAddLink(BaseModel):
    node_source: str
    node_destination: str


@dataclass
class TopologyAdjustmentRemoveLink(BaseModel):
    node_source: str
    node_destination: str


TopologyAdjustment = (TopologyAdjustmentAdd | TopologyAdjustmentRemove | TopologyAdjustmentAddLink |
                      TopologyAdjustmentRemove)


class InterfaceSettings(BaseModel):
    name: str
    nodes: str
    datatype: str
    paths: List[str]
    strip: List[str]


class RealnetSettings(BaseModel):
    apps: List[str]
    interfaces: List[InterfaceSettings]


class SiblingSettings(BaseModel):
    name: str
    topology_adjustments: List[TopologyAdjustment]
    interfaces: List[InterfaceSettings]
    controller: str
    autostart: bool


class ControllerSettings(BaseModel):
    name: str
    module: str
    builder: str
    interfaces: List[str]
    apps: List[str]


class BuilderSettings(BaseModel):
    module: str


class InterfaceCredentials(BaseModel):
    name: str
    module: str
    port: int
    username: str
    password: str


class AppSettings(BaseModel):
    name: str
    module: str


class Settings(BaseModel):
    topology_name: str
    topology_type: TopologyType
    sync_interval: int
    sibling_timeout: int
    realnet: RealnetSettings
    siblings: List[SiblingSettings]
    controllers: List[ControllerSettings]
    builders: List[BuilderSettings]
    interface_credentials: List[InterfaceCredentials]
    apps: List[AppSettings]




