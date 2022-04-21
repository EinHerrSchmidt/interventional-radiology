from __future__ import division
import time
import pyomo.environ as pyo
import plotly.express as px
import pandas as pd
import datetime

from model import Patient


class Planner:

    def __init__(self, timeLimit, solver):
        self.model = pyo.AbstractModel()
        self.modelInstance = None
        self.solver = pyo.SolverFactory(solver)
        if(solver == "cplex"):
            self.solver.options['timelimit'] = timeLimit
        if(solver == "cbc"):
            self.solver.options['seconds'] = timeLimit

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

    def build_common_model(self):
        self.define_common_variables_and_params()
        self.define_common_constraints()

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
        self.model.bigMRangeSet = pyo.RangeSet(1, self.model.M)

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
        self.model.tau = pyo.Param(self.model.j, self.model.k, self.model.t)
        self.model.specialty = pyo.Param(self.model.i)
        self.model.bigM = pyo.Param(self.model.bigMRangeSet)

    def define_gamma_variables(self):
        self.model.gamma = pyo.Var(self.model.i, domain=pyo.NonNegativeReals)

    def define_objective(self):
        self.model.objective = pyo.Objective(
            rule=self.objective_function,
            sense=pyo.maximize)

    def create_model_instance(self, data):
        print("Creating model instance...")
        self.modelInstance = self.model.create_instance(data)
        print("Model instance created.")

    def common_extract_solution(self, modelInstance):
        dict = {}
        for k in modelInstance.k:
            for t in modelInstance.t:
                patients = []
                for i in modelInstance.i:
                    if(round(modelInstance.x[i, k, t].value) == 1):
                        p = modelInstance.p[i]
                        c = modelInstance.c[i]
                        a = modelInstance.a[i]
                        anesthetist = 0
                        if(not isinstance(self, SimpleOrderingPlanner)):
                            for alpha in modelInstance.alpha:
                                if(round(modelInstance.beta[alpha, i, t].value) == 1):
                                    anesthetist = alpha
                        order = round(modelInstance.gamma[i].value)
                        specialty = modelInstance.specialty[i]
                        priority = modelInstance.r[i]
                        patients.append(
                            Patient(i, priority, k, specialty, t, p, c, a, anesthetist, order))
                patients.sort(key=lambda x: x.order)
                dict[(k, t)] = patients
        return dict

    def common_print_solution(self, modelInstance):
        solution = self.common_extract_solution(modelInstance)
        operatedPatients = 0
        for t in modelInstance.t:
            for k in modelInstance.k:
                print("Day: " + str(t) + "; Operating Room: S" + str(k) + "\n")
                for patient in solution[(k, t)]:
                    print(patient)
                    operatedPatients += 1
                print("\n")
        print("Total number of operated patients: " + str(operatedPatients))

    def plot_graph(self, modelInstance):
        solutionPatients = self.common_extract_solution(modelInstance)
        dataFrames = []
        dff = pd.DataFrame([])
        for t in modelInstance.t:
            df = pd.DataFrame([])
            for k in modelInstance.k:
                patients = solutionPatients[(k, t)]
                for idx in range(0, len(patients)):
                    patient = patients[idx]
                    if(isinstance(self, SimpleOrderingPlanner)):
                        if(idx == 0):
                            patient.order = 0
                        else:
                            patient.order = patients[idx - 1].order + patients[idx - 1].operatingTime
                    start = datetime.datetime(1970, 1, t, 8, 0, 0) + datetime.timedelta(minutes=round(patient.order))
                    finish = start + datetime.timedelta(minutes=round(patient.operatingTime))
                    room = "S" + str(k)
                    covid = "Y" if patient.covid == 1 else "N"
                    anesthesia = "Y" if patient.anesthesia == 1 else "N"
                    anesthetist = "A" + str(patient.anesthetist) if patient.anesthetist != 0 else ""
                    dataFrameToAdd = pd.DataFrame([dict(Start=start, Finish=finish, Room=room, Covid=covid, Anesthesia=anesthesia, Anesthetist=anesthetist)])
                    df = pd.concat([df, dataFrameToAdd])
            dataFrames.append(df)
            dff = pd.concat([df, dff])

        fig = px.timeline(dff,
                          x_start="Start",
                          x_end="Finish",
                          y="Room",
                          color="Covid",
                          text="Anesthetist",
                          labels={"Start": "Surgery start", "Finish": "Surgery end", "Room": "Operating room", "Covid": "Covid patient", "Anesthesia": "Need for anesthesia", "Anesthetist": "Anesthetist"},
                          hover_data=["Anesthesia", "Anesthetist"]
                          )

        fig.update_layout(xaxis=dict(title='Timetable', tickformat='%H:%M:%S',))
        fig.show()


