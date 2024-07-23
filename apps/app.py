"""Module for the Application class"""

from abc import ABC, abstractmethod
from logging import Logger
from config import Settings
from event.eventbroker import EventBroker


class Application(ABC):
    """
    Abstract class for all applications

    Attributes:
        logger (Logger): Logger
        config (dict): Configuration
        real_topo (dict): Real network topology definition
        m_logger (Logger): Measurement Logger


    Methods:
        run: Run the application
    """

    logger = None

    config: Settings
    real_topo = dict()

    def __init__(self, config: Settings, real_topo: dict, logger, m_logger: Logger = None, load_increase: int = 0):
        """
        Constructor
        """
        self.logger = logger
        self.m_logger = m_logger

        self.config = config
        self.real_topo = real_topo
        self.load_increase = load_increase

    @abstractmethod
    async def run(self, topo: dict, broker: EventBroker, task: dict):
        """
        Run the application

        Args:
            topo (dict): network topology definition (e.g., belonging to a sibling)
            queues (dict): Dictionary of queues
            task (dict): Task dictionary

        Returns:
            None

        Raises:
            None
        """
