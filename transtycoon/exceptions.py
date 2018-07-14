

class NotInPlaceException(Exception):
    pass


class NothingToLoadException(Exception):
    pass


class TruckIsAlredyFullException(Exception):
    pass


class StorageIsFullException(Exception):
    pass


class RoutineFinished(StopIteration):
    pass


class NotEnoughResources(Exception):
    pass
