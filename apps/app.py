"""Module for the Application class"""

from abc import ABC, abstractmethod
from config import Settings
from event.eventbroker import EventBroker


class Application(ABC):
    """
    Abstract class for all applications

    Attributes:
        logger (Logger): Logger
        config (dict): Configuration
        real_topo (dict): Real network topology definition

    Methods:
        run: Run the application
    """

    logger = None

    config: Settings
    real_topo = dict()

    def __init__(self, config: Settings, real_topo: dict, logger):
        """
        Constructor
        """
        self.logger = logger

        self.config = config
        self.real_topo = real_topo

    @abstractmethod
    async def run(self, topo: dict, broker: EventBroker, task: dict):
        """
        Run the application

        Args:
            topo (dict): network topology definition
             (e.g., belonging to a sibling)
            broker (dict): Dictionary of queues
            task (dict): Task dictionary

        Returns:
            None

        Raises:
            None
        """
