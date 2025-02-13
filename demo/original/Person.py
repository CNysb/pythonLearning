from typing import Literal

from tests.extensions.injection.test_add_dependency import Person


class Person:
    def __init__(self, name: str, age: int) -> None:
        self.name = name
        self.age = age

    def say(self):
        print(f"{self.name} is {self.age} years old")

    def compareAge(self, other: Person) -> int:
        return 1 if other.age >= self.age else 0
