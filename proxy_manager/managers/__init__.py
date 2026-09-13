"""
Proxy Managers.

This module contains different proxy manager implementations.

Available managers:
- ZoubiProxy: Simple proxy manager using direct API calls
- IndustrialProxy: Advanced proxy manager with validation and pluggable providers
"""

from .zoubi import ZoubiProxy
from .industrial import IndustrialZoubiProxy as IndustrialProxy

__all__ = ["ZoubiProxy", "IndustrialProxy"]
