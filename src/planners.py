from __future__ import division
import logging
import re
import time
import pyomo.environ as pyo
import plotly.express as px
import pandas as pd
import datetime
from pyomo.opt import SolverStatus, TerminationCondition

from model import Patient
from abc import ABC, abstractmethod


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

    @abstractmethod
    def define_model(self):
        pass

    @staticmethod
    def single_surgery_rule(model, i):
        return sum(model.x[i, k, t] for k in model.k for t in model.t) <= 1

    @staticmethod
    def surgery_time_rule(model, k, t):
        return sum(model.p[i] * model.x[i, k, t] for i in model.i) <= model.s[k, t]

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
        return sum(model.beta[alpha, i, t] * model.p[i] for i in model.i) <= model.An[alpha, t]

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
        return sum(model.r[i] * model.x[i, k, t] for i in model.i for k in model.k for t in model.t)

    # constraints
    def define_single_surgery_constraints(self, model):
        model.single_surgery_constraint = pyo.Constraint(
            model.i,
            rule=self.single_surgery_rule)

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

        model.i = pyo.RangeSet(1, model.I)
        model.j = pyo.RangeSet(1, model.J)
        model.k = pyo.RangeSet(1, model.K)
        model.t = pyo.RangeSet(1, model.T)
        model.bigMRangeSet = pyo.RangeSet(1, model.M)

    def define_x_variables(self, model):
        model.x = pyo.Var(model.i,
                          model.k,
                          model.t,
                          domain=pyo.Binary)

    def define_parameters(self, model):
        model.p = pyo.Param(model.i)
        model.r = pyo.Param(model.i)
        model.s = pyo.Param(model.k, model.t)
        model.a = pyo.Param(model.i)
        model.c = pyo.Param(model.i)
        model.u = pyo.Param(model.i, model.i)
        model.tau = pyo.Param(model.j, model.k, model.t)
        model.specialty = pyo.Param(model.i)
        model.bigM = pyo.Param(model.bigMRangeSet)
        model.d = pyo.Param(model.i)
        model.precedence = pyo.Param(model.i)


