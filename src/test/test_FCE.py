import unittest

import fast_complete_heuristic as FCE
import fast_complete_heuristic_variant as FCEV
from test.test_utils import build_data_dictionary
from test.common_tests import TestCommon


class TestFCE(TestCommon):

    def FCE_non_overlapping_patients(self):
        self.non_overlapping_patients()

    def FCE_non_overlapping_anesthetists(self):
        self.non_overlapping_anesthetists()

    def FCE_priority_constraints(self):
        self.priority_constraints()

    def FCE_surgery_time_constraint(self):
        self.surgery_time_constraint()

    def FCE_end_of_day_constraint(self):
        self.end_of_day_constraint()

    def FCE_anesthesia_total_time_constraint(self):
        self.anesthesia_total_time_constraint()

    def FCE_single_surgery(self):
        self.single_surgery()

    def FCE_anesthetist_assignment(self):
        self.anesthetist_assignment()


class TestFCEStandard(TestFCE):

    @classmethod
    def setUpClass(self):
        self.dataDictionary = build_data_dictionary()
        planner = FCE.Planner(timeLimit=900, gap=0.01, solver="cplex")
        planner.solve_model(self.dataDictionary)
        self.solution = planner.extract_solution()

    def test_FCEO_non_overlapping_patients(self):
        self.FCE_non_overlapping_patients()

    def test_FCEO_non_overlapping_anesthetists(self):
        self.FCE_non_overlapping_anesthetists()

    def test_FCEO_priority_constraints(self):
        self.FCE_priority_constraints()

    def test_FCEO_surgery_time_constraint(self):
        self.FCE_surgery_time_constraint()

    def test_FCEO_end_of_day_constraint(self):
        self.FCE_end_of_day_constraint()

    def test_FCEO_anesthesia_total_time_constraint(self):
        self.FCE_anesthesia_total_time_constraint()

    def test_FCEO_single_surgery(self):
        self.FCE_single_surgery()

    def test_FCEO_anesthetist_assignment(self):
        self.FCE_anesthetist_assignment()


class TestFCEVariant(TestFCE):

    @classmethod
    def setUpClass(self):
        self.dataDictionary = build_data_dictionary()
        planner = FCEV.Planner(timeLimit=900, gap=0.01, solver="cplex")
        planner.solve_model(self.dataDictionary)
        self.solution = planner.extract_solution()

    def test_FCEV_non_overlapping_patients(self):
        self.FCE_non_overlapping_patients()

    def test_FCEV_non_overlapping_anesthetists(self):
        self.FCE_non_overlapping_anesthetists()

    def test_FCEV_priority_constraints(self):
        self.FCE_priority_constraints()

    def test_FCEV_surgery_time_constraint(self):
        self.FCE_surgery_time_constraint()

    def test_FCEV_end_of_day_constraint(self):
        self.FCE_end_of_day_constraint()

    def test_FCEV_anesthesia_total_time_constraint(self):
        self.FCE_anesthesia_total_time_constraint()

    def test_FCEV_single_surgery(self):
        self.FCE_single_surgery()

    def test_FCEV_anesthetist_assignment(self):
        self.FCE_anesthetist_assignment()


if __name__ == '__main__':
    unittest.main()
