from dataclasses import dataclass
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Union
import yaml


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
    nodes: str
    datatype: str
    paths: List[str]
    strip: List[str]


class RealnetSettings(BaseModel):
    apps: Optional[List[str]]
    interfaces: Dict[str, InterfaceSettings]


class SiblingSettings(BaseModel):
    # topology_adjustments: Optional[Dict[str, Union[TopologyAdjustmentAdd, TopologyAdjustmentRemove]]] = Field(..., alias='topology-adjustments')
    interfaces: Dict[str, InterfaceSettings]
    controller: str
    autostart: bool


class ControllerSettings(BaseModel):
    module: str
    builder: str
    interfaces: List[str]
    apps: List[str]


class BuilderSettings(BaseModel):
    module: str


class InterfaceCredentials(BaseModel):
    module: str
    port: int
    username: str
    password: str


class AppSettings(BaseModel):
    module: str


class Settings(BaseModel):
    topology_name: str = Field(..., alias='name')
    topology: TopologyType
    sync_interval: int = Field(..., alias='interval')
    sibling_timeout: int = Field(..., alias='create_sibling_timeout')
    realnet: RealnetSettings
    siblings: Dict[str, SiblingSettings]
    controllers: Dict[str, ControllerSettings]
    builders: Dict[str, BuilderSettings]
    interface_credentials: dict[str, InterfaceCredentials] = Field(..., alias='interfaces')
    apps: Dict[str, AppSettings]


def read_config(config_file: str) -> Settings:
    with open(config_file) as file:
        data = yaml.safe_load(file)
        return Settings(**data)


if __name__ == '__main__':
    settings = read_config('digsinet.yml')
    print(settings)
