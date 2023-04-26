"""
Gets whether the system is currently frozen
"""
import sys


def frozen():
    """
    Returns if the system is frozen
    """
    return getattr(sys, "frozen", False)
