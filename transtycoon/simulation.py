import os
import uuid

import cv2

from transtycoon import exceptions
from transtycoon.report import plot_objects


class Simulation:

    def __init__(self, transports, captured_objects=None):
        self.transports = transports
        self.time = 0

        self.completed = [False for _ in transports]
        self.make_animation = captured_objects is not None
        self.captured_objects = captured_objects

        self.simulation_id = uuid.uuid4().hex

        if self.make_animation:
            os.makedirs(os.path.join(".simulation", self.simulation_id, "images"))

    def make_turn(self):
        for i, transport in enumerate(self.transports):

            if self.completed[i] is False and not transport.work():
                self.completed[i] = self.time
        self.time += 1
        if False not in self.completed:
            return False
        return True

    def make_turns(self, n=None):
        carry_on = True
        counter = 0
        while carry_on:
            if self.make_animation:
                self.make_snapshot(save=True)

            carry_on = self.make_turn()

            if n:
                if counter > n:
                    break
                counter += 1

        if self.make_animation:
            self.create_animation()

        return self.get_report()

    def get_time(self):
        return self.time

    def get_report(self):
        rep = {"simulation_steps": self.time,
               "transport_steps": self.completed,
               "total_work_steps": sum(self.completed)}

        # TODO
        return rep

    def make_snapshot(self, save=False):
        fig, ax = plot_objects(**self.captured_objects)

        path = os.path.join(".simulation", self.simulation_id, "images", "img_{}.png".format(self.time))
        ax.set_title("Time: {}".format(self.time))
        if save:
            fig.savefig(path)
        else:
            return fig, ax

    def create_animation(self):
        image_folder = os.path.join(".simulation", self.simulation_id, "images")
        video_name = os.path.join(".simulation", self.simulation_id, "animation.avi")

        images = [img for img in os.listdir(image_folder) if img.endswith(".png")]
        images = sorted(images, key=lambda x: int(x.split("_")[1].split(".")[0]))
        frame = cv2.imread(os.path.join(image_folder, images[0]))
        height, width, layers = frame.shape

        video = cv2.VideoWriter(video_name, -1, 1, (width, height))

        for image in images:
            video.write(cv2.imread(os.path.join(image_folder, image)))

        cv2.destroyAllWindows()
        video.release()
        print("Video created at {}".format(video_name))


class BaseTask:

    def __init__(self, wait_for=False, min_amount=0):
        self.completed = False
        self.turns_waiting_for_storage = 0
        self.turn_n = 0
        self.wait_for = wait_for or []
        self.min_amount = min_amount

    def wait_or_done(self):
        for obj in self.wait_for:
            if obj.is_working():
                return True
        return False


class OneWayGathering(BaseTask):

    def __init__(self, gather_from, deliver_to, wait_for=None, min_amount=0):
        super().__init__(wait_for=wait_for, min_amount=min_amount)

        self.gather_from = gather_from
        self.deliver_to = deliver_to

    def work(self, transport):
        self.completed = False
        this_turn_log = transport.log.bind(time=transport.work_steps, carry=transport.loaded)
        if transport.loaded == 0:
            if not transport.is_on_position(self.gather_from.position):
                transport.go_to_position(self.gather_from.position)
                this_turn_log.info("Moving to the {} ({})".format(self.gather_from.name, self.gather_from.resources))
            else:
                if self.wait_or_done() and transport.can_load(self.gather_from, self.min_amount) != True:
                    this_turn_log.info("Waiting for more resources to gather",
                                       present_cargo=self.gather_from.resources,
                                       min_carg0=self.min_amount)
                    return False

                try:
                    transport.load(self.gather_from)
                    this_turn_log.info("Loading",  carry=transport.loaded)
                except exceptions.NothingToLoadException:
                    if not self.wait_or_done():
                        if transport.loaded == 0:
                            self.completed = True
                            this_turn_log.info("Task completed - nothing more to load 1")
                            return False
                        else:
                            transport.go_to_position(self.deliver_to.position)
                            this_turn_log.info(
                                "Moving to the {} ({}) to deliver remaining cargo".format(self.deliver_to.name, self.deliver_to.resources))
                    else:
                        this_turn_log.info("Waiting for a cargo")
        else:
            if not transport.is_on_position(self.deliver_to.position):
                transport.go_to_position(self.deliver_to.position)
                this_turn_log.info("Moving to the {} ({})".format(self.deliver_to.name, self.deliver_to.resources))
            else:
                try:
                    transport.unload(self.deliver_to)
                    self.turns_waiting_for_storage = 0
                    this_turn_log.info("Unloading the cargo", carry=transport.loaded)

                    if self.gather_from.resources <= 0 and not self.wait_or_done():
                        self.completed = True
                        this_turn_log.info("Task completed - nothing more to load 2")
                        return False

                except exceptions.StorageIsFullException:
                    self.turns_waiting_for_storage += 1
                    this_turn_log.info("Waiting for {} to free a space for {} turns".format(self.deliver_to,
                                                                                            self.turns_waiting_for_storage))

        self.turn_n += 1
        return True
