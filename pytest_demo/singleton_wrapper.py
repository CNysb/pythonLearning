def singleton_wrapper(cls):
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


@singleton_wrapper
class Person:
    def __init__(self, name):
        self.name = name


p1 = Person("Alice")
p2 = Person("Bob")

print(p1 is p2)  # True
