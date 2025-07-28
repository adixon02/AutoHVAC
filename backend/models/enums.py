"""
Enums for AutoHVAC models to ensure type safety and consistency
"""

from enum import Enum


class DuctConfig(str, Enum):
    """Duct configuration options for Manual J calculations"""
    ducted_attic = 'ducted_attic'
    ducted_crawl = 'ducted_crawl'
    ductless = 'ductless'


class HeatingFuel(str, Enum):
    """Heating fuel type options for HVAC equipment recommendations"""
    gas = 'gas'
    heat_pump = 'heat_pump'
    electric = 'electric'