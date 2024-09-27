# pylint: skip-file
"""
Test for module utils.singleton
"""

import pytest
import threading

from utils.singleton import SingletonMeta


class SingletonClass(metaclass=SingletonMeta):
    def __init__(self, value):
        self.value = value


@pytest.fixture(scope="module", autouse=True)
def reset_singleton_instances():
    """
    Fixture to reset singleton instances between tests.
    """
    SingletonMeta._instances.clear()


def test_singleton_instance():
    """
    Test that multiple instantiations return the same instance.
    """
    instance1 = SingletonClass(10)
    instance2 = SingletonClass(20)

    assert instance1 is instance2
    assert instance1.value == 10
    assert instance2.value == 10


def test_multiple_singletons_with_different_classes():
    """
    Test that different singleton classes are independent.
    """

    class AnotherSingleton(metaclass=SingletonMeta):
        pass

    instance1 = SingletonClass(50)
    instance2 = AnotherSingleton()
    instance3 = AnotherSingleton()

    assert instance1 is not instance2
    assert instance2 is instance3