class SimplePlanner(Planner):

    def __init__(self, timeLimit, gap, solver):
        super().__init__(timeLimit, gap, solver)
        self.model = pyo.AbstractModel()
        self.modelInstance = None

    @staticmethod
    def anesthetist_no_overlap_rule(model, i1, i2, k1, k2, t, alpha):
        if(i1 == i2 or k1 == k2 or model.a[i1] * model.a[i2] == 0):
            return pyo.Constraint.Skip
        return model.gamma[i1] + model.p[i1] <= model.gamma[i2] + model.bigM[3] * (5 - model.beta[alpha, i1, t] - model.beta[alpha, i2, t] - model.x[i1, k1, t] - model.x[i2, k2, t] - model.Lambda[i1, i2, t])

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
        return model.gamma[i] + model.p[i] <= model.s[k, t]

    @staticmethod
    def time_ordering_precedence_rule(model, i1, i2, k, t):
        if(i1 == i2
           or (model.specialty[i1] != model.specialty[i2])
           or (model.specialty[i1] == 1 and (k == 3 or k == 4))
           or (model.specialty[i1] == 2 and (k == 1 or k == 2))):
            return pyo.Constraint.Skip
        return model.gamma[i1] + model.p[i1] <= model.gamma[i2] + model.bigM[5] * (3 - model.x[i1, k, t] - model.x[i2, k, t] - model.y[i1, i2, k, t])

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
        self.define_x_variables(self.model)
        self.define_parameters(self.model)

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
        self.modelInstance = self.model.create_instance(data)
        elapsed = (time.time() - t)
        return elapsed

    def fix_y_variables(self, modelInstance):
        print("Fixing y variables...")
        fixed = 0
        for k in modelInstance.k:
            for t in modelInstance.t:
                for i1 in range(2, self.modelInstance.I + 1):
                    for i2 in range(1, i1):
                        if(modelInstance.u[i1, i2] == 1):
                            modelInstance.y[i1, i2, k, t].fix(1)
                            modelInstance.y[i2, i1, k, t].fix(0)
                            fixed += 2
        print(str(fixed) + " y variables fixed.")

    def extract_solution(self):
        dict = {}
        for k in self.modelInstance.k:
            for t in self.modelInstance.t:
                patients = []
                for i in self.modelInstance.i:
                    if(round(self.modelInstance.x[i, k, t].value) == 1):
                        p = self.modelInstance.p[i]
                        c = self.modelInstance.c[i]
                        a = self.modelInstance.a[i]
                        anesthetist = 0
                        for alpha in self.modelInstance.alpha:
                            if(round(self.modelInstance.beta[alpha, i, t].value) == 1):
                                anesthetist = alpha
                        order = round(self.modelInstance.gamma[i].value)
                        specialty = self.modelInstance.specialty[i]
                        priority = self.modelInstance.r[i]
                        precedence = self.modelInstance.precedence[i]
                        patients.append(Patient(
                            i, priority, k, specialty, t, p, c, precedence, None, a, anesthetist, order))
                patients.sort(key=lambda x: x.order)
                dict[(k, t)] = patients
        return dict

    def solve_model(self, data):
        self.define_model()
        buildingTime = self.create_model_instance(data)
        self.fix_y_variables(self.modelInstance)
        print("Solving model instance...")
        self.model.results = self.solver.solve(self.modelInstance, tee=True)
        print("\nModel instance solved.")
        print(self.model.results)
        resultsAsString = str(self.model.results)
        upperBound = float(
            re.search("Upper bound: -*(\d*\.\d*)", resultsAsString).group(1))

        timeLimitHit = self.model.results.solver.termination_condition in [
            TerminationCondition.maxTimeLimit]
        statusOk = self.model.results.solver.status == SolverStatus.ok

        runInfo = {"BuildingTime": buildingTime,
                   "StatusOK": statusOk,
                   "SolverTime": self.solver._last_solve_time,
                   "TimeLimitHit": timeLimitHit,
                   "UpperBound": upperBound,
                   "Gap": round((1 - pyo.value(self.modelInstance.objective) / upperBound) * 100, 2)
                   }

        return runInfo


class TwoPhasePlanner(Planner):

    def __init__(self, timeLimit, gap, solver):
        super().__init__(timeLimit, gap, solver)
        self.MP_model = pyo.AbstractModel()
        self.MPInstance = None
        self.SP_model = pyo.AbstractModel()
        self.SPInstance = None

    def define_model(self):
        self.define_MP()
        self.define_SP()

        self.define_objective(self.MP_model)
        self.define_objective(self.SP_model)

    def define_MP(self):
        self.define_sets(self.MP_model)
        self.define_x_variables(self.MP_model)
        self.define_parameters(self.MP_model)
        self.define_single_surgery_constraints(self.MP_model)
        self.define_surgery_time_constraints(self.MP_model)
        self.define_specialty_assignment_constraints(self.MP_model)
        self.define_anesthetists_number_param(self.MP_model)
        self.define_anesthetists_range_set(self.MP_model)
        self.define_beta_variables(self.MP_model)
        self.define_anesthetists_availability(self.MP_model)
        self.define_anesthetist_assignment_constraint(self.MP_model)
        self.define_anesthetist_time_constraint(self.MP_model)

        self.define_objective(self.MP_model)

    def define_x_parameters(self):
        self.SP_model.xParam = pyo.Param(self.SP_model.i,
                                        self.SP_model.k,
                                        self.SP_model.t)

    def define_status_parameters(self):
        self.SP_model.status = pyo.Param(self.SP_model.i,
                                        self.SP_model.k,
                                        self.SP_model.t)

    def define_SP(self):
        self.define_sets(self.SP_model)
        self.define_x_variables(self.SP_model)
        self.define_parameters(self.SP_model)
        self.define_single_surgery_constraints(self.SP_model)
        self.define_surgery_time_constraints(self.SP_model)
        self.define_specialty_assignment_constraints(self.SP_model)
        self.define_anesthetists_number_param(self.SP_model)
        self.define_anesthetists_range_set(self.SP_model)
        self.define_beta_variables(self.SP_model)
        self.define_anesthetists_availability(self.SP_model)
        self.define_anesthetist_assignment_constraint(self.SP_model)
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

        self.define_objective(self.SP_model)

    def extract_solution(self):
        if(self.SP_model.results.solver.status != SolverStatus.ok):
            return None
        dict = {}
        for k in self.SPInstance.k:
            for t in self.SPInstance.t:
                patients = []
                for i in self.SPInstance.i:
                    if(round(self.SPInstance.x[i, k, t].value) == 1):
                        p = self.SPInstance.p[i]
                        c = self.SPInstance.c[i]
                        a = self.SPInstance.a[i]
                        anesthetist = 0
                        for alpha in self.SPInstance.alpha:
                            if(round(self.SPInstance.beta[alpha, i, t].value) == 1):
                                anesthetist = alpha
                        order = round(self.SPInstance.gamma[i].value, 2)
                        specialty = self.SPInstance.specialty[i]
                        priority = self.SPInstance.r[i]
                        precedence = self.SPInstance.precedence[i]
                        patients.append(Patient(
                            i, priority, k, specialty, t, p, c, precedence, None, a, anesthetist, order))
                patients.sort(key=lambda x: x.order)
                dict[(k, t)] = patients
        return dict


