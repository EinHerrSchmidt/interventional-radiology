import unittest

from greedy_planner import Planner
from test.common import build_data_dictionary
from test.common import TestCommon


class TestGreedyRoomByRoom(TestCommon):

    @classmethod
    def setUpClass(self):
        self.dataDictionary = build_data_dictionary()
        planner = Planner(packingStrategy="default", anesthetistAssignmentStrategy="WIS")
        planner.solve_model(self.dataDictionary)
        self.solution = planner.extract_solution()

    def test_non_empty_solution(self):
        self.non_empty_solution()

    def test_non_overlapping_patients(self):
        self.non_overlapping_patients()

    def test_non_overlapping_anesthetists(self):
        self.non_overlapping_anesthetists()

    def test_priority_constraints(self):
        self.priority_constraints()

    def test_surgery_time_constraint(self):
        self.surgery_time_constraint()

    def test_end_of_day_constraint(self):
        self.end_of_day_constraint()

    def test_anesthesia_total_time_constraint(self):
        self.anesthesia_total_time_constraint()

    def test_single_surgery(self):
        self.single_surgery()

    def test_anesthetist_assignment(self):
        self.anesthetist_assignment()

class TestGreedyFirstFit(TestCommon):

    @classmethod
    def setUpClass(self):
        self.dataDictionary = build_data_dictionary()
        planner = Planner(packingStrategy="first fit", anesthetistAssignmentStrategy="WIS")
        planner.solve_model(self.dataDictionary)
        self.solution = planner.extract_solution()

    def test_non_empty_solution(self):
        self.non_empty_solution()

    def test_non_overlapping_patients(self):
        self.non_overlapping_patients()

    def test_non_overlapping_anesthetists(self):
        self.non_overlapping_anesthetists()

    def test_priority_constraints(self):
        self.priority_constraints()

    def test_surgery_time_constraint(self):
        self.surgery_time_constraint()

    def test_end_of_day_constraint(self):
        self.end_of_day_constraint()

    def test_anesthesia_total_time_constraint(self):
        self.anesthesia_total_time_constraint()

    def test_single_surgery(self):
        self.single_surgery()

    def test_anesthetist_assignment(self):
        self.anesthetist_assignment()

class TestGreedyBestFit(TestCommon):

    @classmethod
    def setUpClass(self):
        self.dataDictionary = build_data_dictionary()
        planner = Planner(packingStrategy="best fit", anesthetistAssignmentStrategy="WIS")
        planner.solve_model(self.dataDictionary)
        self.solution = planner.extract_solution()

    def test_non_empty_solution(self):
        self.non_empty_solution()

    def test_non_overlapping_patients(self):
        self.non_overlapping_patients()

    def test_non_overlapping_anesthetists(self):
        self.non_overlapping_anesthetists()

    def test_priority_constraints(self):
        self.priority_constraints()

    def test_surgery_time_constraint(self):
        self.surgery_time_constraint()

    def test_end_of_day_constraint(self):
        self.end_of_day_constraint()

    def test_anesthesia_total_time_constraint(self):
        self.anesthesia_total_time_constraint()

    def test_single_surgery(self):
        self.single_surgery()

    def test_anesthetist_assignment(self):
        self.anesthetist_assignment()

if __name__ == '__main__':
    unittest.main()
