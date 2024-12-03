import argparse


__all__ = ["ArgParser"]


class ArgParser:
    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self.action_group = self.parser.add_mutually_exclusive_group()
        self.action_group.add_argument(
            "--start",
            help="Start DigSiNet, "
            "create sibling topologies and run controllers, apps and"
            " interfaces.",
            action="store_true",
            default=True,
        )
        self.action_group.add_argument(
            "--stop",
            help="Stop and remove DigSiNet sibling topologies.",
            action="store_true",
            default=False,
        )
        self.action_group.add_argument(
            "--cleanup",
            help="Forcefully cleanup all sibling topologies.",
            action="store_true",
            default=False,
        )
        self.parser.add_argument(
            "--yes-i-really-mean-it",
            help="Confirm forcefull cleanup",
            action="store_true",
            default=False,
        )
        self.parser.add_argument(
            "--config", help="Config file", default="./digsinet.yml"
        )
        self.parser.add_argument(
            "--reconfigure",
            help="Reconfigure existing containerlab containers",
            action="store_true",
        )
        self.parser.add_argument(
            "--debug", help="Enable debug logging", action="store_true"
        )
        self.parser.add_argument(
            "--task-debug",
            help="Enable task debug logging",
            action="store_true",
        )

    def get_args(self):
        return self.parser.parse_args()