class TwoPhaseHeuristicPlanner(TwoPhasePlanner):

    @abstractmethod
    def fix_SP_x_variables(self):
        pass

    @abstractmethod
    def extend_data(self, data):
        pass

    @staticmethod
    def anesthetist_no_overlap_rule(model, i1, i2, k1, k2, t, alpha):
        if(model.status[i1, k1, t] == Planner.DISCARDED or model.status[i2, k2, t] == Planner.DISCARDED):
            return pyo.Constraint.Skip
        if(i1 == i2 or k1 == k2 or model.a[i1] * model.a[i2] == 0):
            return pyo.Constraint.Skip
        return model.gamma[i1] + model.p[i1] <= model.gamma[i2] + model.bigM[3] * (5 - model.beta[alpha, i1, t] - model.beta[alpha, i2, t] - model.x[i1, k1, t] - model.x[i2, k2, t] - model.Lambda[i1, i2, t])

    @staticmethod
    def end_of_day_rule(model, i, k, t):
        if(model.status[i, k, t] == Planner.DISCARDED):
            return pyo.Constraint.Skip
        if((model.specialty[i] == 1 and (k == 3 or k == 4))
           or (model.specialty[i] == 2 and (k == 1 or k == 2))):
            return pyo.Constraint.Skip
        return model.gamma[i] + model.p[i] <= model.s[k, t]

    @staticmethod
    def time_ordering_precedence_rule(model, i1, i2, k, t):
        if(model.status[i1, k, t] == Planner.DISCARDED or model.status[i2, k, t] == Planner.DISCARDED):
            return pyo.Constraint.Skip
        if(i1 == i2
           or (model.specialty[i1] != model.specialty[i2])
           or (model.specialty[i1] == 1 and (k == 3 or k == 4))
           or (model.specialty[i1] == 2 and (k == 1 or k == 2))):
            return pyo.Constraint.Skip
        return model.gamma[i1] + model.p[i1] <= model.gamma[i2] + model.bigM[5] * (3 - model.x[i1, k, t] - model.x[i2, k, t] - model.y[i1, i2, k, t])

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

    def create_MP_instance(self, data):
        print("Creating MP instance...")
        t = time.time()
        self.MPInstance = self.MP_model.create_instance(data)
        elapsed = (time.time() - t)
        print("MP instance created in " + str(round(elapsed, 2)) + "s")
        return elapsed

    def create_SP_instance(self, data):
        self.extend_data(data)
        print("Creating SP instance...")
        t = time.time()
        self.SPInstance = self.SP_model.create_instance(data)
        elapsed = (time.time() - t)
        print("SP instance created in " + str(round(elapsed, 2)) + "s")
        return elapsed

    def solve_model(self, data):
        self.define_model()
        MPBuildingTime = self.create_MP_instance(data)

        # MP
        print("Solving MP instance...")
        print(self.solver)
        self.MP_model.results = self.solver.solve(self.MPInstance, tee=True, keepfiles=True)
        print("\nMP instance solved.")
        MPSolverTime = self.solver._last_solve_time
        MPTimeLimitHit = self.MP_model.results.solver.termination_condition in [
            TerminationCondition.maxTimeLimit]
        resultsAsString = str(self.MP_model.results)
        MPUpperBound = float(
            re.search("Upper bound: -*(\d*\.\d*)", resultsAsString).group(1))

        self.solver.options[self.timeLimit] = max(
            10, 600 - self.solver._last_solve_time)

        # SP
        SPBuildingTime = self.create_SP_instance(data)

        self.fix_SP_x_variables()
        print("Solving SP instance...")
        self.SP_model.results = self.solver.solve(self.SPInstance, tee=True, keepfiles=True)
        print("SP instance solved.")
        SPSolverTime = self.solver._last_solve_time
        SPTimeLimitHit = self.SP_model.results.solver.termination_condition in [
            TerminationCondition.maxTimeLimit]

        statusOk = self.SP_model.results.solver.status == SolverStatus.ok

        runInfo = {"MPSolverTime": MPSolverTime,
                   "SPSolverTime": SPSolverTime,
                   "MPBuildingTime": MPBuildingTime,
                   "SPBuildingTime": SPBuildingTime,
                   "statusOk": statusOk,
                   "MPTimeLimitHit": MPTimeLimitHit,
                   "SPTimeLimitHit": SPTimeLimitHit,
                   "MPobjectiveValue": pyo.value(self.MPInstance.objective),
                   "SPobjectiveValue": pyo.value(self.SPInstance.objective),
                   "MPUpperBound": MPUpperBound,
                   "objectiveFunctionLB": 0}

        print(self.SP_model.results)
        return runInfo


