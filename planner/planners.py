from __future__ import division
import logging
import re
import time
import pyomo.environ as pyo
import plotly.express as px
import pandas as pd
import datetime
from pyomo.opt import SolverStatus, TerminationCondition
from math import isclose

from abc import ABC, abstractmethod

from planner.model import Patient


class Planner(ABC):

    DISCARDED = 0
    FREE = 1
    FIXED = 2

    def __init__(self, timeLimit, gap, solver):
        self.solver = pyo.SolverFactory(solver)
        if(solver == "cplex"):
            self.timeLimit = 'timelimit'
            self.gap = 'mipgap'
            self.solver.options['emphasis'] = "mip 2"
        if(solver == "gurobi"):
            self.timeLimit = 'timelimit'
            self.gap = 'mipgap'
            self.solver.options['mipfocus'] = 2
        if(solver == "cbc"):
            self.timeLimit = 'seconds'
            self.gap = 'ratiogap'
            self.solver.options['heuristics'] = "on"
            # self.solver.options['round'] = "on"
            # self.solver.options['feas'] = "on"
            self.solver.options['cuts'] = "on"
            self.solver.options['preprocess'] = "on"
            # self.solver.options['printingOptions'] = "normal"

        self.solver.options[self.timeLimit] = timeLimit
        self.solver.options[self.gap] = gap

        self.reset_run_info()

    def reset_run_info(self):
        self.solver_time = 0
        self.cumulated_building_time = 0
        self.status_ok = False
        self.gap = 0
        self.MP_objective_function_value = 0
        self.objective_function_value = 0
        self.MP_time_limit_hit = False
        self.time_limit_hit = False
        self.MP_upper_bound = 0
        self.upper_bound = 0


    @abstractmethod
    def extract_run_info(self):
        pass

    @abstractmethod
    def define_model(self):
        pass

    @staticmethod
    def single_surgery_rule(model, i):
        return sum(model.x[i, k, t] for k in model.k for t in model.t) <= 1

    @staticmethod
    def single_delay_rule(model, i):
        return sum(model.delta[q, i, k, t] for k in model.k for t in model.t for q in model.q) <= 1

    @staticmethod
    def robustness_constraints_rule(model, q, k, t):
        return sum(model.delta[q, i, k, t] for i in model.i) <= model.Gamma[q, k, t]

    @staticmethod
    def delay_implication_constraint_rule(model, i, k, t):
        return model.x[i, k, t] >= sum(model.delta[q, i, k, t] for q in model.q)

    @staticmethod
    def surgery_time_rule(model, k, t):
        return sum(model.p[i] * model.x[i, k, t] + sum(model.d[q, i] * model.delta[q, i, k, t] for q in model.q) for i in model.i) <= model.s[k, t]

    @staticmethod
    def specialty_assignment_rule(model, j, k, t):
        return sum(model.x[i, k, t] for i in model.i if model.specialty[i] == j) <= model.bigM[1] * model.tau[j, k, t]

    @staticmethod
    def anesthetist_assignment_rule(model, i, t):
        if(model.a[i] == 0):
            return pyo.Constraint.Skip
        return sum(model.beta[alpha, i, t] for alpha in model.alpha) == model.a[i] * sum(model.x[i, k, t] for k in model.k)

    @staticmethod
    def anesthetist_time_rule(model, alpha, t):
        return sum(model.beta[alpha, i, t] * model.p[i] for i in model.i) + sum(model.z[q, alpha, i, k, t] * model. d[q, i] for i in model.i for k in model.k for q in model.q) <= model.An[alpha, t]

    # needed for linearizing product of binary variables
    @staticmethod
    def z_rule_1(model, alpha, i, k, t):
        return sum(model.z[q, alpha, i, k, t] for q in model.q) <= model.beta[alpha, i, t]

    @staticmethod
    def z_rule_2(model, alpha, i, k, t):
        return sum(model.z[q, alpha, i, k, t] for q in model.q) <= sum(model.delta[q, i, k, t] for q in model.q)

    @staticmethod
    def z_rule_3(model, alpha, i, k, t):
        return sum(model.z[q, alpha, i, k, t] for q in model.q) >= model.beta[alpha, i, t] + sum(model.delta[q, i, k, t] for q in model.q) - 1

    # patients with same anesthetist on same day but different room cannot overlap
    @staticmethod
    @abstractmethod
    def anesthetist_no_overlap_rule(model, i1, i2, k1, k2, t, alpha):
        pass

    # precedence across rooms
    @staticmethod
    @abstractmethod
    def lambda_rule(model, i1, i2, t):
        pass

    # ensure gamma plus operation time does not exceed end of day
    @staticmethod
    @abstractmethod
    def end_of_day_rule(model, i, k, t):
        pass

    # ensure that patient i1 terminates operation before i2, if y_12kt = 1
    @staticmethod
    @abstractmethod
    def time_ordering_precedence_rule(model, i1, i2, k, t):
        pass

    @staticmethod
    @abstractmethod
    def start_time_ordering_priority_rule(model, i1, i2, k, t):
        pass

    # either i1 comes before i2 in (k, t) or i2 comes before i1 in (k, t)
    @staticmethod
    @abstractmethod
    def exclusive_precedence_rule(model, i1, i2, k, t):
        pass

    @staticmethod
    def objective_function(model):
        N = 1 / (sum(model.r[i] for i in model.i))
        R = sum(model.x[i, k, t] * model.r[i] for i in model.i for k in model.k for t in model.t)
        return sum(model.d[q, i] * model.delta[q, i, k, t] for i in model.i for k in model.k for t in model.t for q in model.q) * 667 + 10000 * N * R

    # constraints
    def define_single_surgery_constraints(self, model):
        model.single_surgery_constraint = pyo.Constraint(
            model.i,
            rule=self.single_surgery_rule)

    def define_single_delay_constraints(self, model):
        model.single_surgery_delay_constraint = pyo.Constraint(
            model.i,
            rule=self.single_delay_rule)

    def define_robustness_constraints(self, model):
        model.robustness_constraint = pyo.Constraint(
            model.q,
            model.k,
            model.t,
            rule=self.robustness_constraints_rule)

    def define_delay_implication_constraint(self, model):
        model.delay_implication_constraint = pyo.Constraint(
            model.i,
            model.k,
            model.t,
            rule=self.delay_implication_constraint_rule)

    def define_surgery_time_constraints(self, model):
        model.surgery_time_constraint = pyo.Constraint(
            model.k,
            model.t,
            rule=self.surgery_time_rule)

    def define_specialty_assignment_constraints(self, model):
        model.specialty_assignment_constraint = pyo.Constraint(
            model.j,
            model.k,
            model.t,
            rule=self.specialty_assignment_rule)

    def define_anesthetist_assignment_constraint(self, model):
        model.anesthetist_assignment_constraint = pyo.Constraint(
            model.i,
            model.t,
            rule=self.anesthetist_assignment_rule)

    def define_anesthetist_time_constraint(self, model):
        model.anesthetist_time_constraint = pyo.Constraint(
            model.alpha,
            model.t,
            rule=self.anesthetist_time_rule)

    def define_anesthetist_no_overlap_constraint(self, model):
        model.anesthetist_no_overlap_constraint = pyo.Constraint(
            model.i,
            model.i,
            model.k,
            model.k,
            model.t,
            model.alpha,
            rule=self.anesthetist_no_overlap_rule)

    def define_lambda_constraint(self, model):
        model.lambda_constraint = pyo.Constraint(
            model.i,
            model.i,
            model.t,
            rule=self.lambda_rule)

    def define_end_of_day_constraint(self, model):
        model.end_of_day_constraint = pyo.Constraint(
            model.i,
            model.k,
            model.t,
            rule=self.end_of_day_rule)

    def define_priority_constraint(self, model):
        model.priority_constraint = pyo.Constraint(
            model.i,
            model.i,
            model.k,
            model.t,
            rule=self.start_time_ordering_priority_rule)

    def define_precedence_constraint(self, model):
        model.precedence_constraint = pyo.Constraint(
            model.i,
            model.i,
            model.k,
            model.t,
            rule=self.time_ordering_precedence_rule)

    def define_exclusive_precedence_constraint(self, model):
        model.exclusive_precedence_constraint = pyo.Constraint(
            model.i,
            model.i,
            model.k,
            model.t,
            rule=self.exclusive_precedence_rule)

    def define_z_constraints(self, model):
        model.z_constraints_1 = pyo.Constraint(
            model.alpha,
            model.i,
            model.k,
            model.t,
            rule=self.z_rule_1)

        model.z_constraints_2 = pyo.Constraint(
            model.alpha,
            model.i,
            model.k,
            model.t,
            rule=self.z_rule_2)

        model.z_constraints_3 = pyo.Constraint(
            model.alpha,
            model.i,
            model.k,
            model.t,
            rule=self.z_rule_3)

    def define_objective(self, model):
        model.objective = pyo.Objective(
            rule=self.objective_function,
            sense=pyo.maximize)

    def define_lambda_variables(self, model):
        model.Lambda = pyo.Var(model.i,
                               model.i,
                               model.t,
                               domain=pyo.Binary)

    def define_y_variables(self, model):
        model.y = pyo.Var(model.i,
                          model.i,
                          model.k,
                          model.t,
                          domain=pyo.Binary)

    def define_gamma_variables(self, model):
        model.gamma = pyo.Var(model.i, domain=pyo.NonNegativeReals)

    def define_anesthetists_number_param(self, model):
        model.A = pyo.Param(within=pyo.NonNegativeIntegers)

    def define_anesthetists_range_set(self, model):
        model.alpha = pyo.RangeSet(1, model.A)

    def define_beta_variables(self, model):
        model.beta = pyo.Var(model.alpha,
                             model.i,
                             model.t,
                             domain=pyo.Binary)

    def define_anesthetists_availability(self, model):
        model.An = pyo.Param(model.alpha, model.t)

    def define_sets(self, model):
        model.I = pyo.Param(within=pyo.NonNegativeIntegers)
        model.J = pyo.Param(within=pyo.NonNegativeIntegers)
        model.K = pyo.Param(within=pyo.NonNegativeIntegers)
        model.T = pyo.Param(within=pyo.NonNegativeIntegers)
        model.M = pyo.Param(within=pyo.NonNegativeIntegers)
        model.Q = pyo.Param(within=pyo.NonNegativeIntegers)

        model.i = pyo.RangeSet(1, model.I)
        model.j = pyo.RangeSet(1, model.J)
        model.k = pyo.RangeSet(1, model.K)
        model.t = pyo.RangeSet(1, model.T)
        model.bigMRangeSet = pyo.RangeSet(1, model.M)
        model.q = pyo.RangeSet(1, model.Q)

    def define_x_variables(self, model):
        model.x = pyo.Var(model.i,
                          model.k,
                          model.t,
                          domain=pyo.Binary)

    def define_delta_variables(self, model):
        model.delta = pyo.Var(model.q,
                              model.i,
                              model.k,
                              model.t,
                              domain=pyo.Binary)

    def define_z_variables(self, model):
        model.z = pyo.Var(model.q,
                          model.alpha,
                          model.i,
                          model.k,
                          model.t,
                          domain=pyo.Binary)

    def define_parameters(self, model):
        model.p = pyo.Param(model.i)
        model.d = pyo.Param(model.q, model.i)
        model.r = pyo.Param(model.i)
        model.s = pyo.Param(model.k, model.t)
        model.a = pyo.Param(model.i)
        model.c = pyo.Param(model.i)
        model.u = pyo.Param(model.i, model.i)
        model.tau = pyo.Param(model.j, model.k, model.t)
        model.specialty = pyo.Param(model.i)
        model.bigM = pyo.Param(model.bigMRangeSet)
        model.precedence = pyo.Param(model.i)
        model.Gamma = pyo.Param(model.q, model.k, model.t)


