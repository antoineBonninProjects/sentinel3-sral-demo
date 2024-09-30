"""
This module defines the SingletonMeta metaclass for implementing the Singleton design pattern.
This is not a thread safe implementation.

Usage:
    To make any class a Singleton, define it as follows:
    
    class MyClass(metaclass=SingletonMeta):
        # class implementation

Classes:
    SingletonMeta -- Metaclass to enforce the Singleton pattern.
"""

__all__ = ['SingletonMeta']


class SingletonMeta(type):
    """
    Metaclass to make Singletons.

    To make any class a Singleton:
    > MyClass(metaclass=SingletonMeta):
          # class implem
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        """
        Possible changes to the value of the `__init__` argument do not affect
        the returned instance.
        """
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]
