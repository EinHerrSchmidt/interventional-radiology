from __future__ import division
from matplotlib.pyplot import semilogx
import pyomo.environ as pyo

from model import Patient


class Planner:

    def __init__(self):
        self.model = pyo.AbstractModel()
        self.modelInstance = None
        self.solver = pyo.SolverFactory('cplex')
        self.solver.options['timelimit'] = 900
        # self.solver.options['mipgap'] = 0.5
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
    # @staticmethod
    # def anesthetist_assignment_rule(model, i, k, t):
    #     return sum(model.beta[alpha, i, k, t]
    #                for alpha in model.alpha) == model.a[i]*model.x[i, k, t]

    # do not exceed anesthetist time in each day
    #@staticmethod
    #def anesthetist_time_rule(model, alpha, t):
    #    return sum(model.beta[alpha, i, k, t] * model.p[i]
    #               for i in model.i for k in model.k) <= model.An[alpha, t]

    # patients with same anesthetist on same day but different room cannot overlap
    # @staticmethod
    # def anesthetist_no_overlap_rule(model, i1, i2, k1, k2, t, alpha):
    #     if(i1 == i2 or k1 == k2 or model.a[i1] * model.a[i2] == 0):
    #         return pyo.Constraint.Skip
    #     return model.gamma[i1, k1, t] + model.p[i1] <= model.gamma[i2, k2, t] + model.bigM[2] * (5 - model.beta[alpha, i1, k1, t] - model.beta[alpha, i2, k2, t] - model.x[i1,k1,t] - model.x[i2,k2,t] - model.Lambda[i1, i2, t])

    # precedence across rooms, same day
    # @staticmethod
    # def lambda_rule(model, i1, i2, t):
    #     if(i1 >= i2):
    #         return pyo.Constraint.Skip
    #     return model.Lambda[i1, i2, t] + model.Lambda[i2, i1, t] == 1

    # ensure that patient i1 terminates operation before i2, if y_12kt = 1
    @staticmethod
    def precedence_rule(model, i1, i2, k, t):
        if(i1 == i2):
            return pyo.Constraint.Skip
        return model.gamma[i1, k, t] <= model.gamma[i2, k, t] - 1 + model.bigM[5] * (3 - model.x[i1, k, t] - model.x[i2, k, t] - model.y[i1, i2, k, t])

    # Covid patients after non-Covid patients
    @staticmethod
    def covid_precedence_rule(model, i1, i2, k, t):
        if(i1 == i2 or not (model.c[i1] == 0 and model.c[i2] == 1 )):
            return pyo.Constraint.Skip
        return model.gamma[i1, k, t] * (1 - model.c[i1]) <= model.gamma[i2, k, t] *  model.c[i2] + model.bigM[3] * (1 - model.c[i2])

    # either i1 comes before i2 in (k, t) or i2 comes before i1 in (k, t)
    @staticmethod
    def exclusive_precedence_rule(model, i1, i2, k, t):
        if(i1 >= i2):
            return pyo.Constraint.Skip
        return model.y[i1, i2, k, t] + model.y[i2, i1, k, t] == 1

    # if patient i has specialty 1 and needs anesthesia, then he cannot be in room 2
    @staticmethod
    def anesthesia_S1_rule(model, i):
        if(model.a[i] * model.rho[i, 1] == 0):
            return pyo.Constraint.Skip
        return sum(model.x[i, 2, t] * model.a[i] for t in model.t) <= 1 - model.rho[i, 1]

    # if patient i has specialty 2 and needs anesthesia, then he cannot be in room 4
    @staticmethod
    def anesthesia_S3_rule(model, i):
        if(model.a[i] * model.rho[i, 2] == 0):
            return pyo.Constraint.Skip
        return sum(model.x[i, 4, t] * model.a[i] for t in model.t) <= 1 - model.rho[i, 2]

    # patients needing anesthesia cannot exceed anesthesia total time in each room
    @staticmethod
    def anesthesia_total_time_rule(model, k, t):
        #if(model.a[i] * model.rho[i, 2] == 0):
        #    return pyo.Constraint.Skip
        return sum(model.x[i, k, t] * model.p[i] * model.a[i] for i in model.i) <= 240


    def define_model(self):
        self.model.I = pyo.Param(within=pyo.NonNegativeIntegers)  # patients
        self.model.J = pyo.Param(within=pyo.NonNegativeIntegers)  # specialties
        self.model.K = pyo.Param(
            within=pyo.NonNegativeIntegers)  # operating rooms
        self.model.T = pyo.Param(
            within=pyo.NonNegativeIntegers)  # horizon days
        # self.model.A = pyo.Param(
        #     within=pyo.NonNegativeIntegers)  # anesthetists
        self.model.M = pyo.Param(within=pyo.NonNegativeIntegers)  # big Ms

        self.model.i = pyo.RangeSet(1, self.model.I)
        self.model.j = pyo.RangeSet(1, self.model.J)
        self.model.k = pyo.RangeSet(1, self.model.K)
        self.model.t = pyo.RangeSet(1, self.model.T)
        # self.model.alpha = pyo.RangeSet(1, self.model.A)
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

        # self.model.beta = pyo.Var(self.model.alpha,
        #                           self.model.i,
        #                           self.model.k,
        #                           self.model.t,
        #                           domain=pyo.Binary)

        self.model.gamma = pyo.Var(self.model.i,
                                    self.model.k,
                                    self.model.t,
                                   domain=pyo.NonNegativeIntegers)

        # self.model.Lambda = pyo.Var(self.model.i,
        #                             self.model.i,
        #                             self.model.t,
        #                            domain=pyo.Binary)

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
        # self.model.An = pyo.Param(self.model.alpha, self.model.t)

        # need for anesthesia
        self.model.a = pyo.Param(self.model.i)

        # Covid infection
        self.model.c = pyo.Param(self.model.i)

        # medical specialty for each (k, t)
        self.model.tau = pyo.Param(self.model.j, self.model.k, self.model.t)

        # specialty needed by each patient
        self.model.specialty = pyo.Param(self.model.i)

        self.model.rho = pyo.Param(self.model.i, self.model.j)

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
        # self.model.anesthetist_assignment_constraint = pyo.Constraint(
        #     self.model.i,
        #     self.model.k,
        #     self.model.t,
        #     rule=self.anesthetist_assignment_rule)
        # self.model.anesthetist_time_constraint = pyo.Constraint(
        #     self.model.alpha,
        #     self.model.t,
        #     rule=self.anesthetist_time_rule)
        # self.model.anesthetist_no_overlap_constraint = pyo.Constraint(
        #     self.model.i,
        #     self.model.i,
        #     self.model.k,
        #     self.model.k,
        #     self.model.t,
        #     self.model.alpha,
        #     rule=self.anesthetist_no_overlap_rule)
        # self.model.lambda_constraint = pyo.Constraint(
        #     self.model.i,
        #     self.model.i,
        #     self.model.t,
        #     rule=self.lambda_rule)
        self.model.precedence_constraint = pyo.Constraint(
            self.model.i,
            self.model.i,
            self.model.k,
            self.model.t,
            rule=self.precedence_rule)
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
        self.model.anesthesia_S1_constraint = pyo.Constraint(
            self.model.i,
            rule=self.anesthesia_S1_rule)
        self.model.anesthesia_S3_constraint = pyo.Constraint(
            self.model.i,
            rule=self.anesthesia_S3_rule)
        self.model.anesthesia_total_time_constraint = pyo.Constraint(
            self.model.k,
            self.model.t,
            rule=self.anesthesia_total_time_rule)
            

        self.model.objective = pyo.Objective(
            rule=self.objective_function, sense=pyo.maximize)

    def solve_model(self):
        self.model.results = self.solver.solve(self.modelInstance, tee=True)
        print(self.model.results)

    def create_model_instance(self, data):
        self.modelInstance = self.model.create_instance(data)
        print("Model instance created")

    def extract_solution(self):
        dict = {}
        for k in self.modelInstance.k:
            for t in self.modelInstance.t:
                patients = []
                for i in self.modelInstance.i:
                        if(self.modelInstance.x[i, k, t].value == 1):
                            p = self.modelInstance.p[i]
                            c = self.modelInstance.c[i]
                            a = self.modelInstance.a[i]
                            anesthetist = 0

                            order = self.modelInstance.gamma[i, k, t].value
                            specialty = self.modelInstance.specialty[i]
                            priority = self.modelInstance.r[i]
                            patients.append(Patient(i, priority, k, specialty, t, p, c, a, anesthetist, order))
                patients.sort(key=lambda x: x.order)
                dict[(k, t)] = patients
        return dict

    def print_solution(self):
        solution = self.extract_solution()
        for t in self.modelInstance.t:
            for k in self.modelInstance.k:
                print("Day: " + str(t) + "; Operating Room: S" + str(k) + "\n")
                for patient in solution[(k,t)]:
                    print(patient)
                print("\n")