class FastCompleteHeuristicPlanner(TwoPhaseHeuristicPlanner):

    @staticmethod
    def lambda_rule(model, i1, i2, t):
        if(i1 >= i2 or not (model.a[i1] == 1 and model.a[i2] == 1)):
            return pyo.Constraint.Skip
        i1AllDay = 0
        i2AllDay = 0
        for k in model.k:
            # if i1, i2 happen to be assigned to same room k on day t, then no need to use constraint
            if(model.status[i1, k, t] == Planner.FIXED and model.status[i2, k, t] == Planner.FIXED):
                return pyo.Constraint.Skip
            if(model.status[i1, k, t] == Planner.FIXED or model.status[i1, k, t] == Planner.FREE):
                i1AllDay += 1
            if(model.status[i2, k, t] == Planner.FIXED or model.status[i2, k, t] == Planner.FREE):
                i2AllDay += 1
        if(i1AllDay == 0 or i2AllDay == 0):
            return pyo.Constraint.Skip
        return model.Lambda[i1, i2, t] + model.Lambda[i2, i1, t] == 1

    def extend_data(self, data):
        statusDict = {}
        for i in range(1, self.MPInstance.I + 1):
            for k in range(1, self.MPInstance.K + 1):
                for t in range(1, self.MPInstance.T + 1):
                    if(round(self.MPInstance.x[i, k, t].value) == 1 and self.MPInstance.a[i] == 1):
                        statusDict[(i, k, t)] = Planner.FREE
                    elif(round(self.MPInstance.x[i, k, t].value) == 1 and self.MPInstance.a[i] == 0):
                        statusDict[(i, k, t)] = Planner.FIXED
                    else:
                        statusDict[(i, k, t)] = Planner.DISCARDED
        data[None]['status'] = statusDict

    def fix_SP_x_variables(self):
        print("Fixing x variables for phase two...")
        fixed = 0
        for k in self.MPInstance.k:
            for t in self.MPInstance.t:
                for i1 in self.MPInstance.i:
                    if(round(self.MPInstance.x[i1, k, t].value) == 1 and self.SPInstance.a[i1] == 0):
                        self.SPInstance.x[i1, k, t].fix(1)
                        fixed += 1
                    if(round(self.MPInstance.x[i1, k, t].value) == 0):
                        self.SPInstance.x[i1, k, t].fix(0)
                        fixed += 1
        print(str(fixed) + " x variables fixed.")


