from __future__ import division
import re
import time
import pyomo.environ as pyo
from pyomo.opt import SolverStatus, TerminationCondition

from model import Patient

class Planner:

    DISCARDED = 0
    FREE = 1
    FIXED = 2

    def __init__(self, timeLimit, gap, solver):
        self.MPModel = pyo.AbstractModel()
        self.MPInstance = None
        self.SPModel = pyo.AbstractModel()
        self.SPInstance = None
        self.solver = pyo.SolverFactory(solver)
        if(solver == "cplex"):
            self.solver.options['timelimit'] = timeLimit
            self.solver.options['mipgap'] = gap
            self.solver.options['emphasis'] = "mip 2"
            self.solver.options['mip'] = "strategy probe 3"
            self.solver.options['mip'] = "cuts all 2"
        if(solver == "gurobi"):
            self.solver.options['timelimit'] = timeLimit
            self.solver.options['mipgap'] = gap
            self.solver.options['mipfocus'] = 2
        if(solver == "cbc"):
            self.solver.options['seconds'] = timeLimit
            self.solver.options['ratiogap'] = gap
            self.solver.options['heuristics'] = "on"
            # self.solver.options['round'] = "on"
            # self.solver.options['feas'] = "on"
            self.solver.options['cuts'] = "on"
            self.solver.options['preprocess'] = "on"
            # self.solver.options['printingOptions'] = "normal"

    @staticmethod
    def weighted_objective_function(model):
        return sum(model.r[i] * model.d[i] * model.x[i, k, t] for i in model.i for k in model.k for t in model.t)

    # one surgery per patient, at most
    @staticmethod
    def single_surgery_rule(model, i):
        return sum(model.x[i, k, t] for k in model.k for t in model.t) <= 1

    # estimated surgery times cannot exceed operating room/surgical team time availability
    @staticmethod
    def surgery_time_rule(model, k, t):
        return sum(model.p[i] * model.x[i, k, t] for i in model.i) <= model.s[k, t]

    # each patient must be assigned to a room matching her specialty need
    @staticmethod
    def specialty_assignment_rule(model, j, k, t):
        return sum(model.x[i, k, t] for i in model.i if model.specialty[i] == j) <= model.bigM[1] * model.tau[j, k, t]

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

    def define_gamma_variables(self):
        self.SPModel.gamma = pyo.Var(self.SPModel.i, domain=pyo.NonNegativeReals)

    def define_objective(self, model):
        model.objective = pyo.Objective(
            rule=self.weighted_objective_function,
            sense=pyo.maximize)

    # assign an anesthetist if and only if a patient needs her
    @staticmethod
    def anesthetist_assignment_rule(model, i, t):
        if(model.a[i] == 0):
            return pyo.Constraint.Skip
        return sum(model.beta[alpha, i, t] for alpha in model.alpha) == model.a[i] * sum(model.x[i, k, t] for k in model.k)

    # do not exceed anesthetist time in each day
    @staticmethod
    def anesthetist_time_rule(model, alpha, t):
        return sum(model.beta[alpha, i, t] * model.p[i] for i in model.i) <= model.An[alpha, t]

    # patients with same anesthetist on same day but different room cannot overlap
    @staticmethod
    def anesthetist_no_overlap_rule(model, i1, i2, k1, k2, t, alpha):
        if(model.status[i1, k1, t] == Planner.DISCARDED or model.status[i2, k2, t] == Planner.DISCARDED):
            return pyo.Constraint.Skip
        if(i1 == i2 or k1 == k2 or model.a[i1] * model.a[i2] == 0):
            return pyo.Constraint.Skip
        if(model.status[i1, k1, t] == Planner.FIXED and model.status[i2, k2, t] == Planner.FIXED
        and model.xParam[i1, k1, t] + model.xParam[i2, k2, t] < 2):
            return pyo.Constraint.Skip
        return model.gamma[i1] + model.p[i1] <= model.gamma[i2] + model.bigM[3] * (5 - model.beta[alpha, i1, t] - model.beta[alpha, i2, t] - model.x[i1, k1, t] - model.x[i2, k2, t] - model.Lambda[i1, i2, t])

    # precedence across rooms, same day
    @staticmethod
    def lambda_rule(model, i1, i2, t):
        if(i1 >= i2 or not (model.a[i1] == 1 and model.a[i2] == 1)):
            return pyo.Constraint.Skip
        i1AllDay = 0
        i2AllDay = 0
        for k in model.k:
            # if i1, i2 happen to be assigned to same room k on day t, then no need to use constraint
            if(model.status[i1, k, t] == Planner.FIXED and model.status[i2, k, t] == Planner.FIXED
            and model.xParam[i1, k, t] + model.xParam[i2, k, t] == 2):
                return pyo.Constraint.Skip
            if(model.status[i1, k, t] == Planner.FIXED or model.status[i1, k, t] == Planner.FREE):
                i1AllDay += 1
            if(model.status[i2, k, t] == Planner.FIXED or model.status[i2, k, t] == Planner.FREE):
                i2AllDay += 1
        if(i1AllDay == 0 or i2AllDay == 0):
            return pyo.Constraint.Skip
        return model.Lambda[i1, i2, t] + model.Lambda[i2, i1, t] == 1

    # ensure gamma plus operation time does not exceed end of day
    @staticmethod
    def end_of_day_rule(model, i, k, t):
        if(model.status[i, k, t] == Planner.DISCARDED):
            return pyo.Constraint.Skip
        if(model.xParam[i, k, t] == 0):
            return pyo.Constraint.Skip
        return model.gamma[i] + model.p[i] <= model.s[k, t]

    # ensure that patient i1 terminates operation before i2, if y_12kt = 1
    @staticmethod
    def time_ordering_precedence_rule(model, i1, i2, k, t):
        if(model.status[i1, k, t] == Planner.DISCARDED or model.status[i2, k, t] == Planner.DISCARDED):
            return pyo.Constraint.Skip
        if(i1 == i2):
            return pyo.Constraint.Skip
        if(model.status[i1, k, t] == Planner.FIXED and model.status[i2, k, t] == Planner.FIXED
        and model.xParam[i1, k, t] + model.xParam[i2, k, t] < 2):
            return pyo.Constraint.Skip
        return model.gamma[i1] + model.p[i1] <= model.gamma[i2] + model.bigM[5] * (3 - model.x[i1, k, t] - model.x[i2, k, t] - model.y[i1, i2, k, t])

    @staticmethod
    def start_time_ordering_priority_rule(model, i1, i2, k, t):
        if(model.status[i1, k, t] == Planner.DISCARDED or model.status[i2, k, t] == Planner.DISCARDED):
            return pyo.Constraint.Skip
        if(i1 == i2 or model.u[i1, i2] == 0 ):
            return pyo.Constraint.Skip
        if(model.status[i1, k, t] == Planner.FIXED and model.status[i2, k, t] == Planner.FIXED
            and model.xParam[i1, k, t] + model.xParam[i2, k, t] < 2):
            return pyo.Constraint.Skip
        return model.gamma[i1] * model.u[i1, i2] <= model.gamma[i2] * (1 - model.u[i2, i1]) + model.bigM[2] * (2 - model.x[i1, k, t] - model.x[i2, k, t])

    # either i1 comes before i2 in (k, t) or i2 comes before i1 in (k, t)
    @staticmethod
    def exclusive_precedence_rule(model, i1, i2, k, t):
        if(model.specialty[i1] != model.specialty[i2]):
            return pyo.Constraint.Skip
        if(model.status[i1, k, t] == Planner.DISCARDED or model.status[i2, k, t] == Planner.DISCARDED):
            return pyo.Constraint.Skip
        if(i1 >= i2):
            return pyo.Constraint.Skip
        if(model.status[i1, k, t] == Planner.FIXED and model.status[i2, k, t] == Planner.FIXED
           and model.xParam[i1, k, t] + model.xParam[i2, k, t] < 2):
            return pyo.Constraint.Skip
        return model.y[i1, i2, k, t] + model.y[i2, i1, k, t] == 1

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

    def define_lambda_variables(self):
        self.SPModel.Lambda = pyo.Var(self.SPModel.i,
                                    self.SPModel.i,
                                    self.SPModel.t,
                                    domain=pyo.Binary)

    def define_y_variables(self):
        self.SPModel.y = pyo.Var(self.SPModel.i,
                               self.SPModel.i,
                               self.SPModel.k,
                               self.SPModel.t,
                               domain=pyo.Binary)

    def define_x_parameters(self):
        self.SPModel.xParam = pyo.Param(self.SPModel.i,
                              self.SPModel.k,
                              self.SPModel.t)

    def define_status_parameters(self):
        self.SPModel.status = pyo.Param(self.SPModel.i,
                              self.SPModel.k,
                              self.SPModel.t)

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

    def define_anesthetist_no_overlap_constraint(self):
        self.SPModel.anesthetist_no_overlap_constraint = pyo.Constraint(
            self.SPModel.i,
            self.SPModel.i,
            self.SPModel.k,
            self.SPModel.k,
            self.SPModel.t,
            self.SPModel.alpha,
            rule=self.anesthetist_no_overlap_rule)

    def define_lambda_constraint(self):
        self.SPModel.lambda_constraint = pyo.Constraint(
            self.SPModel.i,
            self.SPModel.i,
            self.SPModel.t,
            rule=self.lambda_rule)

    def define_end_of_day_constraint(self):
        self.SPModel.end_of_day_constraint = pyo.Constraint(
            self.SPModel.i,
            self.SPModel.k,
            self.SPModel.t,
            rule=self.end_of_day_rule)

    def define_priority_constraint(self):
        self.SPModel.priority_constraint = pyo.Constraint(
            self.SPModel.i,
            self.SPModel.i,
            self.SPModel.k,
            self.SPModel.t,
            rule=self.start_time_ordering_priority_rule)

    def define_precedence_constraint(self):
        self.SPModel.precedence_constraint = pyo.Constraint(
            self.SPModel.i,
            self.SPModel.i,
            self.SPModel.k,
            self.SPModel.t,
            rule=self.time_ordering_precedence_rule)

    def define_exclusive_precedence_constraint(self):
        self.SPModel.exclusive_precedence_constraint = pyo.Constraint(
            self.SPModel.i,
            self.SPModel.i,
            self.SPModel.k,
            self.SPModel.t,
            rule=self.exclusive_precedence_rule)

    def define_common_components(self, model):
        self.define_sets(model)
        self.define_x_variables(model)
        self.define_parameters(model)
        self.define_single_surgery_constraints(model)
        self.define_surgery_time_constraints(model)
        self.define_specialty_assignment_constraints(model)
        self.define_anesthetists_number_param(model)
        self.define_anesthetists_range_set(model)
        self.define_beta_variables(model)
        self.define_anesthetists_availability(model)
        self.define_anesthetist_assignment_constraint(model)
        self.define_anesthetist_time_constraint(model)

    def define_MP(self):
        self.define_common_components(self.MPModel)
        self.define_objective(self.MPModel)

    def define_SP(self):
        self.define_common_components(self.SPModel)

        # SP's components
        self.define_x_parameters()
        self.define_status_parameters()
        self.define_lambda_variables()
        self.define_y_variables()
        self.define_gamma_variables()
        self.define_anesthetist_no_overlap_constraint()
        self.define_lambda_constraint()
        self.define_end_of_day_constraint()
        self.define_priority_constraint()
        self.define_precedence_constraint()
        self.define_exclusive_precedence_constraint()

        self.define_objective(self.SPModel)

    def solve_model(self, data):
        self.define_MP()
        self.define_SP()
        MPBuildingTime = self.create_MP_instance(data)

        # MP
        print("Solving MP instance...")
        self.MPModel.results = self.solver.solve(self.MPInstance, tee=True)
        print("\nMP instance solved.")
        MPSolverTime = self.solver._last_solve_time
        MPTimeLimitHit = self.MPModel.results.solver.termination_condition in [TerminationCondition.maxTimeLimit]
        resultsAsString = str(self.MPModel.results)
        MPUpperBound = float(re.search("Upper bound: -*(\d*\.\d*)", resultsAsString).group(1))

        # SP
        SPBuildingTime = self.create_SP_instance(data)

        self.fix_SP_x_variables()
        print("Solving SP instance...")
        self.SPModel.results = self.solver.solve(self.SPInstance, tee=True)
        print("SP instance solved.")
        SPSolverTime = self.solver._last_solve_time
        SPTimeLimitHit = self.SPModel.results.solver.termination_condition in [TerminationCondition.maxTimeLimit]

        statusOk = self.SPModel.results.solver.status == SolverStatus.ok

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
                    "objectiveFunctionLB": self.compute_objective_function_LB()}

        print(self.SPModel.results)
        return runInfo

    def compute_objective_function_LB(self):
        value = 0
        for i in self.MPInstance.i:
            for k in self.MPInstance.k:
                for t in self.MPInstance.t:
                    if(round(self.MPInstance.x[i, k, t].value) == 1 and self.MPInstance.a[i] == 0):
                        value += self.MPInstance.r[i]

        for t in self.MPInstance.t:
            dict = {}
            for k in self.MPInstance.k:
                roomKPatients = []
                for i in self.MPInstance.i:
                    if(round(self.MPInstance.x[i, k, t].value) == 1 and self.MPInstance.a[i] == 1):
                        roomKPatients.append((self.MPInstance.r[i], self.MPInstance.p[i]))
                roomKPatients.sort(key=lambda x: x[0], reverse=True)
                dict[(k, t)] = roomKPatients
            for a in self.MPInstance.alpha:
                maxGain = 0
                bestRoom = 0
                patientsToDelete = 0
                for k in self.MPInstance.k:
                    gain = 0
                    anesthetistTime = self.MPInstance.An[a, t]
                    toDelete = 0
                    for patient in dict[(k, t)]:
                        if(anesthetistTime >= patient[1]):
                            anesthetistTime = anesthetistTime - patient[1]
                            gain = gain + patient[0]
                            toDelete = toDelete + 1
                        else:
                            break
                    if(gain > maxGain):
                        maxGain = gain
                        bestRoom = k
                        patientsToDelete = toDelete
                if(maxGain == 0):
                    break
                value = value + maxGain
                updatedRoom = dict[(bestRoom, t)]
                del updatedRoom[:patientsToDelete]
                dict[(bestRoom, t)] = updatedRoom

        return value

    def extend_data(self, data):
        xParamDict = {}
        statusDict = {}
        for i in range(1, self.MPInstance.I + 1):
            for k in range(1, self.MPInstance.K + 1):
                for t in range(1, self.MPInstance.T + 1):
                    if(round(self.MPInstance.x[i, k, t].value) == 1 and self.MPInstance.a[i] == 1):
                        statusDict[(i, k, t)] = Planner.FREE
                        xParamDict[(i, k, t)] = 1
                    elif(round(self.MPInstance.x[i, k, t].value) == 1 and self.MPInstance.a[i] == 0):
                        statusDict[(i, k, t)] = Planner.FIXED
                        xParamDict[(i, k, t)] = 1
                    else:
                        statusDict[(i, k, t)] = Planner.DISCARDED
                        xParamDict[(i, k, t)] = 0
        data[None]['xParam'] = xParamDict
        data[None]['status'] = statusDict

    def create_MP_instance(self, data):
        print("Creating MP instance...")
        t = time.time()
        self.MPInstance = self.MPModel.create_instance(data)
        elapsed = (time.time() - t)
        print("MP instance created in " + str(round(elapsed, 2)) + "s")
        return elapsed

    def create_SP_instance(self, data):
        self.extend_data(data)
        print("Creating SP instance...")
        t = time.time()
        self.SPInstance = self.SPModel.create_instance(data)
        elapsed = (time.time() - t)
        print("SP instance created in " + str(round(elapsed, 2)) + "s")
        return elapsed

    def fix_SP_x_variables(self):
        print("Fixing x variables for phase two...")
        fixed = 0
        for k in self.MPInstance.k:
            for t in self.MPInstance.t:
                for i1 in self.MPInstance.i:
                    if(round(self.MPInstance.x[i1, k, t].value) == 1 and self.MPInstance.a[i1] == 0):
                        self.SPInstance.x[i1, k, t].fix(1)
                        fixed += 1
                    if(round(self.MPInstance.x[i1, k, t].value) == 0):
                        self.SPInstance.x[i1, k, t].fix(0)
                        fixed += 1
        print(str(fixed) + " x variables fixed.")

    def extract_solution(self):
        if(self.SPModel.results.solver.status != SolverStatus.ok):
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
                        delayWeight = self.SPInstance.d[i]
                        patients.append(Patient(i, priority, k, specialty, t, p, c, precedence, delayWeight, a, anesthetist, order))
                patients.sort(key=lambda x: x.order)
                dict[(k, t)] = patients
        return dict
