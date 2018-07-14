import structlog
from matplotlib import pyplot as plt


def renderer(logger, name, event_dict, **kwargs):

    t = "Time {}".format(event_dict.pop("time")) if "time" in event_dict else ""

    event = event_dict.pop("event") if "event" in event_dict else ""
    name = ", {}".format(event_dict.pop("name")) if "name" in event_dict else ""

    return "[{}{}] {} : {}".format(t, name, event,
                                      "  ".join(["{}={}".format(key, value) for key, value in event_dict.items()]))


def get_logger():
    structlog.configure(processors=[renderer])
    return structlog.get_logger()


def plot_objects(warehouses=None, fields=None, transports=None, ax=None, scale=20, min_size=20, shift=None):
    fig = None
    if not ax:
        fig, ax = plt.subplots(figsize=(13, 8))

    if shift is None:
        shift = [0, 0]

    for field in fields or []:
        ax.scatter(field.position.x + shift[0], field.position.y + shift[1], s=field.resources * scale + min_size,
                   marker=r'$\clubsuit$')
        ax.annotate(field.name, (field.position.x + shift[0], field.position.y + shift[1]))

    for warehouse in warehouses or []:
        ax.scatter(warehouse.position.x + shift[0], warehouse.position.y + shift[1],
                   s=warehouse.resources * scale + min_size)
        ax.annotate(warehouse.name, (warehouse.position.x + shift[0], warehouse.position.y + shift[1]))

    for transport in transports or []:
        ax.scatter(transport.position.x + shift[0], transport.position.y + shift[1],
                   s=transport.loaded * scale + min_size, marker='^')
        ax.scatter(transport.position.x + shift[0], transport.position.y + shift[1],
                   s=transport.max_capacity * scale + min_size, marker='^',
                   alpha=0.5)

        ax.annotate(transport.name, (transport.position.x, transport.position.y))

    return fig, ax