class StartingMinutePlanner(Planner):

    # assign an anesthetist if and only if a patient needs her
    @staticmethod
    def anesthetist_assignment_rule(model, i, t):
        return sum(model.beta[alpha, i, t] for alpha in model.alpha) == model.a[i] * sum(model.x[i, k, t] for k in model.k)

    # do not exceed anesthetist time in each day
    @staticmethod
    def anesthetist_time_rule(model, alpha, t):
        return sum(model.beta[alpha, i, t] * model.p[i] for i in model.i) <= model.An[alpha, t]

    # patients with same anesthetist on same day but different room cannot overlap
    @staticmethod
    def anesthetist_no_overlap_rule(model, i1, i2, k1, k2, t, alpha):
        if(i1 == i2 or k1 == k2 or model.a[i1] * model.a[i2] == 0
           or (model.find_component('xParam') and model.xParam[i1, k1, t] + model.xParam[i2, k1, t] == 2)
           or (model.find_component('xParam') and model.xParam[i1, k2, t] + model.xParam[i2, k2, t] == 2)):
            return pyo.Constraint.Skip
        return model.gamma[i1] + model.p[i1] <= model.gamma[i2] + model.bigM[3] * (5 - model.beta[alpha, i1, t] - model.beta[alpha, i2, t] - model.x[i1, k1, t] - model.x[i2, k2, t] - model.Lambda[i1, i2, t])

    # precedence across rooms, same day
    @staticmethod
    def lambda_rule(model, i1, i2, t):
        if(i1 >= i2 or not (model.a[i1] == 1 and model.a[i2] == 1)):
            return pyo.Constraint.Skip
        return model.Lambda[i1, i2, t] + model.Lambda[i2, i1, t] == 1

    # ensure gamma plus operation time does not exceed end of day
    @staticmethod
    def end_of_day_rule(model, i, k, t):
        if(model.find_component('xParam') and model.xParam[i, k, t] == 0):
            return pyo.Constraint.Skip
        return model.gamma[i] + model.p[i] <= model.s[k, t] + model.bigM[4] * (1 - model.x[i, k, t])

    # ensure that patient i1 terminates operation before i2, if y_12kt = 1
    @staticmethod
    def time_ordering_precedence_rule(model, i1, i2, k, t):
        if(i1 == i2 or (model.find_component('xParam') and model.xParam[i1, k, t] + model.xParam[i2, k, t] < 2)):
            return pyo.Constraint.Skip
        return model.gamma[i1] + model.p[i1] <= model.gamma[i2] + model.bigM[5] * (3 - model.x[i1, k, t] - model.x[i2, k, t] - model.y[i1, i2, k, t])

    @staticmethod
    def start_time_ordering_priority_rule(model, i1, i2, k, t):
        if(i1 == i2 or not (model.u[i1, i2] == 1 and model.u[i2, i1] == 0) or (model.find_component('xParam') and model.xParam[i1, k, t] + model.xParam[i2, k, t] < 2)):
            return pyo.Constraint.Skip
        return model.gamma[i1] * model.u[i1, i2] <= model.gamma[i2] * (1 - model.u[i2, i1]) + model.bigM[2] * (2 - model.x[i1, k, t] - model.x[i2, k, t])

    # either i1 comes before i2 in (k, t) or i2 comes before i1 in (k, t)
    @staticmethod
    def exclusive_precedence_rule(model, i1, i2, k, t):
        if(i1 >= i2 or (model.find_component('xParam') and model.xParam[i1, k, t] + model.xParam[i2, k, t] < 2)):
            return pyo.Constraint.Skip
        return model.y[i1, i2, k, t] + model.y[i2, i1, k, t] == 1

    def define_anesthetists_number_param(self):
        self.model.A = pyo.Param(within=pyo.NonNegativeIntegers)

    def define_anesthetists_range_set(self):
        self.model.alpha = pyo.RangeSet(1, self.model.A)

    def define_beta_variables(self):
        self.model.beta = pyo.Var(self.model.alpha,
                                  self.model.i,
                                  self.model.t,
                                  domain=pyo.Binary)

    def define_anesthetists_availability(self):
        self.model.An = pyo.Param(self.model.alpha, self.model.t)

    def define_lambda_variables(self):
        self.model.Lambda = pyo.Var(self.model.i,
                                    self.model.i,
                                    self.model.t,
                                    domain=pyo.Binary)

    def define_y_variables(self):
        self.model.y = pyo.Var(self.model.i,
                               self.model.i,
                               self.model.k,
                               self.model.t,
                               domain=pyo.Binary)

    def define_anesthetist_assignment_constraint(self):
        self.model.anesthetist_assignment_constraint = pyo.Constraint(
            self.model.i,
            self.model.t,
            rule=self.anesthetist_assignment_rule)

    def define_anesthetist_time_constraint(self):
        self.model.anesthetist_time_constraint = pyo.Constraint(
            self.model.alpha,
            self.model.t,
            rule=self.anesthetist_time_rule)
    
    def define_anesthetist_no_overlap_constraint(self):
        self.model.anesthetist_no_overlap_constraint = pyo.Constraint(
            self.model.i,
            self.model.i,
            self.model.k,
            self.model.k,
            self.model.t,
            self.model.alpha,
            rule=self.anesthetist_no_overlap_rule)

    def define_lambda_constraint(self):
        self.model.lambda_constraint = pyo.Constraint(
            self.model.i,
            self.model.i,
            self.model.t,
            rule=self.lambda_rule)
    
    def define_end_of_day_constraint(self):
        self.model.end_of_day_constraint = pyo.Constraint(
            self.model.i,
            self.model.k,
            self.model.t,
            rule=self.end_of_day_rule)

    def define_priority_constraint(self):
        self.model.priority_constraint = pyo.Constraint(
            self.model.i,
            self.model.i,
            self.model.k,
            self.model.t,
            rule=self.start_time_ordering_priority_rule)

    def define_precedence_constraint(self):
        self.model.precedence_constraint = pyo.Constraint(
            self.model.i,
            self.model.i,
            self.model.k,
            self.model.t,
            rule=self.time_ordering_precedence_rule)

    def define_exclusive_precedence_constraint(self):
        self.model.exclusive_precedence_constraint = pyo.Constraint(
            self.model.i,
            self.model.i,
            self.model.k,
            self.model.t,
            rule=self.exclusive_precedence_rule)

    def fix_y_variables(self, modelInstance):
        print("Fixing y variables...")
        fixed = 0
        for k in modelInstance.k:
            for t in modelInstance.t:
                for i1 in modelInstance.i:
                    for i2 in modelInstance.i:
                        if(i1 != i2 and modelInstance.u[i1, i2] == 1):
                            modelInstance.y[i1, i2, k, t].fix(1)
                            modelInstance.y[i2, i1, k, t].fix(0)
                            fixed += 2
        print(str(fixed) + " y variables fixed.")