class SimplePlanner(Planner):

    def __init__(self, timeLimit, gap, solver):
        super().__init__(timeLimit, gap, solver)
        self.model = pyo.AbstractModel()
        self.model_instance = None

    @staticmethod
    def anesthetist_no_overlap_rule(model, i1, i2, k1, k2, t, alpha):
        if(i1 == i2 or k1 == k2 or model.a[i1] * model.a[i2] == 0):
            return pyo.Constraint.Skip
        return model.gamma[i1] + model.p[i1] + sum(model.d[q, i1] * model.delta[q, i1, k1, t] for q in model.q) <= model.gamma[i2] + model.bigM[3] * (5 - model.beta[alpha, i1, t] - model.beta[alpha, i2, t] - model.x[i1, k1, t] - model.x[i2, k2, t] - model.Lambda[i1, i2, t])

    @staticmethod
    def lambda_rule(model, i1, i2, t):
        if(i1 >= i2 or not (model.a[i1] == 1 and model.a[i2] == 1)):
            return pyo.Constraint.Skip
        return model.Lambda[i1, i2, t] + model.Lambda[i2, i1, t] == 1

    @staticmethod
    def end_of_day_rule(model, i, k, t):
        if((model.specialty[i] == 1 and (k == 3 or k == 4))
           or (model.specialty[i] == 2 and (k == 1 or k == 2))):
            return pyo.Constraint.Skip
        return model.gamma[i] + model.p[i] + sum(model.d[q, i] * model.delta[q, i, k, t] for q in model.q) <= model.s[k, t]

    @staticmethod
    def time_ordering_precedence_rule(model, i1, i2, k, t):
        if(i1 == i2
           or (model.specialty[i1] != model.specialty[i2])
           or (model.specialty[i1] == 1 and (k == 3 or k == 4))
           or (model.specialty[i1] == 2 and (k == 1 or k == 2))):
            return pyo.Constraint.Skip
        return model.gamma[i1] + model.p[i1] + sum(model.d[q, i1] * model.delta[q, i1, k, t] for q in model.q) <= model.gamma[i2] + model.bigM[5] * (3 - model.x[i1, k, t] - model.x[i2, k, t] - model.y[i1, i2, k, t])

    @staticmethod
    def start_time_ordering_priority_rule(model, i1, i2, k, t):
        if(i1 == i2 or model.u[i1, i2] == 0
           or (model.specialty[i1] != model.specialty[i2])
           or (model.specialty[i1] == 1 and (k == 3 or k == 4))
           or (model.specialty[i1] == 2 and (k == 1 or k == 2))):
            return pyo.Constraint.Skip
        return model.gamma[i1] * model.u[i1, i2] <= model.gamma[i2] * (1 - model.u[i2, i1]) + model.bigM[2] * (2 - model.x[i1, k, t] - model.x[i2, k, t])

    @staticmethod
    def exclusive_precedence_rule(model, i1, i2, k, t):
        if(i1 >= i2
           or (model.specialty[i1] != model.specialty[i2])
           or (model.specialty[i1] == 1 and (k == 3 or k == 4))
           or (model.specialty[i1] == 2 and (k == 1 or k == 2))):
            return pyo.Constraint.Skip
        return model.y[i1, i2, k, t] + model.y[i2, i1, k, t] == 1

    def define_model(self):
        self.define_sets(self.model)
        self.define_parameters(self.model)
        self.define_x_variables(self.model)
        self.define_delta_variables(self.model)
        self.define_single_delay_constraints(self.model)
        self.define_robustness_constraints(self.model)
        self.define_delay_implication_constraint(self.model)

        self.define_single_surgery_constraints(self.model)
        self.define_surgery_time_constraints(self.model)
        self.define_specialty_assignment_constraints(self.model)

        self.define_anesthetists_number_param(self.model)
        self.define_anesthetists_range_set(self.model)
        self.define_beta_variables(self.model)
        self.define_anesthetists_availability(self.model)
        self.define_lambda_variables(self.model)
        self.define_y_variables(self.model)
        self.define_gamma_variables(self.model)

        self.define_anesthetist_assignment_constraint(self.model)
        self.define_z_variables(self.model)
        self.define_z_constraints(self.model)
        self.define_anesthetist_time_constraint(self.model)
        self.define_anesthetist_no_overlap_constraint(self.model)
        self.define_lambda_constraint(self.model)
        self.define_end_of_day_constraint(self.model)
        self.define_priority_constraint(self.model)
        self.define_precedence_constraint(self.model)
        self.define_exclusive_precedence_constraint(self.model)

        self.define_objective(self.model)

    def create_model_instance(self, data):
        print("Creating model instance...")
        t = time.time()
        self.model_instance = self.model.create_instance(data)
        elapsed = (time.time() - t)
        self.cumulated_building_time += elapsed

    def fix_y_variables(self, model_instance):
        print("Fixing y variables...")
        fixed = 0
        for k in model_instance.k:
            for t in model_instance.t:
                for i1 in range(2, self.model_instance.I + 1):
                    for i2 in range(1, i1):
                        if(model_instance.u[i1, i2] == 1):
                            model_instance.y[i1, i2, k, t].fix(1)
                            model_instance.y[i2, i1, k, t].fix(0)
                            fixed += 2
        print(str(fixed) + " y variables fixed.")

    def extract_solution(self):
        dict = {}
        for k in self.model_instance.k:
            for t in self.model_instance.t:
                patients = []
                for i in self.model_instance.i:
                    if(round(self.model_instance.x[i, k, t].value) == 1):
                        p = self.model_instance.p[i]
                        if(sum(round(self.model_instance.delta[q, i, k, t].value) for q in self.model_instance.q) == 1):
                            d = True
                            arrival_delay = self.model_instance.d[1, i]
                        else:
                            d = False
                            arrival_delay = 0
                        c = self.model_instance.c[i]
                        a = self.model_instance.a[i]
                        anesthetist = 0
                        for alpha in self.model_instance.alpha:
                            if(round(self.model_instance.beta[alpha, i, t].value) == 1):
                                anesthetist = alpha
                        order = round(self.model_instance.gamma[i].value)
                        specialty = self.model_instance.specialty[i]
                        priority = self.model_instance.r[i]
                        precedence = self.model_instance.precedence[i]
                        patients.append(Patient(
                            i, priority, k, specialty, t, p, arrival_delay, c, precedence, None, a, anesthetist, order, d))
                patients.sort(key=lambda x: x.order)
                dict[(k, t)] = patients
        return dict

    def extract_run_info(self):
        return {"cumulated_building_time": self.cumulated_building_time,
                "solver_time": self.solver_time,
                "time_limit_hit": self.time_limit_hit,
                "upper_bound": self.upper_bound,
                "status_ok": self.status_ok,
                "gap": self.gap
                }

    def solve_model(self, data):
        self.define_model()
        self.create_model_instance(data)
        self.reset_run_info()
        self.fix_y_variables(self.model_instance)
        print("Solving model instance...")
        self.model.results = self.solver.solve(self.model_instance, tee=True)
        print("\nModel instance solved.")
        self.solver_time = self.solver._last_solve_time
        resultsAsString = str(self.model.results)
        self.upper_bound = float(
            re.search("Upper bound: -*(\d*\.\d*)", resultsAsString).group(1))
        self.gap = round(
            (1 - pyo.value(self.model_instance.objective) / self.upper_bound) * 100, 2)

        self.time_limit_hit = self.model.results.solver.termination_condition in [
            TerminationCondition.maxTimeLimit]
        self.status_ok = self.model.results.solver.status == SolverStatus.ok


