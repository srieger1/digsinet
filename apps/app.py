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
    async def run(self, config, clab_topology_definition, sibling, sibling_clab_topo, real_nodes,
            queues, task):
        '''
        Run the application

        Args:
            config (dict): Configuration dictionary
            clab_topology_definition (dict): clab topology definition
            sibling (str): Name of sibling
            sibling_clab_topo (dict): clab topology definition of sibling
            real_nodes (dict): Dictionary of real nodes
            queues (dict): Dictionary of queues
            task (dict): Task dictionary

        Returns:
            None

        Raises:
            None
        '''