class SinglePhaseStartingMinutePlanner(StartingMinutePlanner):

    def __init__(self, timeLimit, solver):
        super().__init__(timeLimit, solver)
        self.define_model()

    def define_model(self):
        self.build_common_model()
        self.define_variables_and_params()
        self.define_constraints()
        self.define_objective()

    def define_variables_and_params(self):
        self.define_anesthetists_number_param()
        self.define_anesthetists_range_set()
        self.define_beta_variables()
        self.define_anesthetists_availability()
        self.define_lambda_variables()
        self.define_y_variables()
        self.define_gamma_variables()

    def define_constraints(self):
        self.define_anesthetist_assignment_constraint()
        self.define_anesthetist_time_constraint()
        self.define_anesthetist_no_overlap_constraint()
        self.define_lambda_constraint()
        self.define_end_of_day_constraint()
        self.define_priority_constraint()
        self.define_precedence_constraint()
        self.define_exclusive_precedence_constraint()

    def solve_model(self, data):
        self.create_model_instance(data)
        self.fix_y_variables(self.modelInstance)
        print("Solving model instance...")
        self.model.results = self.solver.solve(self.modelInstance, tee=True)
        print("\nModel instance solved.")
        print(self.model.results)

    def print_solution(self):
        super().common_print_solution(self.modelInstance)

    def plot_graph(self):
        super().plot_graph(self.modelInstance)

    def extract_solution(self):
        return super().common_extract_solution(self.modelInstance)