class TwoPhasePlanner(Planner):

    def __init__(self, timeLimit, gap, solver):
        super().__init__(timeLimit, gap, solver)
        self.MP_model = pyo.AbstractModel()
        self.MP_instance = None
        self.SP_model = pyo.AbstractModel()
        self.SP_instance = None

    def define_model(self):
        self.define_MP()
        self.define_SP()

        self.define_objective(self.MP_model)
        self.define_objective(self.SP_model)

    def define_MP(self):
        self.define_sets(self.MP_model)
        self.define_parameters(self.MP_model)
        self.define_x_variables(self.MP_model)
        self.define_delta_variables(self.MP_model)
        self.define_single_delay_constraints(self.MP_model)
        self.define_robustness_constraints(self.MP_model)
        self.define_delay_implication_constraint(self.MP_model)
        self.define_single_surgery_constraints(self.MP_model)
        self.define_surgery_time_constraints(self.MP_model)
        self.define_specialty_assignment_constraints(self.MP_model)
        self.define_anesthetists_number_param(self.MP_model)
        self.define_anesthetists_range_set(self.MP_model)
        self.define_beta_variables(self.MP_model)
        self.define_anesthetists_availability(self.MP_model)
        self.define_anesthetist_assignment_constraint(self.MP_model)
        self.define_z_variables(self.MP_model)
        self.define_z_constraints(self.MP_model)
        self.define_anesthetist_time_constraint(self.MP_model)

    def define_x_parameters(self):
        self.SP_model.x_param = pyo.Param(self.SP_model.i,
                                          self.SP_model.k,
                                          self.SP_model.t)

    def define_status_parameters(self):
        self.SP_model.status = pyo.Param(self.SP_model.i,
                                         self.SP_model.k,
                                         self.SP_model.t)

    def define_SP(self):
        self.define_sets(self.SP_model)
        self.define_parameters(self.SP_model)
        self.define_x_variables(self.SP_model)
        self.define_delta_variables(self.SP_model)
        self.define_single_delay_constraints(self.SP_model)
        self.define_robustness_constraints(self.SP_model)
        self.define_delay_implication_constraint(self.SP_model)
        self.define_single_surgery_constraints(self.SP_model)
        self.define_surgery_time_constraints(self.SP_model)
        self.define_specialty_assignment_constraints(self.SP_model)
        self.define_anesthetists_number_param(self.SP_model)
        self.define_anesthetists_range_set(self.SP_model)
        self.define_beta_variables(self.SP_model)
        self.define_anesthetists_availability(self.SP_model)
        self.define_anesthetist_assignment_constraint(self.SP_model)
        self.define_z_variables(self.SP_model)
        self.define_z_constraints(self.SP_model)
        self.define_anesthetist_time_constraint(self.SP_model)

        # SP's components
        self.define_x_parameters()
        self.define_status_parameters()
        self.define_lambda_variables(self.SP_model)
        self.define_y_variables(self.SP_model)
        self.define_gamma_variables(self.SP_model)
        self.define_anesthetist_no_overlap_constraint(self.SP_model)
        self.define_lambda_constraint(self.SP_model)
        self.define_end_of_day_constraint(self.SP_model)
        self.define_priority_constraint(self.SP_model)
        self.define_precedence_constraint(self.SP_model)
        self.define_exclusive_precedence_constraint(self.SP_model)

    def create_MP_instance(self, data):
        print("Creating MP instance...")
        t = time.time()
        self.MP_instance = self.MP_model.create_instance(data)
        elapsed = (time.time() - t)
        print("MP instance created in " + str(round(elapsed, 2)) + "s")
        self.cumulated_building_time += elapsed

    def create_SP_instance(self, data):
        self.extend_data(data)
        print("Creating SP instance...")
        t = time.time()
        self.SP_instance = self.SP_model.create_instance(data)
        elapsed = (time.time() - t)
        print("SP instance created in " + str(round(elapsed, 2)) + "s")
        self.cumulated_building_time += elapsed

    def extract_solution(self):
        if(self.SP_model.results.solver.status != SolverStatus.ok):
            return None
        dict = {}
        for k in self.SP_instance.k:
            for t in self.SP_instance.t:
                patients = []
                for i in self.SP_instance.i:
                    if(round(self.SP_instance.x[i, k, t].value) == 1):
                        p = self.SP_instance.p[i]
                        if(sum(round(self.SP_instance.delta[q, i, k, t].value) for q in self.SP_instance.q) == 1):
                            d = True
                            arrival_delay = self.SP_instance.d[1, i]
                        else:
                            d = False
                            arrival_delay = 0
                        c = self.SP_instance.c[i]
                        a = self.SP_instance.a[i]
                        anesthetist = 0
                        for alpha in self.SP_instance.alpha:
                            if(round(self.SP_instance.beta[alpha, i, t].value) == 1):
                                anesthetist = alpha
                        order = round(self.SP_instance.gamma[i].value, 2)
                        specialty = self.SP_instance.specialty[i]
                        priority = self.SP_instance.r[i]
                        precedence = self.SP_instance.precedence[i]
                        patients.append(Patient(
                            i, priority, k, specialty, t, p, arrival_delay, c, precedence, None, a, anesthetist, order, d))
                patients.sort(key=lambda x: x.order)
                dict[(k, t)] = patients
        return dict

    def solve_MP(self):
        print("Solving MP instance...")
        self.MP_model.results = self.solver.solve(self.MP_instance, tee=True)
        print("\nMP instance solved.")
        self.solver_time += self.solver._last_solve_time
        self.MP_time_limit_hit = self.MP_model.results.solver.termination_condition in [
            TerminationCondition.maxTimeLimit]
        self.MP_objective_function_value = pyo.value(self.MP_instance.objective)

        resultsAsString = str(self.MP_model.results)
        self.MP_upper_bound = float(
            re.search("Upper bound: -*(\d*\.\d*)", resultsAsString).group(1))

    def solve_SP(self):
        print("Solving SP instance...")
        self.SP_model.results = self.solver.solve(self.SP_instance, tee=True)
        print("SP instance solved.")
        self.solver_time += self.solver._last_solve_time
        self.time_limit_hit = self.SP_model.results.solver.termination_condition in [
            TerminationCondition.maxTimeLimit]


