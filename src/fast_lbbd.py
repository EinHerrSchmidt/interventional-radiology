from __future__ import division
from itertools import tee
import logging
import time
import pyomo.environ as pyo
from pyomo.opt import TerminationCondition
import plotly.express as px
import pandas as pd
import datetime

from model import Patient

class Planner:

    def __init__(self, timeLimit, solver):
        self.MPModel = pyo.AbstractModel()
        self.MPInstance = None
        self.SPModel = pyo.AbstractModel()
        self.SPInstance = None
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

    def define_gamma_variables(self):
        self.SPModel.gamma = pyo.Var(self.SPModel.i, domain=pyo.NonNegativeReals)

    def define_objective(self, model):
        model.objective = pyo.Objective(
            rule=self.objective_function,
            sense=pyo.maximize)

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

    def plot_graph_(self, modelInstance):
        solutionPatients = self.common_extract_solution(modelInstance)
        dataFrames = []
        dff = pd.DataFrame([])
        for t in modelInstance.t:
            df = pd.DataFrame([])
            for k in modelInstance.k:
                patients = solutionPatients[(k, t)]
                for idx in range(0, len(patients)):
                    patient = patients[idx]
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
                          labels={"Start": "Surgery start", "Finish": "Surgery end", "Room": "Operating room",
                                  "Covid": "Covid patient", "Anesthesia": "Need for anesthesia", "Anesthetist": "Anesthetist"},
                          hover_data=["Anesthesia", "Anesthetist"]
                          )

        fig.update_layout(xaxis=dict(title='Timetable', tickformat='%H:%M:%S',))
        fig.show()


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
           or (model.xParam[i1, k1, t] + model.xParam[i2, k2, t] < 2)
           or (model.xParam[i1, k1, t] + model.xParam[i2, k1, t] == 2)
           or (model.xParam[i1, k2, t] + model.xParam[i2, k2, t] == 2)):
            return pyo.Constraint.Skip
        return model.gamma[i1] + model.p[i1] <= model.gamma[i2] + model.bigM[3] * (5 - model.beta[alpha, i1, t] - model.beta[alpha, i2, t] - model.x[i1, k1, t] - model.x[i2, k2, t] - model.Lambda[i1, i2, t])

    # precedence across rooms, same day
    @staticmethod
    def lambda_rule(model, i1, i2, t):
        if(i1 >= i2 or not (model.a[i1] == 1 and model.a[i2] == 1)):
            return pyo.Constraint.Skip
        for k in model.k:
            if(model.xParam[i1, k, t] + model.xParam[i2, k, t] == 2):
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
        if(i1 == i2 or not (model.u[i1, i2] == 1 and model.u[i2, i1] == 0) or (model.xParam[i1, k, t] + model.xParam[i2, k, t] < 2)):
            return pyo.Constraint.Skip
        return model.gamma[i1] * model.u[i1, i2] <= model.gamma[i2] * (1 - model.u[i2, i1]) + model.bigM[2] * (2 - model.x[i1, k, t] - model.x[i2, k, t])

    # either i1 comes before i2 in (k, t) or i2 comes before i1 in (k, t)
    @staticmethod
    def exclusive_precedence_rule(model, i1, i2, k, t):
        if(i1 >= i2 or (model.find_component('xParam') and model.xParam[i1, k, t] + model.xParam[i2, k, t] < 2)):
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

    @staticmethod
    def exclude_infeasible_patients_rule(model, modelInstance):
        return sum(1 - model.x[i, k, t] for i in model.i for k in model.k for t in model.t if modelInstance.x[i, k, t] == 1)


    def define_MP(self):
        self.define_sets(self.MPModel)
        self.define_x_variables(self.MPModel)
        self.define_parameters(self.MPModel)
        self.define_single_surgery_constraints(self.MPModel)
        self.define_surgery_time_constraints(self.MPModel)
        self.define_specialty_assignment_constraints(self.MPModel)
        self.define_anesthetists_number_param(self.MPModel)
        self.define_anesthetists_range_set(self.MPModel)
        self.define_beta_variables(self.MPModel)
        self.define_anesthetists_availability(self.MPModel)
        self.define_anesthetist_assignment_constraint(self.MPModel)
        self.define_anesthetist_time_constraint(self.MPModel)

        self.define_objective(self.MPModel)

    def define_SP(self):
        self.define_sets(self.SPModel)
        self.define_x_variables(self.SPModel)
        self.define_parameters(self.SPModel)
        self.define_single_surgery_constraints(self.SPModel)
        self.define_surgery_time_constraints(self.SPModel)
        self.define_specialty_assignment_constraints(self.SPModel)
        self.define_anesthetists_number_param(self.SPModel)
        self.define_anesthetists_range_set(self.SPModel)
        self.define_beta_variables(self.SPModel)
        self.define_anesthetists_availability(self.SPModel)
        self.define_anesthetist_assignment_constraint(self.SPModel)
        self.define_anesthetist_time_constraint(self.SPModel)


        self.define_x_parameters()
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
        self.create_master_problem_model_instance(data)
        self.MPInstance.cuts = pyo.ConstraintList()

        solverTime = 0
        while True:
            # Master problem
            print("Solving master problem model instance...")
            self.MPModel.results = self.solver.solve(self.MPInstance, tee=True)
            print("\nMaster problem model instance solved.")
            solverTime += self.solver._last_solve_time
            print(self.MPModel.results)

            # Sub Problem
            self.create_subproblem_model_instance(data)

            self.fix_SP_x_variables()
            self.fix_beta_variables()
            self.fix_y_variables()
            self.fix_lambda_variables()
            print("Solving subproblem model instance...")
            self.SPModel.results = self.solver.solve(self.SPModelInstance, tee=True)
            print("Subproblem model instance solved.")
            solverTime += self.solver._last_solve_time
            if(not self.SPModelInstance.solutions or self.SPModel.results.solver.termination_condition == TerminationCondition.infeasible):
                self.MPInstance.cuts.add(sum(1 - self.MPInstance.x[i, k, t] for i in self.MPInstance.i for k in self.MPInstance.k for t in self.MPInstance.t if round(self.MPInstance.x[i, k, t].value) == 1) >= 1)
                print("Generated cuts so far: \n")
                self.MPInstance.cuts.display()
                print("\n")
            else:
                break

        # TODO check solver status in order to determine how it ended
        
        print(self.SPModel.results)
        logging.basicConfig(filename='times.log', encoding='utf-8', level=logging.INFO)
        logging.info("Problem solved in " + str(round(solverTime, 2)) + "s")
        logging.info("Objective value: " + str(pyo.value(self.SPModelInstance.objective)))

    def extend_data(self, data):
        dict = {}
        for i in range(1, self.MPInstance.I + 1):
            for k in range(1, self.MPInstance.K + 1):
                for t in range(1, self.MPInstance.T + 1):
                    if(round(self.MPInstance.x[i, k, t].value) == 1):
                        dict[(i, k, t)] = 1
                    else:
                        dict[(i, k, t)] = 0
        data[None]['xParam'] = dict

    def create_master_problem_model_instance(self, data):
        print("Creating master problem model instance...")
        t = time.time()
        self.MPInstance = self.MPModel.create_instance(data)
        elapsed = (time.time() - t)
        print("Master problem model instance created in " + str(round(elapsed, 2)) + "s")
        logging.basicConfig(filename='times.log', encoding='utf-8', level=logging.INFO)
        logging.info("Master problem model instance created in " + str(round(elapsed, 2)) + "s")

    def create_subproblem_model_instance(self, data):
        self.extend_data(data)
        print("Creating subproblem model instance...")
        t = time.time()
        self.SPModelInstance = self.SPModel.create_instance(data)
        elapsed = (time.time() - t)
        print("Subproblem model instance created in " + str(round(elapsed, 2)) + "s")
        logging.basicConfig(filename='times.log', encoding='utf-8', level=logging.INFO)
        logging.info("Subproblem model instance created in " + str(round(elapsed, 2)) + "s")                       

    def fix_SP_x_variables(self):
        print("Fixing x variables for phase two...")
        fixed = 0
        for k in self.MPInstance.k:
            for t in self.MPInstance.t:
                for i1 in self.MPInstance.i:
                    if(round(self.MPInstance.x[i1, k, t].value) == 1):
                        self.SPModelInstance.x[i1, k, t].fix(1)
                    else:
                        self.SPModelInstance.x[i1, k, t].fix(0)
                    fixed += 1
        print(str(fixed) + " x variables fixed.")

    def fix_beta_variables(self):
        print("Fixing beta variables for phase two...")
        fixed = 0
        for i in self.MPInstance.i:
            for t in self.MPInstance.t:
                if(sum(round(self.MPInstance.x[i, k, t].value) for k in self.MPInstance.k) == 0):
                    for a in self.MPInstance.alpha:
                        self.SPModelInstance.beta[a, i, t].fix(0)
                        fixed += 1
        print(str(fixed) + " beta variables fixed.")

    def unfix_gamma_variables(self):
        print("Unfixing gamma variables...")
        fixed = 0
        for i1 in self.MPInstance.i:
                self.SPModelInstance.gamma[i1].unfix()
        print(str(fixed) + " gamma variables unfixed.")

    def fix_gamma_variables(self):
        print("Fixing gamma variables...")
        fixed = 0
        for i1 in self.MPInstance.i:
            if(sum(round(self.MPInstance.x[i1, k, t].value) for k in self.MPInstance.k for t in self.MPInstance.t) == 0):
                self.SPModelInstance.gamma[i1].fix(0)
                fixed += 1
        print(str(fixed) + " gamma variables fixed.")

    def fix_SP_y_variables(self):
        print("Fixing y variables...")
        fixed = 0
        for k in self.SPModelInstance.k:
            for t in self.SPModelInstance.t:
                for i1 in self.SPModelInstance.i:
                    for i2 in self.SPModelInstance.i:
                        if(i1 != i2 and self.MPInstance.u[i1, i2] == 1):
                            self.SPModelInstance.y[i1, i2, k, t].fix(1)
                            self.SPModelInstance.y[i2, i1, k, t].fix(0)
                            fixed += 2
        print(str(fixed) + " y variables fixed.")

    def fix_y_variables(self):
        print("Fixing y variables...")
        fixed = 0
        for k in self.SPModelInstance.k:
            for t in self.SPModelInstance.t:
                for i1 in self.SPModelInstance.i:
                    for i2 in self.SPModelInstance.i:
                        if(i1 != i2 and self.MPInstance.u[i1, i2] == 1):
                            self.SPModelInstance.y[i1, i2, k, t].fix(1)
                            self.SPModelInstance.y[i2, i1, k, t].fix(0)
                            fixed += 2
                        if(i1 != i2 and (round(self.MPInstance.x[i1, k, t].value) + round(self.MPInstance.x[i2, k, t].value) < 2)):
                            self.SPModelInstance.y[i1, i2, k, t].fix(0)
                            self.SPModelInstance.y[i2, i1, k, t].fix(1)
                            fixed += 2
        print(str(fixed) + " y variables fixed.")

    def fix_lambda_variables(self):
        print("Fixing lambda variables for phase two...")
        fixed = 0
        for k in self.MPInstance.k:
            for t in self.MPInstance.t:
                for i1 in self.MPInstance.i:
                    for i2 in self.MPInstance.i:
                        if(i1 != i2 and (round(self.MPInstance.x[i1, k, t].value) + round(self.MPInstance.x[i2, k, t].value) == 2)):
                            self.SPModelInstance.Lambda[i1, i2, t].fix(0)
                            self.SPModelInstance.Lambda[i2, i1, t].fix(1)
                            fixed += 2
        print(str(fixed) + " lambda variables fixed.")

    def drop_lambda_constraints(self):
        print("Dropping lambda constraints for phase two...")
        dropped = 0
        for k1 in self.SPModelInstance.k:
            for t in self.SPModelInstance.t:
                for i1 in self.SPModelInstance.i:
                    for i2 in self.SPModelInstance.i:
                        # remove constraint if both patients need anesthesia, but are assigned to the same room
                        if(self.SPModelInstance.a[i1] == 1 and self.SPModelInstance.a[i2] == 1 and not(i1 >= i2) and round(self.SPModelInstance.x[i1, k1, t].value) + round(self.SPModelInstance.x[i2, k1, t].value) == 2):
                            self.SPModelInstance.lambda_constraint[i1, i2, t].deactivate()
                            dropped += 1
                        if(dropped > 0 and dropped % 10000 == 0):
                            print("Dropped " + str(dropped) + " constraints so far")
        print("Dropped " + str(dropped) + " lambda constraints in total")

    def print_solution(self):
        self.common_print_solution(self.SPModelInstance)

    def plot_graph(self):
        self.plot_graph_(self.SPModelInstance)

    def extract_solution(self):
        return self.common_extract_solution(self.SPModelInstance)