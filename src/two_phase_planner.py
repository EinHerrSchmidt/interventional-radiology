from __future__ import division
from enum import Enum
import time
import pyomo.environ as pyo
import plotly.express as px
import pandas as pd
import datetime

from model import Patient


class ModelType(Enum):
    START_TIME_ORDERING = 1
    SIMPLE_ORDERING = 2


class Planner:

    def __init__(self, timeLimit, modelType, solver):
        self.model = pyo.AbstractModel()
        self.modelInstance = None
        self.modelInstancePhaseTwo = None
        self.solver = pyo.SolverFactory(solver)
        if(solver == "cplex"):
            self.solver.options['timelimit'] = timeLimit
        if(solver == "cbc"):
            self.solver.options['seconds'] = timeLimit
            # self.solver.options['threads'] = 10
            # self.solver.options['heuristics'] = "off"
            # self.solver.options['round'] = "on"
            # self.solver.options['feas'] = "off"
            # self.solver.options['passF'] = 250
            # self.solver.options['cuts'] = "off"
            # self.solver.options['ratioGAP'] = 0.05
            # self.solver.options['preprocess'] = "on"
            # self.solver.options['printingOptions'] = "normal"

        self.modelType = modelType
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

    # patients with same anesthetist on same day but different room cannot overlap
    @staticmethod
    def anesthetist_no_overlap_rule(model, i1, i2, k1, k2, t, alpha):
        if(i1 == i2 or k1 == k2 or model.a[i1] * model.a[i2] == 0):
            return pyo.Constraint.Skip
        return model.gamma[i1] + model.p[i1] <= model.gamma[i2] + model.bigM[3] * (3 - model.beta[alpha, i1, k1, t] - model.beta[alpha, i2, k2, t] - model.Lambda[i1, i2, t])

    # precedence across rooms, same day
    @staticmethod
    def lambda_rule(model, i1, i2, t):
        if(i1 >= i2):
            return pyo.Constraint.Skip
        return model.Lambda[i1, i2, t] + model.Lambda[i2, i1, t] == 1

    # ensure gamma plus operation time does not exceed end of day
    @staticmethod
    def end_of_day_rule(model, i, k, t):
        return model.gamma[i] + model.p[i] <= model.s[k, t] + model.bigM[4] * (1 - model.x[i, k, t])

    # ensure that patient i1 terminates operation before i2, if y_12kt = 1
    @staticmethod
    def time_ordering_precedence_rule(model, i1, i2, k, t):
        if(i1 == i2):
            return pyo.Constraint.Skip
        return model.gamma[i1] + model.p[i1] <= model.gamma[i2] + model.bigM[5] * (3 - model.x[i1, k, t] - model.x[i2, k, t] - model.y[i1, i2, k, t])

    # Covid patients after non-Covid patients
    @staticmethod
    def start_time_ordering_covid_precedence_rule(model, i1, i2, k, t):
        if(i1 == i2 or not (model.c[i1] == 0 and model.c[i2] == 1)):
            return pyo.Constraint.Skip
        return model.gamma[i1] * (1 - model.c[i1]) <= model.gamma[i2] * model.c[i2] + model.bigM[2] * (3 - model.c[i2] - model.x[i1, k, t] - model.x[i2, k, t])

    # either i1 comes before i2 in (k, t) or i2 comes before i1 in (k, t)
    @staticmethod
    def exclusive_precedence_rule(model, i1, i2, k, t):
        if(i1 >= i2):
            return pyo.Constraint.Skip
        return model.y[i1, i2, k, t] + model.y[i2, i1, k, t] == 1

    def define_variables_and_params_phase_one(self):
        self.model.I = pyo.Param(within=pyo.NonNegativeIntegers)
        self.model.J = pyo.Param(within=pyo.NonNegativeIntegers)
        self.model.K = pyo.Param(within=pyo.NonNegativeIntegers)
        self.model.T = pyo.Param(within=pyo.NonNegativeIntegers)
        self.model.M = pyo.Param(within=pyo.NonNegativeIntegers)

        self.model.i = pyo.RangeSet(1, self.model.I)
        self.model.j = pyo.RangeSet(1, self.model.J)
        self.model.k = pyo.RangeSet(1, self.model.K)
        self.model.t = pyo.RangeSet(1, self.model.T)
        self.model.bm = pyo.RangeSet(1, self.model.M)

        self.model.x = pyo.Var(self.model.i,
                               self.model.k,
                               self.model.t,
                               domain=pyo.Binary)

        self.model.p = pyo.Param(self.model.i)
        # self.model.m = pyo.Param(self.model.i)
        # self.model.l = pyo.Param(self.model.i)
        # self.model.L = pyo.Param(self.model.i)
        self.model.r = pyo.Param(self.model.i)
        self.model.s = pyo.Param(self.model.k, self.model.t)
        self.model.a = pyo.Param(self.model.i)
        self.model.c = pyo.Param(self.model.i)
        self.model.tau = pyo.Param(self.model.j, self.model.k, self.model.t)
        self.model.specialty = pyo.Param(self.model.i)
        self.model.bigM = pyo.Param(self.model.bm)

        if(self.modelType == ModelType.START_TIME_ORDERING):
            self.model.A = pyo.Param(within=pyo.NonNegativeIntegers)
            self.model.alpha = pyo.RangeSet(1, self.model.A)
            self.model.beta = pyo.Var(self.model.alpha,
                                      self.model.i,
                                      self.model.k,
                                      self.model.t,
                                      domain=pyo.Binary)
            # anesthetists' available time
            self.model.An = pyo.Param(self.model.alpha, self.model.t)

    def define_variable_and_params_phase_two(self):
        self.model.Lambda = pyo.Var(self.model.i,
                                    self.model.i,
                                    self.model.t,
                                    domain=pyo.Binary)
        self.model.y = pyo.Var(self.model.i,
                               self.model.i,
                               self.model.k,
                               self.model.t,
                               domain=pyo.Binary)
        self.model.gamma = pyo.Var(self.model.i,
                                   domain=pyo.NonNegativeReals)

    def define_constraints_phase_two(self):
        self.model.anesthetist_no_overlap_constraint = pyo.Constraint(
            self.model.i,
            self.model.i,
            self.model.k,
            self.model.k,
            self.model.t,
            self.model.alpha,
            rule=self.anesthetist_no_overlap_rule)
        self.model.lambda_constraint = pyo.Constraint(
            self.model.i,
            self.model.i,
            self.model.t,
            rule=self.lambda_rule)
        self.model.end_of_day_constraint = pyo.Constraint(
            self.model.i,
            self.model.k,
            self.model.t,
            rule=self.end_of_day_rule)
        self.model.covid_precedence_constraint = pyo.Constraint(
            self.model.i,
            self.model.i,
            self.model.k,
            self.model.t,
            rule=self.start_time_ordering_covid_precedence_rule)
        self.model.precedence_constraint = pyo.Constraint(
            self.model.i,
            self.model.i,
            self.model.k,
            self.model.t,
            rule=self.time_ordering_precedence_rule)
        self.model.exclusive_precedence_constraint = pyo.Constraint(
            self.model.i,
            self.model.i,
            self.model.k,
            self.model.t,
            rule=self.exclusive_precedence_rule)

    def define_constraints_phase_one(self):
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

    def define_model(self):
        self.define_variables_and_params_phase_one()
        self.define_constraints_phase_one()
        self.model.objective = pyo.Objective(
            rule=self.objective_function,
            sense=pyo.maximize)

    def solve_model(self, data):
        self.create_model_instance(data)
        print("Solving phase one model instance...")
        self.model.results = self.solver.solve(self.modelInstance, tee=True)
        print("\nPhase one model instance solved.")
        self.extend_model()
        self.create_model_instance_phase_two(data)
        self.fix_variables_from_phase_one()
        self.drop_constraints()
        print("Solving phase two model instance...")
        self.model.results = self.solver.solve(
            self.modelInstancePhaseTwo, tee=True)
        print("Phase two model instance solved.")
        print(self.model.results)

    def extend_model(self):
        print("Extending model for phase two...")
        self.define_variable_and_params_phase_two()
        self.define_constraints_phase_two()
        print("Model extended for phase two.")

    def create_model_instance(self, data):
        print("Creating model instance...")
        self.modelInstance = self.model.create_instance(data)
        print("Model instance created.")

    def create_model_instance_phase_two(self, data):
        print("Creating model instance for phase two...")
        t = time.time()
        self.modelInstancePhaseTwo = self.model.create_instance(data)
        elapsed = (time.time() - t)
        print("Model instance for phase two created in " + str(round(elapsed, 2)) + "s")

    def fix_variables_from_phase_one(self):
        print("Fixing variables for phase two...")
        for k in self.modelInstance.k:
            for t in self.modelInstance.t:
                for i1 in self.modelInstance.i:
                    if(self.modelInstance.x[i1, k, t].value == 1):
                        self.modelInstancePhaseTwo.x[i1, k, t].fix(1)
                    else:
                        self.modelInstancePhaseTwo.x[i1, k, t].fix(0)
                        # self.modelInstancePhaseTwo.gamma[i1].fix(0)
                    for i2 in self.modelInstance.i:
                        if(i1 != i2 and (self.modelInstance.x[i1, k, t].value + self.modelInstance.x[i2, k, t].value < 2)):
                            self.modelInstancePhaseTwo.y[i1, i2, k, t].fix(0)
                        # can be dropped only if drop_constraints() is then called!!!
                        if(i1 != i2 and (self.modelInstance.x[i1, k, t].value + self.modelInstance.x[i2, k, t].value == 2)):
                            self.modelInstancePhaseTwo.Lambda[i1, i2, t].fix(0)
        print("Variables fixed.")

    def drop_constraints(self):
        print("Dropping constraints...")
        dropped = 0
        for k1 in self.modelInstancePhaseTwo.k:
            for t in self.modelInstancePhaseTwo.t:
                for i1 in self.modelInstancePhaseTwo.i:
                    if(self.modelInstancePhaseTwo.x[i1, k1, t].value < 1):
                        self.modelInstancePhaseTwo.end_of_day_constraint[i1, k1, t].deactivate(
                            )
                        dropped += 1
                    for i2 in self.modelInstancePhaseTwo.i:
                        if(i1 != i2 and self.modelInstancePhaseTwo.c[i1] == 0 and self.modelInstancePhaseTwo.c[i2] == 1
                                and self.modelInstancePhaseTwo.x[i1, k1, t].value + self.modelInstancePhaseTwo.x[i2, k1, t].value < 2):
                            self.modelInstancePhaseTwo.covid_precedence_constraint[i1, i2, k1, t].deactivate(
                            )
                            dropped += 1
                        if(i1 != i2 and self.modelInstancePhaseTwo.x[i1, k1, t].value + self.modelInstancePhaseTwo.x[i2, k1, t].value < 2):
                            self.modelInstancePhaseTwo.precedence_constraint[i1, i2, k1, t].deactivate(
                            )
                            dropped += 1
                        if(i1 < i2 and self.modelInstancePhaseTwo.x[i1, k1, t].value + self.modelInstancePhaseTwo.x[i2, k1, t].value < 2):
                            self.modelInstancePhaseTwo.exclusive_precedence_constraint[i1, i2, k1, t].deactivate(
                            )
                            dropped += 1
                        if(not(i1 >= i2) and self.modelInstancePhaseTwo.x[i1, k1, t].value + self.modelInstancePhaseTwo.x[i2, k1, t].value == 2):
                            self.modelInstancePhaseTwo.lambda_constraint[i1, i2, t].deactivate(
                            )
                            dropped += 1
                        for k2 in self.modelInstancePhaseTwo.k:
                            for alpha in self.modelInstancePhaseTwo.alpha:
                                if(not(i1 >= i2 or k1 == k2 or self.modelInstancePhaseTwo.a[i1] * self.modelInstancePhaseTwo.a[i2] == 0)
                                   and self.modelInstancePhaseTwo.x[i1, k1, t].value + self.modelInstancePhaseTwo.x[i2, k1, t].value == 2):
                                    self.modelInstancePhaseTwo.anesthetist_no_overlap_constraint[i1, i2, k1, k2, t, alpha].deactivate(
                                    )
                                    dropped += 1
                        if(dropped > 0 and dropped % 10000 == 0):
                            print("Dropped " + str(dropped) +
                                  " constraints so far")
        print("Dropped " + str(dropped) + " constraints in total")

    def extract_solution(self):
        dict = {}
        for k in self.modelInstancePhaseTwo.k:
            for t in self.modelInstancePhaseTwo.t:
                patients = []
                for i in self.modelInstancePhaseTwo.i:
                    if(self.modelInstancePhaseTwo.x[i, k, t].value == 1):
                        p = self.modelInstancePhaseTwo.p[i]
                        c = self.modelInstancePhaseTwo.c[i]
                        a = self.modelInstancePhaseTwo.a[i]
                        anesthetist = 0
                        if(self.modelType == ModelType.START_TIME_ORDERING and a == 1):
                            for alpha in self.modelInstancePhaseTwo.alpha:
                                if(self.modelInstancePhaseTwo.beta[alpha, i, k, t].value == 1):
                                    anesthetist = alpha
                        order = self.modelInstancePhaseTwo.gamma[i].value
                        specialty = self.modelInstancePhaseTwo.specialty[i]
                        priority = self.modelInstancePhaseTwo.r[i]
                        patients.append(
                            Patient(i, priority, k, specialty, t, p, c, a, anesthetist, order))
                patients.sort(key=lambda x: x.order)
                dict[(k, t)] = patients
        return dict

    def print_solution(self):
        solution = self.extract_solution()
        operatedPatients = 0
        for t in self.modelInstancePhaseTwo.t:
            for k in self.modelInstancePhaseTwo.k:
                print("Day: " + str(t) + "; Operating Room: S" + str(k) + "\n")
                for patient in solution[(k, t)]:
                    print(patient)
                    operatedPatients += 1
                print("\n")
        print("Total number of operated patients: " + str(operatedPatients))