class TwoPhaseStartingMinutePlanner(StartingMinutePlanner):

    def __init__(self, timeLimit, solver):
        super().__init__(timeLimit, solver)
        self.modelInstancePhaseTwo = None
        self.define_model()

    def define_model(self):
        self.build_common_model()
        self.define_variables_and_params_phase_one()
        self.define_constraints_phase_one()
        self.define_objective()

    def define_variables_and_params_phase_one(self):
        self.define_anesthetists_number_param()
        self.define_anesthetists_range_set()
        self.define_beta_variables()
        self.define_anesthetists_availability()

    def define_variables_and_params_phase_two(self):
        self.define_lambda_variables()
        self.define_y_variables()
        self.define_gamma_variables()
        self.model.xParam = pyo.Param(self.model.i,
                                      self.model.k,
                                      self.model.t)

    def define_constraints_phase_one(self):
        self.define_anesthetist_assignment_constraint()
        self.define_anesthetist_time_constraint()

    def define_constraints_phase_two(self):
        self.define_anesthetist_no_overlap_constraint()
        self.define_lambda_constraint()
        self.define_end_of_day_constraint()
        self.define_priority_constraint()
        self.define_precedence_constraint()
        self.define_exclusive_precedence_constraint()

    def solve_model(self, data):
        # phase one
        self.create_model_instance(data)
        print("Solving phase one model instance...")
        self.model.results = self.solver.solve(self.modelInstance, tee=True)
        print("\nPhase one model instance solved.")

        # phase two
        self.extend_model()
        self.extend_data(data)
        self.create_model_instance_phase_two(data)
        self.fix_x_variables()
        self.fix_gamma_variables()
        self.fix_y_variables(self.modelInstancePhaseTwo)
        self.handle_lambda_variables_and_constraints()
        print("Solving phase two model instance...")
        self.model.results = self.solver.solve(self.modelInstancePhaseTwo, tee=True)
        print("Phase two model instance solved.")
        print(self.model.results)

    def extend_model(self):
        print("Extending model for phase two...")
        self.define_variables_and_params_phase_two()
        self.define_constraints_phase_two()
        print("Model extended for phase two.")

    def extend_data(self, data):
        dict = {}
        for i in range(1, self.modelInstance.I + 1):
            for k in range(1, self.modelInstance.K + 1):
                for t in range(1, self.modelInstance.T + 1):
                    if(round(self.modelInstance.x[i, k, t].value) == 1):
                        dict[(i, k, t)] = 1
                    else:
                        dict[(i, k, t)] = 0
        data[None]['xParam'] = dict

    def create_model_instance_phase_two(self, data):
        print("Creating model instance for phase two...")
        t = time.time()
        self.modelInstancePhaseTwo = self.model.create_instance(data)
        elapsed = (time.time() - t)
        print("Model instance for phase two created in " + str(round(elapsed, 2)) + "s")

    def fix_x_variables(self):
        print("Fixing x variables for phase two...")
        fixed = 0
        for k in self.modelInstance.k:
            for t in self.modelInstance.t:
                for i1 in self.modelInstance.i:
                    if(round(self.modelInstance.x[i1, k, t].value) == 1):
                        self.modelInstancePhaseTwo.x[i1, k, t].fix(1)
                    else:
                        self.modelInstancePhaseTwo.x[i1, k, t].fix(0)
                    fixed += 1
        print(str(fixed) + " x variables fixed.")

    def fix_gamma_variables(self):
        print("Fixing gamma variables for phase two...")
        fixed = 0
        for i1 in self.modelInstance.i:
            if(sum(round(self.modelInstance.x[i1, k, t].value) for k in self.modelInstance.k for t in self.modelInstance.t) == 0):
                self.modelInstancePhaseTwo.gamma[i1].fix(0)
                fixed += 1
        print(str(fixed) + " gamma variables fixed.")

    def handle_lambda_variables_and_constraints(self):
        self.fix_lambda_variables()
        self.drop_lambda_constraints()

    def fix_lambda_variables(self):
        print("Fixing lambda variables for phase two...")
        fixed = 0
        for k in self.modelInstance.k:
            for t in self.modelInstance.t:
                for i1 in self.modelInstance.i:
                    for i2 in self.modelInstance.i:
                        if(i1 != i2 and (round(self.modelInstance.x[i1, k, t].value) + round(self.modelInstance.x[i2, k, t].value) < 2)):
                            self.modelInstancePhaseTwo.y[i1, i2, k, t].fix(0)
                            fixed += 1
                        if(i1 != i2 and (round(self.modelInstance.x[i1, k, t].value) + round(self.modelInstance.x[i2, k, t].value) == 2)):
                            self.modelInstancePhaseTwo.Lambda[i1, i2, t].fix(0)
                            fixed += 1
        print(str(fixed) + " lambda variables fixed.")

    def drop_lambda_constraints(self):
        print("Dropping lambda constraints for phase two...")
        dropped = 0
        for k1 in self.modelInstancePhaseTwo.k:
            for t in self.modelInstancePhaseTwo.t:
                for i1 in self.modelInstancePhaseTwo.i:
                    for i2 in self.modelInstancePhaseTwo.i:
                        # remove constraint if both patients need anesthesia, but are assigned to the same room
                        if(self.modelInstancePhaseTwo.a[i1] == 1 and self.modelInstancePhaseTwo.a[i2] == 1 and not(i1 >= i2) and round(self.modelInstancePhaseTwo.x[i1, k1, t].value) + round(self.modelInstancePhaseTwo.x[i2, k1, t].value) == 2):
                            self.modelInstancePhaseTwo.lambda_constraint[i1, i2, t].deactivate()
                            dropped += 1
                        if(dropped > 0 and dropped % 10000 == 0):
                            print("Dropped " + str(dropped) + " constraints so far")
        print("Dropped " + str(dropped) + " lambda constraints in total")

    def print_solution(self):
        super().common_print_solution(self.modelInstancePhaseTwo)

    def plot_graph(self):
        super().plot_graph(self.modelInstancePhaseTwo)

    def extract_solution(self):
        return super().common_extract_solution(self.modelInstancePhaseTwo)


