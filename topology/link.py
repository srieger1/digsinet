from dataclasses import dataclass

@dataclass
class Link:
    name_from: str
    name_to: str
    interface_from: str
    interface_to: str