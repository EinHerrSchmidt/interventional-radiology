from __future__ import division
from enum import Enum
import time
import pyomo.environ as pyo
import plotly.express as px
import pandas as pd
import datetime
from data_maker import DataContainer, DataDescriptor, DataMaker

from model import Patient

class ModelType(Enum):
    START_TIME_ORDERING = 1
    TWO_PHASE_START_TIME_ORDERING = 2
    SIMPLE_ORDERING = 3


class Planner:

    totalConstraints = 0
    skippedConstraints = 0

    def __init__(self, timeLimit, modelType, solver):
        self.dataContainer = None

        self.model = pyo.AbstractModel()
        self.previousModelInstance = None
        self.currentModelInstance = None
        self.solver = pyo.SolverFactory(solver)
        if(solver == "cplex"):
            self.solver.options['timelimit'] = timeLimit
        if(solver == "cbc"):
            self.solver.options['seconds'] = timeLimit
            # self.solver.options['threads'] = 6
            # self.solver.options['heuristics'] = "on"
            # self.solver.options['round'] = "on"
            # self.solver.options['feas'] = "both"
            # self.solver.options['passF'] = 180
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
        Planner.totalConstraints += 1
        return sum(model.x[i, k, t] for k in model.k for t in model.t) <= 1

    # estimated surgery times cannot exceed operating room/surgical team time availability
    @staticmethod
    def surgery_time_rule(model, k, t):
        Planner.totalConstraints += 1
        return sum(model.p[i] * model.x[i, k, t] for i in model.i) <= model.s[k, t]

    # each patient must be assigned to a room matching her specialty need
    @staticmethod
    def specialty_assignment_rule(model, j, k, t):
        Planner.totalConstraints += 1
        if(sum(model.specialty[i] for i in model.i if model.specialty[i] == j) == 0):
            return pyo.Constraint.Feasible
        return sum(model.x[i, k, t] for i in model.i if model.specialty[i] == j) <= model.bigM[1] * model.tau[j, k, t]

    # assign an anesthetist if and only if a patient needs her
    @staticmethod
    def anesthetist_assignment_rule(model, i, t):
        Planner.totalConstraints += 1
        return sum(model.beta[alpha, i, t]
                   for alpha in model.alpha) == model.a[i]* sum(model.x[i, k, t] for k in model.k)

    # do not exceed anesthetist time in each day
    @staticmethod
    def anesthetist_time_rule(model, alpha, t):
        Planner.totalConstraints += 1
        return sum(model.beta[alpha, i, t] * model.p[i]
                   for i in model.i) <= model.An[alpha, t]

    # patients with same anesthetist on same day but different room cannot overlap
    @staticmethod
    def anesthetist_no_overlap_rule(model, i1, i2, k1, k2, t, alpha):
        if(i1 == i2 or k1 == k2 or model.a[i1] * model.a[i2] == 0
        or (model.find_component('xParam') and model.xParam[i1, k1, t] + model.xParam[i2, k1, t] == 2)
        or (model.find_component('xParam') and model.xParam[i1, k2, t] + model.xParam[i2, k2, t] == 2)):
            Planner.skippedConstraints += 1
            return pyo.Constraint.Skip
        Planner.totalConstraints += 1
        return model.gamma[i1] + model.p[i1] <= model.gamma[i2] + model.bigM[3] * (5 - model.beta[alpha, i1, t] - model.beta[alpha, i2, t] - model.x[i1,k1,t] - model.x[i2,k2,t] - model.Lambda[i1, i2, t])

    # precedence across rooms, same day
    @staticmethod
    def lambda_rule(model, i1, i2, t):
        if(i1 >= i2 or not (model.a[i1] == 1 and model.a[i2] == 1)):
            Planner.skippedConstraints += 1
            return pyo.Constraint.Skip
        Planner.totalConstraints += 1
        return model.Lambda[i1, i2, t] + model.Lambda[i2, i1, t] == 1

    # ensure gamma plus operation time does not exceed end of day
    @staticmethod
    def end_of_day_rule(model, i, k, t):
        if(model.find_component('xParam') and model.xParam[i, k, t] == 0):
            Planner.skippedConstraints += 1
            return pyo.Constraint.Skip
        Planner.totalConstraints += 1
        return model.gamma[i] + model.p[i] <= model.s[k, t] + model.bigM[4] * (1 - model.x[i, k, t])

    # ensure that patient i1 terminates operation before i2, if y_12kt = 1
    @staticmethod
    def time_ordering_precedence_rule(model, i1, i2, k, t):
        if(i1 == i2 or (model.find_component('xParam') and model.xParam[i1, k, t] + model.xParam[i2, k, t] < 2)):
            Planner.skippedConstraints += 1
            return pyo.Constraint.Skip
        Planner.totalConstraints += 1
        return model.gamma[i1] + model.p[i1] <= model.gamma[i2] + model.bigM[5] * (3 - model.x[i1, k, t] - model.x[i2, k, t] - model.y[i1, i2, k, t])

    @staticmethod
    def start_time_ordering_priority_rule(model, i1, i2, k, t):
        if(i1 == i2 or not (model.u[i1, i2] == 1 and model.u[i2, i1] == 0) or (model.find_component('xParam') and model.xParam[i1, k, t] + model.xParam[i2, k, t] < 2)):
            Planner.skippedConstraints += 1
            return pyo.Constraint.Skip
        Planner.totalConstraints += 1
        return model.gamma[i1] * model.u[i1, i2] <= model.gamma[i2] * (1 - model.u[i2, i1]) + model.bigM[2] * (2 - model.x[i1, k, t] - model.x[i2, k, t])

    # either i1 comes before i2 in (k, t) or i2 comes before i1 in (k, t)
    @staticmethod
    def exclusive_precedence_rule(model, i1, i2, k, t):
        if(i1 >= i2 or (model.find_component('xParam') and model.xParam[i1, k, t] + model.xParam[i2, k, t] < 2)):
            Planner.skippedConstraints += 1
            return pyo.Constraint.Skip
        Planner.totalConstraints += 1
        return model.y[i1, i2, k, t] + model.y[i2, i1, k, t] == 1

    # patients needing anesthesia cannot exceed anesthesia total time in each room
    @staticmethod
    def anesthesia_total_time_rule(model, k, t):
        Planner.totalConstraints += 1
        return sum(model.x[i, k, t] * model.p[i] * model.a[i] for i in model.i) <= 480

    def define_variables_and_params(self):
        self.define_common_variables_and_params()
        self.define_STT_variables_and_params_phase_one()
        self.define_STT_variables_and_params_phase_two()

    def define_common_variables_and_params(self):
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
        self.model.u = pyo.Param(self.model.i, self.model.i)
        self.model.patientId = pyo.Param(self.model.i)
        self.model.tau = pyo.Param(self.model.j, self.model.k, self.model.t)
        self.model.specialty = pyo.Param(self.model.i)
        self.model.bigM = pyo.Param(self.model.bm)

    def define_STT_variables_and_params_phase_one(self):
        self.model.A = pyo.Param(within=pyo.NonNegativeIntegers)
        self.model.alpha = pyo.RangeSet(1, self.model.A)
        self.model.beta = pyo.Var(self.model.alpha,
                                  self.model.i,
                                  self.model.t,
                                  domain=pyo.Binary)
        # anesthetists' available time
        self.model.An = pyo.Param(self.model.alpha, self.model.t)

    def define_STT_variables_and_params_phase_two(self):
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
        self.model.xParam = pyo.Param(self.model.i,
                               self.model.k,
                               self.model.t)

    def define_constraints(self):
        self.define_common_constraints()
        self.define_STT_constraints_phase_one()
        self.define_STT_constraints_phase_two()

    def define_common_constraints(self):
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

    def define_STT_constraints_phase_one(self):
        self.model.anesthetist_assignment_constraint = pyo.Constraint(
            self.model.i,
            self.model.t,
            rule=self.anesthetist_assignment_rule)
        self.model.anesthetist_time_constraint = pyo.Constraint(
            self.model.alpha,
            self.model.t,
            rule=self.anesthetist_time_rule)

    def define_STT_constraints_phase_two(self):
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
        self.model.priority_constraint = pyo.Constraint(
            self.model.i,
            self.model.i,
            self.model.k,
            self.model.t,
            rule=self.start_time_ordering_priority_rule)
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

    def define_model(self):
        self.define_variables_and_params()
        self.define_constraints()
        self.define_objective()

    def define_objective(self):
        self.model.objective = pyo.Objective(
            rule=self.objective_function,
            sense=pyo.maximize)

    def solve_model(self, dataMaker:DataMaker, dataContainer: DataContainer, dataDescriptor: DataDescriptor):
        Planner.totalConstraints = 0
        Planner.skippedConstraints = 0
        totalOperated = 0

        dataDictionary = dataMaker.create_data_dictionary(dataContainer, dataDescriptor)
        dataMaker.print_data(dataDictionary)

        self.create_model_instance(dataDictionary)
        self.printConstraintsNumber()
        self.fix_variables_on_startup()
        print("Solving phase one model instance...")
        self.model.results = self.solver.solve(self.currentModelInstance, tee=True)
        self.print_solution()
        self.plot_graph()
        print("\nPhase one model instance solved.")
        for currentDay in range(2, 6):
            solution = self.extract_solution()
            yesterdayPatients = []
            for k in range(1, 5):
                yesterdayPatients.extend(solution[(k, 1)])
            for patient in yesterdayPatients:
                del dataContainer.operatingTimes[str(patient.id)]
                del dataContainer.priorities[str(patient.id)]
                del dataContainer.anesthesiaFlags[str(patient.id)]
                del dataContainer.covidFlags[str(patient.id)]
                del dataContainer.specialties[str(patient.id)]
                del dataContainer.ids[str(patient.id)]
            dataDescriptor.patients = dataDescriptor.patients - len(yesterdayPatients)
            dataDictionary = dataMaker.create_data_dictionary(dataContainer, dataDescriptor)
            self.create_model_instance(dataDictionary)
            self.printConstraintsNumber()
            self.fix_variables_on_startup()
            print("Solving phase one model instance...")
            self.model.results = self.solver.solve(self.currentModelInstance, tee=True)
            self.print_solution()
            self.plot_graph()
            totalOperated += len(yesterdayPatients)

        print(self.model.results)
        print("Total operated patients: " + str(totalOperated))


    def printConstraintsNumber(self):
        print("Total active constraints: " + str(Planner.totalConstraints))
        print("Skipped constraints: " + str(Planner.skippedConstraints))

    def create_model_instance(self, data):
        print("Creating model instance...")
        self.currentModelInstance = self.model.create_instance(data)
        print("Model instance created.")

    # only for start time ordering
    def fix_variables_on_startup(self):
        print("Fixing variables on startup...")
        fixed = 0
        for k in self.currentModelInstance.k:
            for t in self.currentModelInstance.t:
                for i1 in self.currentModelInstance.i:
                    for i2 in self.currentModelInstance.i:
                        if(i1 != i2 and self.currentModelInstance.u[i1, i2] == 1):
                            self.currentModelInstance.y[i1, i2, k, t].fix(1)
                            self.currentModelInstance.y[i2, i1, k, t].fix(0)
                            fixed += 2
        print(str(fixed) + " variables fixed.")

    def create_model_instance(self, data):
        self.currentModelInstance = self.model.create_instance(data)

    def extract_solution(self):
        dict = {}
        modelInstance = self.currentModelInstance
        for k in modelInstance.k:
            for t in modelInstance.t:
                patients = []
                for i in modelInstance.i:
                    if(self.currentModelInstance.x[i, k, t].value == 1):
                        p = modelInstance.p[i]
                        c = modelInstance.c[i]
                        a = modelInstance.a[i]
                        anesthetist = 0
                        for alpha in modelInstance.alpha:
                            if(modelInstance.beta[alpha, i, t].value == 1):
                                anesthetist = alpha
                        order = modelInstance.gamma[i].value
                        specialty = modelInstance.specialty[i]
                        priority = modelInstance.r[i]
                        patientId = modelInstance.patientId[i]
                        patients.append(
                            Patient(patientId, priority, k, specialty, t, p, c, a, anesthetist, round(order)))
                patients.sort(key=lambda x: x.order)
                dict[(k, t)] = patients
        return dict

    def print_solution(self):
        solution = self.extract_solution()
        modelInstance = self.currentModelInstance
        operatedPatients = 0
        for t in modelInstance.t:
            for k in modelInstance.k:
                print("Day: " + str(t) + "; Operating Room: S" + str(k) + "\n")
                for patient in solution[(k, t)]:
                    print(patient)
                    operatedPatients += 1
                print("\n")
        print("Total number of operated patients: " + str(operatedPatients))

    def plot_graph(self):
        solutionPatients = self.extract_solution()
        dataFrames = []
        dff = pd.DataFrame([])
        for t in self.currentModelInstance.t:
            df = pd.DataFrame([])
            for k in self.currentModelInstance.k:
                patients = solutionPatients[(k, t)]
                for idx in range(0, len(patients)):
                    patient = patients[idx]
                    start = datetime.datetime(1970, 1, t, 8, 0, 0) + datetime.timedelta(minutes=round(patient.order))
                    finish = start + datetime.timedelta(minutes=round(patient.operatingTime))
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
