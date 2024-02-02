'''Module for the Application class'''
from abc import ABC, abstractmethod

class Application(ABC):
    '''
    Abstract class for all applications

    Attributes:
        logger (Logger): Logger
        config (dict): Configuration
        real_topo (dict): Real network topology definition

    Methods:
        run: Run the application
    '''

    logger = None

    config = dict()
    real_topo = dict()

    def __init__(self, config: dict, real_topo: dict):
        '''
        Constructor
        '''
        self.logger = config['logger']

        self.config = config
        self.real_topo = real_topo

    @abstractmethod
    async def run(self, topo: dict, queues: dict, task: dict):
        '''
        Run the application

        Args:
            topo (dict): network topology definition (e.g., belonging to a sibling)
            queues (dict): Dictionary of queues
            task (dict): Task dictionary

        Returns:
            None            
        
        Raises:
            None
        '''