class SimpleOrderingPlanner(Planner):

    def __init__(self, timeLimit, solver):
        super().__init__(timeLimit, solver)
        self.define_model()

    @staticmethod
    def simple_ordering_priority_rule(model, i1, i2, k, t):
        if(i1 == i2 or not (model.u[i1, i2] == 1 and model.u[i2, i1] == 0)):
            return pyo.Constraint.Skip
        return model.gamma[i1] * model.u[i1, i2] <= model.gamma[i2] * (1 - model.u[i2, i1]) - 1 + model.bigM[6] * (2 - model.x[i1, k, t] - model.x[i2, k, t])

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
        return sum(model.x[i, k, t] * model.p[i] * model.a[i] for i in model.i) <= 480

    def define_model(self):
        self.build_common_model()
        self.define_variables_and_params()
        self.define_constraints()
        self.define_objective()

    def define_variables_and_params(self):
        self.model.rho = pyo.Param(self.model.i, self.model.j)
        self.define_gamma_variables()

    def define_constraints(self):
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
        self.model.priority_constraint = pyo.Constraint(
            self.model.i,
            self.model.i,
            self.model.k,
            self.model.t,
            rule=self.simple_ordering_priority_rule)

    def solve_model(self, data):
        self.create_model_instance(data)
        print("Solving model instance...")
        self.model.results = self.solver.solve(self.modelInstance, tee=True)
        print("\nModel instance solved.")

    def print_solution(self):
        super().common_print_solution(self.modelInstance)

    def plot_graph(self):
        super().plot_graph(self.modelInstance)

    def extract_solution(self):
        return super().common_extract_solution(self.modelInstance)