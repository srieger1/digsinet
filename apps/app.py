'''Module for the Application class'''
from abc import ABC, abstractmethod

class Application(ABC):
    '''
    Abstract class for all applications
    
    Attributes:
        None

    Methods:
        __init__(): Constructor
        run(): Run the application
    '''
    def __init__(self):
        '''
        Constructor
        '''

    @abstractmethod
    async def run(self, config: dict, real_topo: dict, sibling_topo: dict, queues: dict, task: dict):
        '''
        Run the application

        Args:
            config (dict): Configuration dictionary
            real_topo (dict): real network topology definition
            sibling_topo (dict): sibling network topology definition
            queues (dict): Dictionary of queues
            task (dict): Task dictionary

        Returns:
            None

        Raises:
            None
        '''