class FastCompleteLagrangeanHeuristicPlanner(FastCompleteHeuristicPlanner):

    @staticmethod
    def objective_function_MP(model):
        return sum(model.r[i] * model.x[i, k, t] for i in model.i for k in model.k for t in model.t) + 1 / (sum(model.An[alpha, t] for alpha in model.alpha for t in model.t) + sum(model.p[i] for i in model.i)) * sum(model.An[alpha, t] - sum(model.beta[alpha, i, t] * model.p[i] for i in model.t) for alpha in model.alpha for t in model.t)

    def define_objective_MP(self, model):
        model.objective = pyo.Objective(
            rule=self.objective_function_MP,
            sense=pyo.maximize)

    def define_model(self):
        self.define_MP()
        self.define_SP()

        self.define_objective_MP(self.MP_model)
        self.define_objective(self.SP_model)


class SlowCompleteHeuristicPlanner(TwoPhaseHeuristicPlanner):

    @staticmethod
    def lambda_rule(model, i1, i2, t):
        if(i1 >= i2 or not (model.a[i1] == 1 and model.a[i2] == 1)):
            return pyo.Constraint.Skip
        # if patients not on same day
        if(sum(model.xParam[i1, k, t] for k in model.k) == 0 or sum(model.xParam[i2, k, t] for k in model.k) == 0):
            return pyo.Constraint.Skip
        return model.Lambda[i1, i2, t] + model.Lambda[i2, i1, t] == 1

    def extend_data(self, data):
        xParamDict = {}
        statusDict = {}
        for i in self.MPInstance.i:
            for t in self.MPInstance.t:
                # patient scheduled on day t
                if(sum(round(self.MPInstance.x[i, k, t].value) for k in self.MPInstance.k) == 1):
                    for k in range(1, self.MPInstance.K + 1):
                        statusDict[(i, k, t)] = Planner.FREE
                        xParamDict[(i, k, t)] = 1
                else:
                    for k in range(1, self.MPInstance.K + 1):
                        statusDict[(i, k, t)] = Planner.DISCARDED
                        xParamDict[(i, k, t)] = 0
        data[None]['xParam'] = xParamDict
        data[None]['status'] = statusDict

    def fix_SP_x_variables(self):
        print("Fixing x variables for phase two...")
        fixed = 0
        for k in self.MPInstance.k:
            for t in self.MPInstance.t:
                for i in self.MPInstance.i:
                    if(self.SPInstance.status[i, k, t] == Planner.DISCARDED):
                        self.SPInstance.x[i, k, t].fix(0)
                        fixed += 1
        print(str(fixed) + " x variables fixed.")

class SlowCompleteLagrangeanHeuristicPlanner(SlowCompleteHeuristicPlanner):

    @staticmethod
    def objective_function_MP(model):
        return sum(model.r[i] * model.x[i, k, t] for i in model.i for k in model.k for t in model.t) + 1 / (sum(model.An[alpha, t] for alpha in model.alpha for t in model.t) + sum(model.p[i] for i in model.i)) * sum(model.An[alpha, t] - sum(model.beta[alpha, i, t] * model.p[i] for i in model.t) for alpha in model.alpha for t in model.t)

    def define_objective_MP(self, model):
        model.objective = pyo.Objective(
            rule=self.objective_function_MP,
            sense=pyo.maximize)

    def define_model(self):
        self.define_MP()
        self.define_SP()

        self.define_objective_MP(self.MP_model)
        self.define_objective(self.SP_model)