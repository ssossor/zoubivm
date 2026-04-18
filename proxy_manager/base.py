from abc import ABC, abstractmethod
import logging
import asyncio

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s'
)
logger = logging.getLogger("proxy_manager")

class BaseProxyManager(ABC):
    def __init__(self):
        self.lock = asyncio.Lock()
        self.proxies = []
        self.current_proxy = None
        self.logger = logging.getLogger(f"proxy_manager.{self.__class__.__name__}")

    @abstractmethod
    async def get_proxies(self):
        """Récupère une nouvelle liste de proxies et défini le current_proxy."""
        pass

    @abstractmethod
    async def rotate(self,):
        """Passe au proxy suivant dans la liste."""
        pass

    def get_current_proxy(self):
        """Retourne le proxy actuellement utilisé."""
        return self.current_proxy
