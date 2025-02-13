import pytest

from original.Person import Person

p = Person("John", 36)
p1 = Person("John", 31)
p2 = Person("John", 38)


@pytest.mark.parametrize("obj1, obj2, expected", [(p, p1, 0), (p, p2, 1)])
def test_compareAge(obj1, obj2, expected):
    assert obj1.compareAge(obj2) == expected