class LBBDPlanner(TwoPhasePlanner):

    def __init__(self, timeLimit, gap, iterations_cap, solver):
        super().__init__(timeLimit, gap, solver)
        self.iterations_cap = iterations_cap
        self.fail = False

    @staticmethod
    def anesthetist_no_overlap_rule(model, i1, i2, k1, k2, t, alpha):
        if(model.status[i1, k1, t] == Planner.DISCARDED or model.status[i2, k2, t] == Planner.DISCARDED):
            return pyo.Constraint.Skip
        if(i1 == i2 or k1 == k2 or model.a[i1] * model.a[i2] == 0):
            return pyo.Constraint.Skip
        return model.gamma[i1] + model.p[i1] + sum(model.d[q, i1] * model.delta[q, i1, k1, t] for q in model.q) <= model.gamma[i2] + model.bigM[3] * (5 - model.beta[alpha, i1, t] - model.beta[alpha, i2, t] - model.x[i1, k1, t] - model.x[i2, k2, t] - model.Lambda[i1, i2, t])

    @staticmethod
    def end_of_day_rule(model, i, k, t):
        if(model.status[i, k, t] == Planner.DISCARDED):
            return pyo.Constraint.Skip
        if((model.specialty[i] == 1 and (k == 3 or k == 4))
           or (model.specialty[i] == 2 and (k == 1 or k == 2))):
            return pyo.Constraint.Skip
        return model.gamma[i] + model.p[i] + sum(model.d[q, i] * model.delta[q, i, k, t] for q in model.q) <= model.s[k, t]

    @staticmethod
    def time_ordering_precedence_rule(model, i1, i2, k, t):
        if(model.status[i1, k, t] == Planner.DISCARDED or model.status[i2, k, t] == Planner.DISCARDED):
            return pyo.Constraint.Skip
        if(i1 == i2
           or (model.specialty[i1] != model.specialty[i2])
           or (model.specialty[i1] == 1 and (k == 3 or k == 4))
           or (model.specialty[i1] == 2 and (k == 1 or k == 2))):
            return pyo.Constraint.Skip
        return model.gamma[i1] + model.p[i1] + sum(model.d[q, i1] * model.delta[q, i1, k, t] for q in model.q) <= model.gamma[i2] + model.bigM[5] * (3 - model.x[i1, k, t] - model.x[i2, k, t] - model.y[i1, i2, k, t])

    @staticmethod
    def start_time_ordering_priority_rule(model, i1, i2, k, t):
        if(model.status[i1, k, t] == Planner.DISCARDED or model.status[i2, k, t] == Planner.DISCARDED):
            return pyo.Constraint.Skip
        if(i1 == i2 or model.u[i1, i2] == 0
           or (model.specialty[i1] != model.specialty[i2])
           or (model.specialty[i1] == 1 and (k == 3 or k == 4))
           or (model.specialty[i1] == 2 and (k == 1 or k == 2))):
            return pyo.Constraint.Skip
        return model.gamma[i1] * model.u[i1, i2] <= model.gamma[i2] * (1 - model.u[i2, i1]) + model.bigM[2] * (2 - model.x[i1, k, t] - model.x[i2, k, t])

    @staticmethod
    def exclusive_precedence_rule(model, i1, i2, k, t):
        if(model.specialty[i1] != model.specialty[i2]):
            return pyo.Constraint.Skip
        if(model.status[i1, k, t] == Planner.DISCARDED or model.status[i2, k, t] == Planner.DISCARDED):
            return pyo.Constraint.Skip
        if(i1 >= i2
           or (model.specialty[i1] != model.specialty[i2])
           or (model.specialty[i1] == 1 and (k == 3 or k == 4))
           or (model.specialty[i1] == 2 and (k == 1 or k == 2))):
            return pyo.Constraint.Skip
        return model.y[i1, i2, k, t] + model.y[i2, i1, k, t] == 1

    def extract_run_info(self):
        return {"cumulated_building_time": self.cumulated_building_time,
                "solver_time": self.solver_time,
                "time_limit_hit": self.time_limit_hit,
                "upper_bound": self.upper_bound,
                "status_ok": self.status_ok,
                "gap": self.gap,
                "MP_objective_function_value": self.MP_objective_function_value,
                "objective_function_value": self.objective_function_value,
                "MP_upper_bound": self.MP_upper_bound,
                "MP_time_limit_hit": self.MP_time_limit_hit,
                "time_limit_hit": self.time_limit_hit
                }

    @staticmethod
    def lambda_rule(model, i1, i2, t):
        if(i1 >= i2 or not (model.a[i1] == 1 and model.a[i2] == 1)):
            return pyo.Constraint.Skip
        # if patients not on same day
        if(sum(model.x_param[i1, k, t] for k in model.k) == 0 or sum(model.x_param[i2, k, t] for k in model.k) == 0):
            return pyo.Constraint.Skip
        return model.Lambda[i1, i2, t] + model.Lambda[i2, i1, t] == 1

    def extend_data(self, data):
        x_param_dict = {}
        status_dict = {}
        for i in self.MP_instance.i:
            for t in self.MP_instance.t:
                # patient scheduled on day t
                if(sum(round(self.MP_instance.x[i, k, t].value) for k in self.MP_instance.k) == 1):
                    for k in range(1, self.MP_instance.K + 1):
                        status_dict[(i, k, t)] = Planner.FREE
                        x_param_dict[(i, k, t)] = 1
                else:
                    for k in range(1, self.MP_instance.K + 1):
                        status_dict[(i, k, t)] = Planner.DISCARDED
                        x_param_dict[(i, k, t)] = 0
        data[None]['x_param'] = x_param_dict
        data[None]['status'] = status_dict

    def fix_SP_x_variables(self):
        print("Fixing x variables for phase two...")
        fixed = 0
        for k in self.MP_instance.k:
            for t in self.MP_instance.t:
                for i in self.MP_instance.i:
                    if(self.SP_instance.status[i, k, t] == Planner.DISCARDED):
                        self.SP_instance.x[i, k, t].fix(0)
                        fixed += 1
        print(str(fixed) + " x variables fixed.")

    def fix_SP_delta_variables(self):
        print("Fixing delta variables for phase two...")
        fixed = 0
        for q in self.MP_instance.q:
            for k in self.MP_instance.k:
                for t in self.MP_instance.t:
                    for i in self.MP_instance.i:
                        if(self.SP_instance.status[i, k, t] == Planner.DISCARDED):
                            self.SP_instance.delta[q, i, k, t].fix(0)
                            fixed += 1
        print(str(fixed) + " delta variables fixed.")

    def fix_MP_delta_variables(self):
        print("Fixing delta variables for phase one...")
        fixed = 0
        for q in self.MP_instance.q:
            for k in self.MP_instance.k:
                for t in self.MP_instance.t:
                    for i in self.MP_instance.i:
                        if(self.MP_instance.specialty[i] == 1 and k in [3, 4] or self.MP_instance.specialty[i] == 2 and k in [1, 2]):
                            self.MP_instance.delta[q, i, k, t].fix(0)
                            fixed += 1
        print(str(fixed) + " delta variables fixed.")

    def fix_MP_x_variables(self):
        print("Fixing delta variables for phase one...")
        fixed = 0
        for k in self.MP_instance.k:
            for t in self.MP_instance.t:
                for i in self.MP_instance.i:
                    if(self.MP_instance.specialty[i] == 1 and k in [3, 4] or self.MP_instance.specialty[i] == 2 and k in [1, 2]):
                        self.MP_instance.x[i, k, t].fix(0)
                        fixed += 1
        print(str(fixed) + " delta variables fixed.")







    def is_infeasible(self, model):
        return model.results.solver.termination_condition in [TerminationCondition.infeasibleOrUnbounded, TerminationCondition.infeasible, TerminationCondition.unbounded]

    def extract_objective_value(self):
        objective_value = None
        if not self.fail and self.status_ok:
            if self.status_ok:
                objective_value = pyo.value(self.SP_instance.objective)
        return objective_value

    def solve_MP(self):
        super().solve_MP()
        residual_time = self.solver.options[self.timeLimit] - self.solver._last_solve_time
        if residual_time <= 0:
            self.last_SP_round = True
            self.solver.options[self.timeLimit] = 10
        else:
            self.solver.options[self.timeLimit] = residual_time

    def solve_SP(self):
        super().solve_SP()
        self.solver.options[self.timeLimit] = self.solver.options[self.timeLimit] - \
            self.solver._last_solve_time

    def extract_run_info(self):
        return {"cumulated_building_time": self.cumulated_building_time,
                "solver_time": self.solver_time,
                "time_limit_hit": self.time_limit_hit,
                "upper_bound": self.upper_bound,
                "status_ok": self.status_ok,
                "gap": self.gap,
                "MP_objective_function_value": self.MP_objective_function_value,
                "objective_function_value": self.objective_function_value,
                "MP_upper_bound": self.MP_upper_bound,
                "MP_time_limit_hit": self.MP_time_limit_hit,
                "time_limit_hit": self.time_limit_hit,
                "iterations": self.iterations,
                "fail": self.fail
                }

    def is_optimal(self):
        return isclose(pyo.value(self.MP_instance.objective), pyo.value(self.SP_instance.objective))

    @staticmethod
    def MP_anesthetist_time_rule(model, t):
        return sum(model.a[i] * model.p[i] * model.x[i, k, t] + sum(model.d[q, i] * model.delta[q, i, k, t] for q in model.q) for i in model.i for k in model.k) - sum(model.An[alpha, t] for alpha in model.alpha) <= 0

    def define_MP_anesthetist_time_constraint(self, model):
        model.MP_anesthetist_time_constraint = pyo.Constraint(
            model.t,
            rule=self.MP_anesthetist_time_rule)

    def define_MP(self):
        self.define_sets(self.MP_model)
        self.define_parameters(self.MP_model)
        self.define_x_variables(self.MP_model)
        self.define_delta_variables(self.MP_model)
        self.define_single_delay_constraints(self.MP_model)
        self.define_robustness_constraints(self.MP_model)
        self.define_delay_implication_constraint(self.MP_model)
        self.define_single_surgery_constraints(self.MP_model)
        self.define_surgery_time_constraints(self.MP_model)
        self.define_specialty_assignment_constraints(self.MP_model)
        self.define_anesthetists_number_param(self.MP_model)
        self.define_anesthetists_range_set(self.MP_model)
        # self.define_beta_variables(self.MP_model)
        self.define_anesthetists_availability(self.MP_model)
        # self.define_anesthetist_assignment_constraint(self.MP_model)
        # self.define_z_variables(self.MP_model)
        # self.define_z_constraints(self.MP_model)
        self.define_MP_anesthetist_time_constraint(self.MP_model)

    def add_objective_cut(self):
        N = 1 / (sum(self.MP_instance.r[i] for i in self.MP_instance.i))
        R = sum(self.MP_instance.x[i, k, t] * self.MP_instance.r[i] for i in self.MP_instance.i for k in self.MP_instance.k for t in self.MP_instance.t)
        cut = sum(self.MP_instance.d[q, i] * self.MP_instance.delta[q, i, k, t] for i in self.MP_instance.i for k in self.MP_instance.k for t in self.MP_instance.t for q in self.MP_instance.q) * 667 + 10000 * N * R <= pyo.value(self.MP_instance.objective)
        self.MP_instance.objective_function_cuts.add(cut)

    def solve_model(self, data):
        self.define_model()
        self.reset_run_info()
        self.create_MP_instance(data)
        self.MP_instance.patients_cuts = pyo.ConstraintList()
        self.MP_instance.objective_function_cuts = pyo.ConstraintList()

        self.iterations = 0
        self.fail = False
        self.last_SP_round = False
        while self.iterations < self.iterations_cap:
            self.iterations += 1
            # MP
            self.fix_MP_delta_variables()
            self.solve_MP()

            # SP
            self.create_SP_instance(data)
            self.fix_SP_x_variables()
            self.solve_SP()

            if not self.is_optimal() and not self.last_SP_round:
                self.MP_instance.patients_cuts.add(sum(
                    1 - self.MP_instance.x[i, k, t] for i in self.MP_instance.i for k in self.MP_instance.k for t in self.MP_instance.t if round(self.MP_instance.x[i, k, t].value) == 1) >= 1)
                # self.MP_instance.objective_function_cuts.add(
                #     sum(self.MP_instance.r[i] * self.MP_instance.x[i, k, t] for i in self.MP_instance.i for k in self.MP_instance.k for t in self.MP_instance.t) <= pyo.value(self.MP_instance.objective))
                self.add_objective_cut()
            else:
                break

        self.status_ok = self.SP_model.results and self.SP_model.results.solver.status == SolverStatus.ok
        self.objective_function_value = self.extract_objective_value()