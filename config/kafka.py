from enum import Enum
from pydantic import BaseModel


class OffsetResetType(str, Enum):
    """
    Enum for Offset Reset Type
    Only works for new consumer groups,
    otherwise will use the last committed offset

    Attributes:
        EARLIEST (str): earliest offset (beginning of the topic)
        LATEST (str): latest offset (end of the topic)
    """

    EARLIEST = "earliest"
    LATEST = "latest"


class TopicsConfig(BaseModel):
    """
    Configuration for Kafka Topics

    Attributes:
        num_partitions (int): number of partitions
        replication_factor (int): replication factor
    """

    num_partitions: int
    replication_factor: int


class OffsetConfig(BaseModel):
    """
    Configuration for Kafka Offset

    Attributes:
        resetType (OffsetResetType): type of offset reset
    """

    reset_type: OffsetResetType


class KafkaSettings(BaseModel):
    """
    Configuration for Kafka

    Attributes:
        host (str): host of the Kafka server
        port (int): port of the Kafka server
        topics (TopicsConfig): configuration for Kafka topics
        offset (OffsetConfig): configuration for Kafka offsets
    """

    host: str
    port: int
    topics: TopicsConfig
    offset: OffsetConfig

    class Config:
        use_enum_values = True
