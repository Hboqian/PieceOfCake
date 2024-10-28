from typing import List
import numpy as np
import logging
import constants
import miniball

from enum import Enum

from piece_of_cake_state import PieceOfCakeState


class Strategy(Enum):
    SNEAK = "sneak"
    CLIMB_HILLS = "climb_hills"
    SAWTOOTH = "sawtooth"


class G2_Player:
    def __init__(
        self,
        rng: np.random.Generator,
        logger: logging.Logger,
        precomp_dir: str,
        tolerance: int,
    ) -> None:
        """Initialise the player with the basic information

        Args:
            rng (np.random.Generator): numpy random number generator, use this for same player behavior across run
            logger (logging.Logger): logger use this like logger.info("message")
            precomp_dir (str): Directory path to store/load pre-computation
            tolerance (int): tolerance for the cake distribution
            cake_len (int): Length of the smaller side of the cake
        """

        self.rng = rng
        self.logger = logger
        self.tolerance = tolerance
        self.cake_len = None
        self.move_queue = []
        self.move_queue = []

        self.phase = "HORIZONTAL"
        self.direction = ""
        self.strategy = Strategy.SNEAK

    def cut(self, cake_len, cake_width, cur_pos) -> tuple[int, List[int]]:
        if cur_pos[0] == 0:
            return constants.CUT, [cake_width, round((cur_pos[1] + 5) % cake_len, 2)]
        else:
            return constants.CUT, [0, round((cur_pos[1] + 5) % cake_len, 2)]

    def assign(self) -> tuple[int, List[int]]:

        # Get sorted indices of polygons and requests in decreasing order of area
        sorted_polygon_indices = sorted(
            range(len(self.polygons)), key=lambda i: self.polygons[i].area, reverse=True
        )
        sorted_request_indices = sorted(
            range(len(self.requests)), key=lambda i: self.requests[i], reverse=True
        )

        # Assign each sorted polygon to each sorted request by index
        assignment = [-1] * min(
            len(sorted_polygon_indices), len(sorted_request_indices)
        )
        for i in range(min(len(sorted_polygon_indices), len(sorted_request_indices))):
            polygon_idx = sorted_polygon_indices[i]
            request_idx = sorted_request_indices[i]
            assignment[request_idx] = (
                polygon_idx  # Match request index to polygon index
            )

        return constants.ASSIGN, assignment

    def sneak(self, start_pos, end_pos, cake_width, cake_len):
        """
        Given a start position & goal position, uses the 1-pixel shaving technique
        to append the necessary steps to the move_queue
        """
        nearest_x, x_dist = nearest_edge_x(start_pos, cake_width)
        nearest_y, y_dist = nearest_edge_y(start_pos, cake_len)

        end_x, end_x_dist = nearest_edge_x(end_pos, cake_width)
        end_y, end_y_dist = nearest_edge_y(end_pos, cake_len)

        # if we are on the top or bottom or the board and require more than 1 move
        if y_dist == 0 and (x_dist > 0.1 or nearest_x != end_x):
            bounce_y = bounce(nearest_y)
            self.move_queue.append([end_x, bounce_y])

            # if the end is not on the same line so we must ricochet off of corner
            if end_y_dist > 0 or nearest_y != end_y:
                bounce_x = bounce(end_x)
                self.move_queue.append([bounce_x, nearest_y])

                # if the end position is on the opposite side
                if end_y_dist == 0:
                    bounce_y = bounce(end_y)
                    self.move_queue.append([bounce_x, end_y])
                    self.move_queue.append([end_x, bounce_y])

        # if we are on the left or right side of the board and require more than 1 move
        elif x_dist == 0 and (y_dist > 0.1 or nearest_y != end_y):
            bounce_x = bounce(nearest_x)
            self.move_queue.append([bounce_x, end_y])

            # if the end is not on the same line so we must ricochet off of corner
            if end_x_dist > 0 or nearest_x != end_x:
                bounce_y = bounce(end_y)
                self.move_queue.append([nearest_x, bounce_y])

                # if the end position is on the opposite side
                if end_x_dist == 0:
                    bounce_x = bounce(end_x)
                    self.move_queue.append([end_x, bounce_y])
                    self.move_queue.append([bounce_x, end_y])

        self.move_queue.append(end_pos)
        return

    def even_cuts(self):
        """
        Adds moves to the merge queue that will cut the cake into even slices.
        """

        n = len(self.requests)
        s_x = self.cake_width / np.sqrt(n)
        s_y = self.cake_len / np.sqrt(n)
        pos = self.cur_pos

        if self.turn_number == 2:
            self.move_queue.append([0, s_y])
            self.move_queue.append([self.cake_width, s_y])
            return

        if self.phase == "HORIZONTAL" and pos[1] + s_y >= self.cake_len:
            self.phase = "VERTICAL"
            if pos[0] == 0:
                new_x = s_x
            else:
                new_x = self.cake_width - s_x
                self.direction = "RIGHT"
            self.sneak(pos, [new_x, self.cake_len], self.cake_width, self.cake_len)
            self.move_queue.append([new_x, 0])

            return

        if self.phase == "HORIZONTAL":
            self.sneak(pos, [pos[0], pos[1] + s_y], self.cake_width, self.cake_len)
            if pos[0] == 0:
                opposite = self.cake_width
            else:
                opposite = 0
            self.move_queue.append([opposite, round(pos[1] + s_y, 2)])

        else:
            if self.direction == "RIGHT":
                new_x = pos[0] - s_x
            else:
                new_x = pos[0] + s_x

            if new_x <= 0 or new_x >= self.cake_width:
                self.phase = "DONE"
                return

            self.sneak(pos, [new_x, pos[1]], self.cake_width, self.cake_len)
            if pos[1] == 0:
                opposite = self.cake_len
            else:
                opposite = 0
            self.move_queue.append([new_x, opposite])

        return

    def can_cake_fit_in_plate(self, cake_piece, radius=12.5):
        cake_points = np.array(
            list(zip(*cake_piece.exterior.coords.xy)), dtype=np.double
        )
        res = miniball.miniball(cake_points)

        return res["radius"] <= radius

    # use just any assignment for now,
    # ideally, we want to find the assignment with the smallest penalty
    # instead of this random one
    def __get_assignments(self) -> float:
        # TODO: Find a way to match polygons with requests
        # with a low penalty

        # sorted_requests = sorted(
        #     [(i, req) for i, req in enumerate(self.requests)], key=lambda x: x[1]
        # )

        if len(self.requests) > len(self.polygons):
            # specify amount of -1 padding needed
            padding = len(self.requests) - len(self.polygons)
            return padding * [-1] + list(range(len(self.polygons)))

        # return an amount of polygon indexes
        # without exceeding the amount of requests
        return list(range(len(self.polygons)))[: len(self.requests)]

    def __calculate_penalty(self, assign_func) -> float:
        penalty = 0
        assignments = assign_func()

        for request_index, assignment in enumerate(assignments):
            # check if the cake piece fit on a plate of diameter 25 and calculate penaly accordingly
            if assignment == -1 or (
                not self.can_cake_fit_in_plate(self.polygons[assignment])
            ):
                penalty += 100
            else:
                penalty_percentage = (
                    100
                    * abs(self.polygons[assignment].area - self.requests[request_index])
                    / self.requests[request_index]
                )
                if penalty_percentage > self.tolerance:
                    penalty += penalty_percentage
        return penalty

    def sneak_alg(self):
        if self.turn_number == 1:
            return constants.INIT, [0.01, 0]

        if len(self.move_queue) == 0 and self.phase != "DONE":
            self.even_cuts()

        if len(self.move_queue) > 0:
            next_val = self.move_queue.pop(0)
            cut = [round(next_val[0], 2), round(next_val[1], 2)]
            return constants.CUT, cut

        if len(self.polygons) < len(self.requests):
            if self.cur_pos[0] == 0:
                return constants.CUT, [
                    self.cake_width,
                    round((self.cur_pos[1] + 5) % self.cake_len, 2),
                ]
            else:
                return constants.CUT, [
                    0,
                    round((self.cur_pos[1] + 5) % self.cake_len, 2),
                ]

        if len(self.polygons) < len(self.requests):
            return self.cut(self.cake_len, self.cake_width, self.cur_pos)
        else:
            return self.assign()

    def climb_hills(self):
        current_penalty = self.__calculate_penalty(self.__get_assignments)
        print(f"1 penalty: {current_penalty}")
        current_penalty = self.__calculate_penalty(self.assign)
        print(f"2 penalty: {current_penalty}")

        if self.turn_number == 1:
            print()
            return constants.INIT, [0, 0]

        if len(self.polygons) < len(self.requests):
            if self.cur_pos[0] == 0:
                return constants.CUT, [
                    self.cake_width,
                    round((self.cur_pos[1] + 5) % self.cake_len, 2),
                ]
            else:
                return constants.CUT, [
                    0,
                    round((self.cur_pos[1] + 5) % self.cake_len, 2),
                ]

        assignment = []
        for i in range(len(self.requests)):
            assignment.append(i)

        return constants.ASSIGN, assignment

    def process_percept(self, current_percept: PieceOfCakeState):
        self.polygons = current_percept.polygons
        self.turn_number = current_percept.turn_number
        self.cur_pos = current_percept.cur_pos
        self.requests = current_percept.requests
        self.cake_len = current_percept.cake_len
        self.cake_width = current_percept.cake_width

    def move(self, current_percept: PieceOfCakeState) -> tuple[int, List[int]]:
        """Function which retrieves the current state of the amoeba map and returns an amoeba movement"""
        self.process_percept(current_percept)

        match self.strategy:
            case Strategy.SNEAK:
                return self.sneak_alg()
            case Strategy.CLIMB_HILLS:
                return self.climb_hills()

            case _:
                return self.sneak_alg()


def nearest_edge_x(pos, cake_width):
    """
    Returns the nearest X-edge and the distance to said edge
    X-edge is 0 if the position is closer to the left side, or cake_width
        if it is closer to the right side.
    """
    min_x = pos[0]
    x_edge = 0
    if cake_width - pos[0] < min_x:
        min_x = cake_width - pos[0]
        x_edge = cake_width
    return x_edge, min_x


def nearest_edge_y(pos, cake_len):
    """
    Returns the nearest Y-edge and the distance to said edge
    Y-edge is 0 if the position is closer to the top, or cake_len
        if it is closer to the bottom.
    """
    min_y = pos[1]
    y_edge = 0
    if cake_len - pos[1] < min_y:
        min_y = cake_len - pos[1]
        y_edge = cake_len
    return y_edge, min_y


def bounce(margin):
    """
    Returns a value 0.01 away from the provided margin
    """
    if margin == 0:
        return 0.01
    return round(margin - 0.01, 2)
