from dataclasses import dataclass
from typing import List
from .link import Link

@dataclass
class Node:
    name: str
    kind: str
    links: List[Link]
