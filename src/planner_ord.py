from __future__ import division
from matplotlib.pyplot import semilogx
import pyomo.environ as pyo
import pyomo.gdp as pyogdp


class Planner:

    def __init__(self):
        self.model = pyo.AbstractModel()
        self.modelInstance = None
        self.solver = pyo.SolverFactory('cplex')
        self.define_model()

    @staticmethod
    def objective_function(model):
        return sum(model.r[i] * model.x[i, k, t] for i in model.i for k in model.k for t in model.t)

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

    # assign an anesthetist if and only if a patient needs her
    @staticmethod
    def anesthetist_assignment_rule(model, i, k, t):
        return sum(model.beta[alpha, i, k, t]
                   for alpha in model.alpha) == model.a[i]*model.x[i, k, t]

    # do not exceed anesthetist time in each day
    @staticmethod
    def anesthetist_time_rule(model, alpha, t):
        return sum(model.beta[alpha, i, k, t] * model.p[i]
                   for i in model.i for k in model.k) <= model.An[alpha, t]

    @staticmethod
    def anesthetist_no_overlap_rule1(model, i1, i2, k1, k2, t, alpha):
        if(i1 == i2 or k1 == k2 or model.a[i1] * model.a[i2] == 0):
            return pyo.Constraint.Skip
        return sum(model.y[i3, i1, k1, t] * model.p[i3] for i3 in model.i) - (sum(model.y[i3, i2, k2, t] * model.p[i3] for i3 in model.i) + model.p[i2]) >= - model.bigM[2] * (1 - model.Lambda[i2, i1]) - model.bigM[3] * (2 - model.beta[alpha, i1, k1, t] - model.beta[alpha, i2, k2, t])

    @staticmethod
    def anesthetist_no_overlap_rule2(model, i1, i2, k1, k2, t, alpha):
        if(i1 == i2 or k1 == k2 or model.a[i1] * model.a[i2] == 0):
            return pyo.Constraint.Skip
        return sum(model.y[i3, i2, k2, t] * model.p[i3] for i3 in model.i) - (sum(model.y[i3, i1, k1, t] * model.p[i3] for i3 in model.i) + model.p[i1]) >= - model.bigM[2] * (1 - model.Lambda[i1, i2]) - model.bigM[3] * (2 - model.beta[alpha, i1, k1, t] - model.beta[alpha, i2, k2, t])

    @staticmethod
    def lambda_rule(model, i1, i2):
        if(i1 >= i2):
            return pyo.Constraint.Skip
        return model.Lambda[i1, i2] + model.Lambda[i2, i1] == 1
    
    # @staticmethod
    # def single_lambda_rule(model, i1, i2):
    #     if(i1 >= i2):
    #         return pyo.Constraint.Skip
    #     return model.Lambda[i1, i2] + model.Lambda[i2, i1] == 1

    # ensure that patient i1 terminates operation before i2, if y_12kt = 1
    @staticmethod
    def precedence_rule(model, i1, i2, k, t):
        if(i1 == i2):
            return pyo.Constraint.Skip
        return model.gamma[i1] <= model.gamma[i2] - 1 + model.bigM[5] * (1 - model.y[i1, i2, k, t])
    
    # to ensure ordering on gamma
    @staticmethod
    def absolute_value_rule1(model, i1, i2):
        if(i1 == i2):
            return pyo.Constraint.Skip
        return model.gamma[i1] - model.gamma[i2] >= 1 - model.Lambda1[i1, i2] * model.bigM[5]

    # to ensure ordering on gamma
    @staticmethod
    def absolute_value_rule2(model, i1, i2):
        if(i1 == i2):
            return pyo.Constraint.Skip
        return model.gamma[i1] - model.gamma[i2] <= - 1 + (1 - model.Lambda1[i1, i2]) * model.bigM[5]

    #to ensure ordering on gamma
    @staticmethod
    def gamma_ordering_rule(model, i1, i2):
        if(i1 >= i2):
            return pyo.Constraint.Skip
        return model.Lambda1[i1, i2] + model.Lambda1[i2, i1] == 1

    # Covid patients after non-Covid patients
    @staticmethod
    def covid_precedence_rule(model, i1, i2, k, t):
        if(i1 == i2):
            return pyo.Constraint.Skip
        return model.y[i1, i2, k, t] >= (1 - model.c[i1]) * model.c[i2]

    # either i1 comes before i2 in (k, t) or i2 comes before i1 in (k, t)
    @staticmethod
    def exclusive_precedence_rule(model, i1, i2, k, t):
        if(i1 >= i2):
            return pyo.Constraint.Skip
        return model.y[i1, i2, k, t] + model.y[i2, i1, k, t] == 1

    def define_model(self):
        self.model.I = pyo.Param(within=pyo.NonNegativeIntegers)  # patients
        self.model.J = pyo.Param(within=pyo.NonNegativeIntegers)  # specialties
        self.model.K = pyo.Param(within=pyo.NonNegativeIntegers)  # op. rooms
        self.model.T = pyo.Param(within=pyo.NonNegativeIntegers)  # week's days
        self.model.A = pyo.Param(within=pyo.NonNegativeIntegers)  # anesthetists
        self.model.M = pyo.Param(within=pyo.NonNegativeIntegers)  # big Ms

        self.model.i = pyo.RangeSet(1, self.model.I)
        self.model.j = pyo.RangeSet(1, self.model.J)
        self.model.k = pyo.RangeSet(1, self.model.K)
        self.model.t = pyo.RangeSet(1, self.model.T)
        self.model.alpha = pyo.RangeSet(1, self.model.A)
        self.model.bm = pyo.RangeSet(1, self.model.M)

        self.model.x = pyo.Var(self.model.i,
                               self.model.k,
                               self.model.t,
                               domain=pyo.Binary)

        self.model.y = pyo.Var(self.model.i,
                               self.model.i,
                               self.model.k,
                               self.model.t,
                               domain=pyo.Binary)

        self.model.beta = pyo.Var(self.model.alpha,
                                  self.model.i,
                                  self.model.k,
                                  self.model.t,
                                  domain=pyo.Binary)

        self.model.gamma = pyo.Var(self.model.i,
                                   domain=pyo.NonNegativeIntegers)

        self.model.Lambda = pyo.Var(self.model.i,
                                    self.model.i,
                                    domain=pyo.Binary)

        self.model.Lambda1 = pyo.Var(self.model.i,
                                     self.model.i,
                                     domain=pyo.Binary)

        # estimated surgery time
        self.model.p = pyo.Param(self.model.i)

        # Maximum Time Before Treatment
        # self.model.m = pyo.Param(self.model.i)

        # referral day
        # self.model.l = pyo.Param(self.model.i)

        # time elapsed in waiting list at planning time
        # self.model.L = pyo.Param(self.model.i)

        # priority coefficient
        self.model.r = pyo.Param(self.model.i)

        # operating room/surgery team temporal availability
        self.model.s = pyo.Param(self.model.k, self.model.t)

        # anesthetists' available time
        self.model.An = pyo.Param(self.model.alpha, self.model.t)

        # need for anesthesia
        self.model.a = pyo.Param(self.model.i)

        # Covid infection
        self.model.c = pyo.Param(self.model.i)

        # medical specialty for each (k, t)
        self.model.tau = pyo.Param(self.model.j, self.model.k, self.model.t)

        # specialty needed by each patient
        self.model.specialty = pyo.Param(self.model.i)

        # big Ms
        self.model.bigM = pyo.Param(self.model.bm)

        self.model.single_surgery_constraint = pyo.Constraint(
            self.model.i,
            rule=self.single_surgery_rule)
        self.model.surgery_time_constraint = pyo.Constraint(
            self.model.k,
            self.model.t,
            rule=self.surgery_time_rule)
        self.model.specialty_assignment_constraint = pyo.Constraint(
            self.model.j,
            self.model.k,
            self.model.t,
            rule=self.specialty_assignment_rule)
        self.model.anesthetist_assignment_constraint = pyo.Constraint(
            self.model.i,
            self.model.k,
            self.model.t,
            rule=self.anesthetist_assignment_rule)
        self.model.anesthetist_time_constraint = pyo.Constraint(
            self.model.alpha,
            self.model.t,
            rule=self.anesthetist_time_rule)
        self.model.anesthetist_no_overlap_constraint1 = pyo.Constraint(
            self.model.i,
            self.model.i,
            self.model.k,
            self.model.k,
            self.model.t,
            self.model.alpha,
            rule=self.anesthetist_no_overlap_rule1)
        self.model.anesthetist_no_overlap_constraint2 = pyo.Constraint(
            self.model.i,
            self.model.i,
            self.model.k,
            self.model.k,
            self.model.t,
            self.model.alpha,
            rule=self.anesthetist_no_overlap_rule2)
        self.model.lambda_constraint = pyo.Constraint(
            self.model.i,
            self.model.i,
            rule=self.lambda_rule)
        # self.model.single_lambda_constraint = pyo.Constraint(
        #     self.model.i,
        #     self.model.i,
        #     rule=self.single_lambda_rule)
        self.model.precedence_constraint = pyo.Constraint(
            self.model.i,
            self.model.i,
            self.model.k,
            self.model.t,
            rule=self.precedence_rule)
        self.model.absolute_value_constraint1 = pyo.Constraint(
            self.model.i,
            self.model.i,
            rule=self.absolute_value_rule1)
        self.model.absolute_value_constraint2 = pyo.Constraint(
            self.model.i,
            self.model.i,
            rule=self.absolute_value_rule2)
        self.model.gamma_ordering_constraint = pyo.Constraint(
            self.model.i,
            self.model.i,
            rule=self.gamma_ordering_rule)
        self.model.covid_precedence_constraint = pyo.Constraint(
            self.model.i,
            self.model.i,
            self.model.k,
            self.model.t,
            rule=self.covid_precedence_rule)
        self.model.exclusive_precedence_constraint = pyo.Constraint(
            self.model.i,
            self.model.i,
            self.model.k,
            self.model.t,
            rule=self.exclusive_precedence_rule)

        self.model.objective = pyo.Objective(
            rule=self.objective_function, sense=pyo.maximize)

    def fix_variables_and_deactivate_constraints(self):
        deactivated_constraints = 0
        fixed_variables = 0
        for i1 in self.modelInstance.i:
            for i2 in self.modelInstance.i:
                for k in self.modelInstance.k:
                    for t in self.modelInstance.t:
                        if(self.modelInstance.specialty[i1] != self.modelInstance.specialty[i2] or i1 == i2):
                            self.modelInstance.y[i1, i2, k, t].fix(0)
                            fixed_variables += 1
                            if(i1 < i2):
                                self.modelInstance.exclusive_precedence_constraint[i1, i2, k, t].deactivate()
                                deactivated_constraints += 1
                            if(i1 != i2):
                                self.modelInstance.covid_precedence_constraint[i1, i2, k, t].deactivate()
                                self.modelInstance.precedence_constraint[i1, i2, k, t].deactivate()
                                deactivated_constraints += 2
                        if(self.modelInstance.c[i1] == 1 or self.modelInstance.c[i2] == 0):
                            if(i1 != i2):
                                self.modelInstance.covid_precedence_constraint[i1, i2, k, t].deactivate()
                                deactivated_constraints += 1

        for alpha in self.modelInstance.alpha:
            for i in self.modelInstance.i:
                for k in self.modelInstance.k:
                    for t in self.modelInstance.t:
                        if(self.modelInstance.a[i] == 0):
                            self.modelInstance.beta[alpha, i, k, t].fix(0)
                            fixed_variables += 1

        for i in self.modelInstance.i:
            for k in self.modelInstance.k:
                for t in self.modelInstance.t:
                    spec = self.modelInstance.specialty[i]
                    # if(self.modelInstance.tau[spec, k, t] == 0):
                    #     self.modelInstance.x[i, k, t].fix(0)
                    #     fixed_variables += 1
                    if(self.modelInstance.a[i] == 0):
                        self.modelInstance.anesthetist_assignment_constraint[i, k, t].deactivate()
                        deactivated_constraints += 1

        print("Deactivated constraints: " + str(deactivated_constraints))
        print("Fixed variables: " + str(fixed_variables))

    def solve_model(self):
        # self.fix_variables_and_deactivate_constraints()
        self.solver.solve(self.modelInstance)
        print("Model instance solved")

    def create_model_instance(self, data):
        self.modelInstance = self.model.create_instance(data)
        print("Model instance created")
