from mock import Mock

from transtycoon import exceptions
from transtycoon.report import get_logger


class Field:

    def __init__(self, position, resources, name=None):
        self.position = position
        self.resources = resources
        self.name = name or "Field"

    def __repr__(self):
        return "{} (resources = {} position = {}".format(self.name, self.resources, self.position)


class Warehouse:

    # Capacity = None means unlimited capacity
    def __init__(self, position, capacity=None, name=None):
        self.position = position
        self.capacity = capacity
        self.name = name or "Warehouse"

        self.resources = 0

    def __repr__(self):
        return "{} (resources = {} position = {}".format(self.name, self.resources, self.position)

    def has_free_space(self):
        if self.capacity is None:
            return True

        if self.get_free_capacity() > 0:
            return True

        return False

    def get_free_capacity(self):
        return self.capacity - self.resources if self.capacity is not None else None


class Position:
    EPS = 1e-3

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def get_distance(self, other):
        # Doesnt have to euclidian distance, but rather distance dependent on the real routes
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

    def __eq__(self, other):
        if isinstance(other, Position):
            return abs(self.x - other.x) < self.EPS and abs(self.y - other.y) < self.EPS
        return False

    def __repr__(self):
        return "[{0:.1f}, {0:.1f}]".format(self.x, self.y)


class Transporter:

    def __init__(self, position, max_capacity=10, speed=1, name=None, log=True):
        self.position = position
        self.speed = speed
        self.max_capacity = max_capacity
        self.name = name or "Truck"

        self.loaded = 0
        self.distance_travelled = 0
        self.tasks = []
        self.historical_tasks = []
        self.work_steps = 0
        self.transported = 0

        self.log = get_logger().bind(name=self.name, position=self.position) if log else Mock()

    def __repr__(self):
        return "[{}] position: {} loaded: {}/{}".format(self.name or "Unknown", self.position, self.loaded,
                                                        self.max_capacity)

    def can_load(self, field, min_amount=0):
        if self.position != field.position:
            return exceptions.NotInPlaceException()

        elif not field.resources > 0:
            return exceptions.NothingToLoadException()

        elif self.max_capacity - self.loaded < min_amount:
            return exceptions.TruckIsAlredyFullException()

        elif not field.resources > min_amount:
            return exceptions.NotEnoughResources()

        return True

    def load(self, field):
        if self.can_load(field) is not True:
            raise self.can_load(field)

        to_load = min(field.resources, self.max_capacity - self.loaded)

        field.resources -= to_load
        self.loaded += to_load
        return to_load

    def can_unload(self, warehouse):
        if self.position != warehouse.position:
            return exceptions.NotInPlaceException()

        elif not warehouse.has_free_space():
            return exceptions.StorageIsFullException()
        return True

    def unload(self, warehouse):
        if self.can_unload(warehouse) is not True:
            raise self.can_unload(warehouse)

        cap = warehouse.get_free_capacity()
        to_unload = min(self.loaded, cap) if cap is not None else self.loaded

        self.loaded -= to_unload
        warehouse.resources += to_unload

        self.transported += to_unload
        return to_unload

    def is_on_position(self, position):
        return self.position == position

    def get_steps_to_postion(self, position):
        return self.position.get_distance(position) / self.speed

    def go_to_position(self, position):
        assert not self.is_on_position(position)

        steps_needed = self.get_steps_to_postion(position)

        if steps_needed < 1:
            self.distance_travelled += self.speed * steps_needed

            self.position.x = position.x
            self.position.y = position.y
            return 0

        else:
            self.distance_travelled += self.speed

            self.position.x += (position.x - self.position.x) / steps_needed
            self.position.y += (position.y - self.position.y) / steps_needed
            return steps_needed - 1

    def assign_task_queue(self, tasks):
        self.tasks = tasks

    def work(self):
        if self.is_working():

            self.work_steps += 1
            if not self.tasks[0].work(self):
                while len(self.tasks):
                    if self.tasks[0].completed:
                        self.historical_tasks.append(self.tasks[0])
                        self.tasks.pop(0)
                        self.log.info("Task is finished", finished=len(self.historical_tasks), remaining=len(self.tasks))
                    else:
                        break

            if len(self.tasks):
                return True
        self.log.info("All tasks is finished")
        return False

    def is_working(self):
        return len(self.tasks) > 0 or self.loaded > 0
