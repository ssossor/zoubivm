"""
Clients module for zoubivm project.

This module contains all the API clients for different platforms.

Available clients:
- RootMeClient: Client for RootMe API with proxy support
"""

from .rootme import RootMeClient
from .utils import RootMeApiError, RootMeRateLimitError, describe_error

__all__ = [
    "RootMeClient",
    "RootMeApiError", 
    "RootMeRateLimitError",
    "describe_error",
]
