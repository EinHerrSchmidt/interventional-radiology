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
        self.SPModel = pyo.AbstractModel()
        self.SPModelInstance = None
        self.define_models()
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

        self.SPModel.single_surgery_constraint = pyo.Constraint(
            self.SPModel.i,
            rule=self.single_surgery_rule)
        self.SPModel.surgery_time_constraint = pyo.Constraint(
            self.SPModel.k,
            self.SPModel.t,
            rule=self.surgery_time_rule)
        self.SPModel.specialty_assignment_constraint = pyo.Constraint(
            self.SPModel.j,
            self.SPModel.k,
            self.SPModel.t,
            rule=self.specialty_assignment_rule)

    def define_common_variables_and_params(self,):
        self.model.I = pyo.Param(within=pyo.NonNegativeIntegers)
        self.model.J = pyo.Param(within=pyo.NonNegativeIntegers)
        self.model.K = pyo.Param(within=pyo.NonNegativeIntegers)
        self.model.T = pyo.Param(within=pyo.NonNegativeIntegers)
        self.model.M = pyo.Param(within=pyo.NonNegativeIntegers)
        self.SPModel.I = pyo.Param(within=pyo.NonNegativeIntegers)
        self.SPModel.J = pyo.Param(within=pyo.NonNegativeIntegers)
        self.SPModel.K = pyo.Param(within=pyo.NonNegativeIntegers)
        self.SPModel.T = pyo.Param(within=pyo.NonNegativeIntegers)
        self.SPModel.M = pyo.Param(within=pyo.NonNegativeIntegers)

        self.model.i = pyo.RangeSet(1, self.model.I)
        self.model.j = pyo.RangeSet(1, self.model.J)
        self.model.k = pyo.RangeSet(1, self.model.K)
        self.model.t = pyo.RangeSet(1, self.model.T)
        self.model.bigMRangeSet = pyo.RangeSet(1, self.model.M)
        self.SPModel.i = pyo.RangeSet(1, self.SPModel.I)
        self.SPModel.j = pyo.RangeSet(1, self.SPModel.J)
        self.SPModel.k = pyo.RangeSet(1, self.SPModel.K)
        self.SPModel.t = pyo.RangeSet(1, self.SPModel.T)
        self.SPModel.bigMRangeSet = pyo.RangeSet(1, self.SPModel.M)

        self.model.x = pyo.Var(self.model.i,
                               self.model.k,
                               self.model.t,
                               domain=pyo.Binary)
        self.SPModel.x = pyo.Var(self.SPModel.i,
                               self.SPModel.k,
                               self.SPModel.t,
                               domain=pyo.Binary)

        self.model.p = pyo.Param(self.model.i)
        self.model.r = pyo.Param(self.model.i)
        self.model.s = pyo.Param(self.model.k, self.model.t)
        self.model.a = pyo.Param(self.model.i)
        self.model.c = pyo.Param(self.model.i)
        self.model.u = pyo.Param(self.model.i, self.model.i)
        self.model.tau = pyo.Param(self.model.j, self.model.k, self.model.t)
        self.model.specialty = pyo.Param(self.model.i)
        self.model.bigM = pyo.Param(self.model.bigMRangeSet)
        self.SPModel.p = pyo.Param(self.SPModel.i)
        self.SPModel.r = pyo.Param(self.SPModel.i)
        self.SPModel.s = pyo.Param(self.SPModel.k, self.SPModel.t)
        self.SPModel.a = pyo.Param(self.SPModel.i)
        self.SPModel.c = pyo.Param(self.SPModel.i)
        self.SPModel.u = pyo.Param(self.SPModel.i, self.SPModel.i)
        self.SPModel.tau = pyo.Param(self.SPModel.j, self.SPModel.k, self.SPModel.t)
        self.SPModel.specialty = pyo.Param(self.SPModel.i)
        self.SPModel.bigM = pyo.Param(self.SPModel.bigMRangeSet)

    def define_gamma_variables(self):
        self.SPModel.gamma = pyo.Var(self.SPModel.i, domain=pyo.NonNegativeReals)

    def define_objective(self):
        self.model.objective = pyo.Objective(
            rule=self.objective_function,
            sense=pyo.maximize)
        self.SPModel.objective = pyo.Objective(
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
        if(i1 == i2 or k1 == k2 or model.a[i1] * model.a[i2] == 0):
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
        return model.gamma[i] + model.p[i] <= model.s[k, t] + model.bigM[4] * (1 - model.x[i, k, t])

    # ensure that patient i1 terminates operation before i2, if y_12kt = 1
    @staticmethod
    def time_ordering_precedence_rule(model, i1, i2, k, t):
        if(i1 == i2):
            return pyo.Constraint.Skip
        return model.gamma[i1] + model.p[i1] <= model.gamma[i2] + model.bigM[5] * (3 - model.x[i1, k, t] - model.x[i2, k, t] - model.y[i1, i2, k, t])

    @staticmethod
    def start_time_ordering_priority_rule(model, i1, i2, k, t):
        if(i1 == i2 or not (model.u[i1, i2] == 1 and model.u[i2, i1] == 0)):
            return pyo.Constraint.Skip
        return model.gamma[i1] * model.u[i1, i2] <= model.gamma[i2] * (1 - model.u[i2, i1]) + model.bigM[2] * (2 - model.x[i1, k, t] - model.x[i2, k, t])

    # either i1 comes before i2 in (k, t) or i2 comes before i1 in (k, t)
    @staticmethod
    def exclusive_precedence_rule(model, i1, i2, k, t):
        if(i1 >= i2):
            return pyo.Constraint.Skip
        return model.y[i1, i2, k, t] + model.y[i2, i1, k, t] == 1

    def reactivate_constraints(self):
        for i1 in self.SPModelInstance.i:
                for k1 in self.SPModelInstance.k:
                    for t in self.SPModelInstance.t:
                        if(self.SPModelInstance.end_of_day_constraint[i1, k1, t]):
                            self.SPModelInstance.end_of_day_constraint[i1, k1, t].activate()
                        for i2 in self.SPModelInstance.i:    
                            if(i1 != i2):
                                self.SPModelInstance.precedence_constraint[i1, i2, k1, t].activate()
                            if(not(i1 == i2 or not (self.SPModelInstance.u[i1, i2] == 1 and self.SPModelInstance.u[i2, i1] == 0))):
                                self.SPModelInstance.priority_constraint[i1, i2, k1, t].activate()
                            if(i1 < i2):
                                self.SPModelInstance.exclusive_precedence_constraint[i1, i2, k1, t].activate()
                            if(not(i1 >= i2 or not (self.SPModelInstance.a[i1] == 1 and self.SPModelInstance.a[i2] == 1))):
                                self.SPModelInstance.lambda_constraint[i1, i2, t].activate()
                            for k2 in self.SPModelInstance.k:
                                for a in self.SPModelInstance.alpha:
                                    if(not(i1 == i2 or k1 == k2 or self.SPModelInstance.a[i1] * self.SPModelInstance.a[i2] == 0)):
                                        self.SPModelInstance.anesthetist_no_overlap_constraint[i1, i2, k1, k2, t, a].activate()
                            
    def deactivate_constraints(self):
        for i1 in self.SPModelInstance.i:
            for k1 in self.SPModelInstance.k:
                for t in self.SPModelInstance.t:
                    if(round(self.modelInstance.x[i1, k1, t].value) == 0):
                        self.SPModelInstance.end_of_day_constraint[i1, k1, t].deactivate()
                    for i2 in self.SPModelInstance.i:
                        if(i1 != i2 and round(self.modelInstance.x[i1, k1, t].value) + round(self.modelInstance.x[i2, k1, t].value) < 2):
                            self.SPModelInstance.precedence_constraint[i1, i2, k1, t].deactivate()
                        if(not(i1 == i2 or not (self.modelInstance.u[i1, i2] == 1 and self.modelInstance.u[i2, i1] == 0)) and round(self.modelInstance.x[i1, k1, t].value) + round(self.modelInstance.x[i2, k1, t].value) < 2):
                            self.SPModelInstance.priority_constraint[i1, i2, k1, t].deactivate()
                        if(i1 < i2 and round(self.modelInstance.x[i1, k1, t].value) + round(self.modelInstance.x[i2, k1, t].value) < 2):
                            self.SPModelInstance.exclusive_precedence_constraint[i1, i2, k1, t].deactivate()
                        if(self.modelInstance.a[i1] == 1 and self.modelInstance.a[i2] == 1 and not(i1 >= i2) and round(self.modelInstance.x[i1, k1, t].value) + round(self.modelInstance.x[i2, k1, t].value) == 2):
                            self.SPModelInstance.lambda_constraint[i1, i2, t].deactivate()
                        for k2 in self.SPModelInstance.k:
                            if(not(i1 == i2 or k1 == k2 or self.modelInstance.a[i1] * self.modelInstance.a[i2] == 0) and (round(self.modelInstance.x[i1, k1, t].value) + round(self.modelInstance.x[i2, k1, t].value) == 2 or 
                                round(self.modelInstance.x[i1, k2, t].value) + round(self.modelInstance.x[i2, k2, t].value) == 2)):
                                for a in self.SPModelInstance.alpha:
                                    self.SPModelInstance.anesthetist_no_overlap_constraint[i1, i2, k1, k2, t, a].deactivate()

    def define_anesthetists_number_param(self):
        self.model.A = pyo.Param(within=pyo.NonNegativeIntegers)
        self.SPModel.A = pyo.Param(within=pyo.NonNegativeIntegers)

    def define_anesthetists_range_set(self):
        self.model.alpha = pyo.RangeSet(1, self.model.A)
        self.SPModel.alpha = pyo.RangeSet(1, self.SPModel.A)

    def define_beta_variables(self):
        self.model.beta = pyo.Var(self.model.alpha,
                                  self.model.i,
                                  self.model.t,
                                  domain=pyo.Binary)

        self.SPModel.beta = pyo.Var(self.SPModel.alpha,
                                  self.SPModel.i,
                                  self.SPModel.t,
                                  domain=pyo.Binary)

    def define_anesthetists_availability(self):
        self.model.An = pyo.Param(self.model.alpha, self.model.t)
        self.SPModel.An = pyo.Param(self.SPModel.alpha, self.SPModel.t)

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

    def define_anesthetist_assignment_constraint(self):
        self.model.anesthetist_assignment_constraint = pyo.Constraint(
            self.model.i,
            self.model.t,
            rule=self.anesthetist_assignment_rule)

        self.SPModel.anesthetist_assignment_constraint = pyo.Constraint(
            self.SPModel.i,
            self.SPModel.t,
            rule=self.anesthetist_assignment_rule)

    def define_anesthetist_time_constraint(self):
        self.model.anesthetist_time_constraint = pyo.Constraint(
            self.model.alpha,
            self.model.t,
            rule=self.anesthetist_time_rule)

        self.SPModel.anesthetist_time_constraint = pyo.Constraint(
            self.SPModel.alpha,
            self.SPModel.t,
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


    def define_models(self):
        self.define_common_variables_and_params()
        self.define_common_constraints()

        self.define_anesthetists_number_param()
        self.define_anesthetists_range_set()
        self.define_beta_variables()
        self.define_anesthetists_availability()

        self.define_anesthetist_assignment_constraint()
        self.define_anesthetist_time_constraint()

        self.extend_sub_problem_model()
        self.define_objective()

    def extend_sub_problem_model(self):
        self.define_variables_and_params_sub_problem()
        self.define_constraints_sub_problem()

    def define_variables_and_params_sub_problem(self):
        self.define_lambda_variables()
        self.define_y_variables()
        self.define_gamma_variables()

    def define_constraints_sub_problem(self):
        self.define_anesthetist_no_overlap_constraint()

        self.define_lambda_constraint()
        self.define_end_of_day_constraint()
        self.define_priority_constraint()
        self.define_precedence_constraint()
        self.define_exclusive_precedence_constraint()

    def solve_model(self, data):
        self.create_master_problem_model_instance(data)
        self.create_subproblem_model_instance(data)
        self.modelInstance.cuts = pyo.ConstraintList()
        while True:
            # Master problem
            print("Solving master problem model instance...")
            self.model.results = self.solver.solve(self.modelInstance, tee=True)
            print("\nMaster problem model instance solved.")
            print(self.model.results)

            # Sub Problem
            self.unfix_SP_x_variables()
            self.fix_x_variables()
            self.unfix_beta_variables()
            self.fix_beta_variables()
            self.unfix_y_variables()
            self.fix_y_variables()
            self.unfix_lambda_variables()
            self.fix_lambda_variables()
            self.reactivate_constraints()
            self.deactivate_constraints()
            print("Solving subproblem model instance...")
            self.SPModel.results = self.solver.solve(self.SPModelInstance, tee=True)
            print("Subproblem model instance solved.")
            print(self.SPModel.results)
            if(not self.SPModelInstance.solutions or pyo.value(self.SPModelInstance.objective) < pyo.value(self.modelInstance.objective)):
                for i in self.SPModelInstance.i:
                    for k in self.SPModelInstance.k:
                        for t in self.SPModelInstance.t:
                            if(self.SPModelInstance.x[i, k, t].fixed == False and round(self.SPModelInstance.x[i, k, t].value) == 0):
                                self.modelInstance.x[i, k, t].fix(0)
            else:
                break

    def create_master_problem_model_instance(self, data):
        print("Creating master problem model instance...")
        t = time.time()
        self.modelInstance = self.model.create_instance(data)
        elapsed = (time.time() - t)
        print("Master problem model instance created in " + str(round(elapsed, 2)) + "s")

    def create_subproblem_model_instance(self, data):
        print("Creating subproblem model instance...")
        t = time.time()
        self.SPModelInstance = self.SPModel.create_instance(data)
        elapsed = (time.time() - t)
        print("Subproblem model instance created in " + str(round(elapsed, 2)) + "s")

    def unfix_SP_x_variables(self):
        for k in self.modelInstance.k:
            for t in self.modelInstance.t:
                for i in self.modelInstance.i:
                    self.SPModelInstance.x[i, k, t].unfix()

    def fix_x_variables(self):
        print("Fixing x variables for phase two...")
        fixed = 0
        for k in self.modelInstance.k:
            for t in self.modelInstance.t:
                for i1 in self.modelInstance.i:
                    if(round(self.modelInstance.x[i1, k, t].value) == 0):
                        self.SPModelInstance.x[i1, k, t].fix(0)
                        fixed += 1
                    # else:
                    #     self.SPModelInstance.x[i1, k, t].fix(0)
        print(str(fixed) + " x variables fixed.")

    def unfix_beta_variables(self):
        for alpha in self.modelInstance.alpha:
            for i in self.modelInstance.i:
                for t in self.modelInstance.t:
                    self.SPModelInstance.beta[alpha, i, t].unfix()

    def fix_beta_variables(self):
        print("Fixing beta variables for phase two...")
        fixed = 0
        for alpha in self.modelInstance.alpha:
            for i in self.modelInstance.i:
                for t in self.modelInstance.t:
                    if(round(self.modelInstance.beta[alpha, i, t].value) == 1):
                        self.SPModelInstance.beta[alpha, i, t].fix(1)
                    else:
                        self.SPModelInstance.beta[alpha, i, t].fix(0)
                    fixed += 1
        print(str(fixed) + " beta variables fixed.")

    def unfix_gamma_variables(self):
        print("Unfixing gamma variables...")
        fixed = 0
        for i1 in self.modelInstance.i:
                self.SPModelInstance.gamma[i1].unfix()
        print(str(fixed) + " gamma variables unfixed.")

    def fix_gamma_variables(self):
        print("Fixing gamma variables...")
        fixed = 0
        for i1 in self.modelInstance.i:
            if(sum(round(self.modelInstance.x[i1, k, t].value) for k in self.modelInstance.k for t in self.modelInstance.t) == 0):
                self.SPModelInstance.gamma[i1].fix(0)
                fixed += 1
        print(str(fixed) + " gamma variables fixed.")

    def unfix_y_variables(self):
        for k in self.SPModelInstance.k:
            for t in self.SPModelInstance.t:
                for i1 in self.SPModelInstance.i:
                    for i2 in self.SPModelInstance.i:
                        self.SPModelInstance.y[i1, i2, k, t].unfix()

    def fix_y_variables(self):
        print("Fixing y variables...")
        fixed = 0
        for k in self.SPModelInstance.k:
            for t in self.SPModelInstance.t:
                for i1 in self.SPModelInstance.i:
                    for i2 in self.SPModelInstance.i:
                        if(i1 != i2 and self.modelInstance.u[i1, i2] == 1):
                            self.SPModelInstance.y[i1, i2, k, t].fix(1)
                            self.SPModelInstance.y[i2, i1, k, t].fix(0)
                            fixed += 2
                        if(i1 != i2 and (round(self.modelInstance.x[i1, k, t].value) + round(self.modelInstance.x[i2, k, t].value) < 2)):
                            self.SPModelInstance.y[i1, i2, k, t].fix(0)
                            fixed += 1
        print(str(fixed) + " y variables fixed.")

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
                        if(i1 != i2 and (round(self.modelInstance.x[i1, k, t].value) + round(self.modelInstance.x[i2, k, t].value) == 2)):
                            self.SPModelInstance.Lambda[i1, i2, t].fix(0)
                            fixed += 1
        print(str(fixed) + " lambda variables fixed.")

    def unfix_lambda_variables(self):
        for t in self.modelInstance.t:
            for i1 in self.modelInstance.i:
                for i2 in self.modelInstance.i:
                    self.SPModelInstance.Lambda[i1, i2, t].unfix()

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