# only for minute ordering, for now. To be extended
    def plot_graph(self):
        solution = self.extract_solution()
        dataFrames = []
        dff = pd.DataFrame([])
        for t in self.modelInstance.t:
            df = pd.DataFrame([])
            for k in self.modelInstance.k:
                for patient in solution[(k, t)]:
                    start = datetime.datetime(
                        1970, 1, t, 8, 0, 0) + datetime.timedelta(minutes=round(patient.order))
                    finish = start + \
                        datetime.timedelta(
                            minutes=round(patient.operatingTime))
                    room = "S" + str(k)
                    covid = "Y" if patient.covid == 1 else "N"
                    anesthesia = "Y" if patient.anesthesia == 1 else "N"
                    anesthetist = "A" + \
                        str(patient.anesthetist) if patient.anesthetist != 0 else ""
                    dfToAdd = pd.DataFrame(
                        [dict(Start=start, Finish=finish, Room=room, Covid=covid, Anesthesia=anesthesia, Anesthetist=anesthetist)])
                    df = pd.concat([df, dfToAdd])
            dataFrames.append(df)
            dff = pd.concat([df, dff])

        # import plotly.graph_objects as go
        # fig = go.Figure()
        fig = px.timeline(dff,
                          x_start="Start",
                          x_end="Finish",
                          y="Room",
                          color="Covid",
                          text="Anesthetist",
                          labels={
                              "Start": "Surgery start",
                              "Finish": "Surgery end",
                              "Room": "Operating room",
                              "Covid": "Covid patient",
                              "Anesthesia": "Need for anesthesia",
                              "Anesthetist": "Anesthetist"
                          },
                          hover_data=["Anesthesia", "Anesthetist"]
                          )

        fig.update_layout(xaxis=dict(
            title='Timetable', tickformat='%H:%M:%S',))
        fig.show()
