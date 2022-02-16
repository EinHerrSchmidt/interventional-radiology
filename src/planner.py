from __future__ import division
from data_maker import DataMaker
import pyomo.environ as pyo


class Planner:

    def __init__(self):
        self.mainModel = pyo.AbstractModel()
        self.secondaryModel = pyo.AbstractModel()
        self.mainModelInstance = None
        self.secondaryModelInstance = None
        self.solver = pyo.SolverFactory('cplex')
        self.define_main_model()

        self.optimumF1 = None
        self.optimumF2 = None

    @staticmethod
    def main_model_objective_function(model):
        N = 1 / (1 + sum(model.r[i] for i in model.i))
        return model.F[1] + N * model.F[2]

    @staticmethod
    def secondary_model_objective_function(model):
        return model.F[3]

    # one surgery per patient, at most
    @staticmethod
    def single_surgery_rule(model, i):
        return sum(model.x[i, k, t] for k in model.k for t in model.t) <= 1

    # estimated surgery times cannot exceed operating room/surgical team time availability
    @staticmethod
    def surgery_availability_rule(model, k, t):
        return sum(model.p[i] * model.x[i, k, t] for i in model.i) <= model.s[k, t]

    @staticmethod
    def f1_rule(model):
        return model.F[1] <= sum(model.p[i] * model.x[i, k, t] for i in model.i for k in model.k for t in model.t)

    @staticmethod
    def f2_rule(model):
        return model.F[2] == sum(model.r[i] * model.x[i, k, t] for i in model.i for k in model.k for t in model.t)

    @staticmethod
    def f3_rule(model):
        return model.F[3] == sum(model.d[i] * model.x[i, k, t] for i in model.i for k in model.k for t in model.t)

    @staticmethod
    def optimum_f1_rule(model, optimumF1):
        return model.F[1] >= optimumF1

    @staticmethod
    def optimum_f2_rule(model, optimumF2):
        return model.F[2] >= optimumF2

    def define_common(self, model):
        model.I = pyo.Param(within=pyo.NonNegativeIntegers)
        model.K = pyo.Param(within=pyo.NonNegativeIntegers)
        model.T = pyo.Param(within=pyo.NonNegativeIntegers)

        model.i = pyo.RangeSet(1, model.I)
        model.k = pyo.RangeSet(1, model.K)
        model.t = pyo.RangeSet(1, model.T)

        model.x = pyo.Var(model.i,
                          model.k,
                          model.t,
                          domain=pyo.Binary)

        # variables F1, F2 and F3
        model.F = pyo.Var([1, 2, 3], domain=pyo.NonNegativeReals)

        # estimated surgery times
        model.p = pyo.Param(model.i)

        # urgency coefficient
        model.r = pyo.Param(model.i)

        # distance coefficient
        model.d = pyo.Param(model.i)

        # operating room/surgery team temporal availability
        model.s = pyo.Param(model.k, model.t)

        model.single_surgery_constraint = pyo.Constraint(
            model.i,
            rule=self.single_surgery_rule)
        model.surgery_time_constraint = pyo.Constraint(
            model.k,
            model.t,
            rule=self.surgery_availability_rule)
        model.f1_constraint = pyo.Constraint(
            rule=self.f1_rule)
        model.f2_constraint = pyo.Constraint(
            rule=self.f2_rule)

    # this model computes a solution with maximum urgency score among those having maximum
    # operating room usage
    def define_main_model(self):
        self.define_common(self.mainModel)
        self.mainModel.objective = pyo.Objective(
            rule=self.main_model_objective_function, sense=pyo.maximize)

    # this model computes a solution with minimum distance score, among those with maximum
    # operating room usage and - secondly - maximum urgency
    def define_secondary_model(self, optimumF1, optimumF2):
        self.define_common(self.secondaryModel)
        self.secondaryModel.objective = pyo.Objective(
            rule=self.secondary_model_objective_function, sense=pyo.minimize)

        self.secondaryModel.f3_constraint = pyo.Constraint(
            rule=self.f3_rule)
        self.secondaryModel.optimum_f1_constraint = pyo.Constraint(
            rule=lambda model, oF1=optimumF1: self.optimum_f1_rule(model, optimumF1))
        self.secondaryModel.optimum_f2_constraint = pyo.Constraint(
            rule=lambda model, oF2=optimumF2: self.optimum_f2_rule(model, optimumF2))

    def solve_main_model(self, data):
        self.mainModelInstance = self.mainModel.create_instance(data)

        self.solver.solve(self.mainModelInstance)
        self.optimumF1 = self.mainModelInstance.F[1].value
        self.optimumF2 = self.mainModelInstance.F[2].value

    def solve(self, data):
        self.solve_main_model(data)
        self.define_secondary_model(self.optimumF1, self.optimumF2)
        self.secondaryModelInstance = self.secondaryModel.create_instance(data)
        self.solver.solve(self.secondaryModelInstance)
