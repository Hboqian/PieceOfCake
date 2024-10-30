from collections import defaultdict
import os
import pickle
from typing import List

import numpy as np
import math
import logging

import constants


class Player:
    def __init__(self, rng: np.random.Generator, logger: logging.Logger,
                 precomp_dir: str, tolerance: int) -> None:
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
        self.requests = None
        self.polygons = None
        self.cake_len = None
        self.cake_width = None
        self.cake_diagonal = None
        self.cuts = []
        self.turn_number = None
        self.cut_number = None
        self.cur_pos = None
        self.base_case_switch = False
        self.working_height = None
    

    def move(self, current_percept) -> tuple[int, List[int]]:
        """Function which retrieves the current state of the amoeba map and returns an amoeba movement

            Args:
                current_percept(TimingMazeState): contains current state information
            Returns:
                int: This function returns the next move of the user:
                    WAIT = -1
                    LEFT = 0
                    UP = 1
                    RIGHT = 2
                    DOWN = 3
        """
        self.polygons = current_percept.polygons
        self.turn_number = current_percept.turn_number
        self.cut_number = current_percept.turn_number - 1
        self.cur_pos = current_percept.cur_pos
        action = None
    
        if self.turn_number == 1:
            # initialize instance variables, sorted requests
            self.requests = current_percept.requests
            self.cake_len = current_percept.cake_len
            self.cake_width = current_percept.cake_width
            self.cake_diagonal = self.calcDiagonal()

            self.cuts.append((0, 0))
            return constants.INIT, [0,0]

        # case if the diagonal of the total cake is <= 25
        if self.cake_diagonal <= 25:
            action = self.cutSmallCake()
        
        else:
            if len(self.polygons) != len(self.requests):
                if self.cur_pos[0] == 0:
                    return constants.CUT, [self.cake_width, round((self.cur_pos[1] + 5)%self.cake_len, 2)]
                else:
                    return constants.CUT, [0, round((self.cur_pos[1] + 5)%self.cake_len, 2)]
                
            assignment = []
            for i in range(len(self.requests)):
                assignment.append(i)

            return constants.ASSIGN, assignment
        
        return action
    
    def calcDiagonal(self) -> float:
        return (math.sqrt((self.cake_len * self.cake_len) + (self.cake_width * self.cake_width)))
    
    def cutSmallCake(self): 
        # assign pieces

        if (self.cut_number > len(self.requests)):
            assignment = self.assignPolygons(polygons=self.polygons)
            return constants.ASSIGN, assignment
        
        current_area = self.requests[self.cut_number - 1]
        
        x = self.cur_pos[0]
        y = self.cur_pos[1]

        if self.base_case_switch:
            # TODO: this currently retraces the past cut and creates triangles from the same point
            x = self.cuts[self.cut_number - 2][0]
            y = self.cuts[self.cut_number - 2][1]
            print ("y:", y)
            if y == 0 or y == self.cake_len:
                print ("in first")
                self.working_height = abs(y - self.cuts[self.cut_number - 1][1])
                x += round(2 * current_area / self.working_height, 2)
            elif self.cuts[self.cut_number - 1][1] == 0:
                print ("in second")
                self.working_height = abs(x - self.cuts[self.cut_number - 1][0])
                y -= round(2 * current_area / self.working_height, 2)
            elif self.cuts[self.cut_number - 1][1] == self.cake_len:
                print ("in third")
                self.working_height = abs(x - self.cuts[self.cut_number - 1][0])
                y += round(2 * current_area / self.working_height, 2)
            else:
                print("this is a problem")
            
            self.cuts.append((x, y))
            return constants.CUT, [x, y]

        if (self.cut_number == 1):
            x = round(2 * current_area / self.cake_len, 2)
        else:
            x = round(self.cuts[self.cut_number - 2][0] + (2 * current_area / self.cake_len), 2)

        y = (0, self.cake_len) [self.cut_number % 2]

        if x > self.cake_width:
            if y == 0: 
                self.base_case_switch = True
            elif y == self.cake_len:
                self.base_case_switch = True

            area_left = (self.cake_len * self.cake_width) / 1.05 * .05 # finding the extra cake portion
            self.working_height = self.cake_width - self.cur_pos[0]
            if (self.cut_number < len(self.requests)): # not on our last request
                area_left += sum(self.requests[self.cut_number:])a
            x = self.cake_width
            y = round(2 * area_left / self.working_height, 2)
           
        self.cuts.append((x, y))
        return constants.CUT, [x, y]

    
    def assignPolygons(self, polygons) -> list[int]:
        # parse polygons to polygon_areas: dict(rank: (area, i))
        polygon_areas = []
        requests_items = []
        for i in range(len(polygons)):
            polygon_areas.append((polygons[i].area, i)) 
        for i in range(len(self.requests)):
            requests_items.append((self.requests[i], i))

        matches = {} # request : polygon

        for i in range(len(requests_items)):
            min_diff = math.inf
            polygon = -1
            polygon_index = -1
            for j in range(len(polygon_areas)):
                temp_diff = abs(float(polygon_areas[j][0]) - float(requests_items[i][0]))
                if temp_diff < min_diff:
                    min_diff = temp_diff
                    polygon = polygon_areas[j][1]
                    polygon_index = j
            matches[i] = polygon
            polygon_areas.pop(polygon_index)
        
        assignment = []
        for i in range(len(requests_items)):
            if i in matches:
                assignment.append(matches[i])
            else:
                assignment.append(-1)
        print("THIS IS MY ASSIGNMENT", assignment)
        return assignment
    

                




        
        
