import logging
import sys
import time
from data_maker import DataDescriptor, DataMaker
import fast_complete_heuristic as fce
import fast_complete_heuristic_variant as fcev
from utils import SolutionVisualizer
if __name__ == '__main__':

    variant = sys.argv[1] == "True"

    solvers = ["cplex"]
    size = [100, 140]
    covid = [0.5]
    anesthesia = [0.2]
    anesthetists = [1]
    delayWeights = [0.2, 0.4, 0.6, 0.8, 1.0]
    delayEstimate = ["UO", "procedure"]

    logging.basicConfig(filename='./times/fce_times.log', encoding='utf-8', level=logging.INFO)
    logging.info("Solver\tSize\tCovid\tAnesthesia\tAnesthetists\tDelayEstimation\tDelayWeight\tMP_building_time\tSP_building_time\tTotal_run_time\tMP_Solver_time\tSP_Solver_time\tStatus_OK\tMP_Objective_Function_Value\tSP_Objective_Function_Value\tMP_Upper_Bound\tMP_Time_Limit_Hit\tSP_Time_Limit_Hit\tObjective_Function_LB\tSpecialty_1_OR_usage\tSpecialty_2_OR_usage\tSpecialty_1_selected_ratio\tSpecialty_2_selected_ratio\tPO\tPR\tSO\tSR\tCO\tCR")

    for solver in solvers:
        for s in size:
            for c in covid:
                for a in anesthesia:
                    for at in anesthetists:
                        for dw in delayWeights:
                            for de in delayEstimate:

                                planner = None
                                if(variant):
                                    planner = fcev.Planner(timeLimit=590, gap = 0.0, solver=solver)
                                else:
                                    planner = fce.Planner(timeLimit=590,gap = 0.0, solver=solver)

                                dataDescriptor = DataDescriptor()

                                dataDescriptor.patients = s
                                dataDescriptor.days = 5
                                dataDescriptor.anesthetists = at
                                dataDescriptor.covidFrequence = c
                                dataDescriptor.anesthesiaFrequence = a
                                dataDescriptor.specialtyBalance = 0.17
                                dataDescriptor.operatingDayDuration = 270
                                dataDescriptor.anesthesiaTime = 270
                                dataDescriptor.delayWeight = dw
                                dataDescriptor.delayEstimation = de

                                dataMaker = DataMaker(seed=52876)
                                dataDictionary = dataMaker.create_data_dictionary(dataDescriptor)
                                t = time.time()
                                dataMaker.print_data(dataDictionary)
                                runInfo = planner.solve_model(dataDictionary)
                                elapsed = (time.time() - t)

                                solution = planner.extract_solution()
                                sv = SolutionVisualizer()
                                usageInfo = sv.compute_room_utilization(solution=solution, dataDictionary=dataDictionary)
                                precedencePartitioning = sv.compute_solution_partitioning_by_precedence(solution=solution)

                                logging.info(solver + "\t"
                                                + str(s) + "\t"
                                                + str(c) + "\t"
                                                + str(a) + "\t"
                                                + str(at) + "\t"
                                                + str(de) + "\t"
                                                + str(dw) + "\t"
                                                + str(runInfo["MPBuildingTime"]) + "\t"
                                                + str(runInfo["SPBuildingTime"]) + "\t"
                                                + str(round(elapsed, 2)) + "\t"
                                                + str(runInfo["MPSolverTime"]) + "\t"
                                                + str(runInfo["SPSolverTime"]) + "\t"
                                                + str(runInfo["statusOk"]) + "\t"
                                                + str(runInfo["MPobjectiveValue"]) + "\t"
                                                + str(sv.compute_solution_value(solution)) + "\t"
                                                + str(runInfo["MPUpperBound"]) + "\t"
                                                + str(runInfo["MPTimeLimitHit"]) + "\t"
                                                + str(runInfo["SPTimeLimitHit"]) + "\t"
                                                + str(runInfo["objectiveFunctionLB"]) + "\t"
                                                + str(usageInfo["Specialty1ORUsage"]) + "\t"
                                                + str(usageInfo["Specialty2ORUsage"]) + "\t"
                                                + str(usageInfo["Specialty1SelectedRatio"]) + "\t"
                                                + str(usageInfo["Specialty2SelectedRatio"]) + "\t"
                                                + str(precedencePartitioning[0]) + "\t"
                                                + str(precedencePartitioning[1]) + "\t"
                                                + str(precedencePartitioning[2]) + "\t"
                                                + str(precedencePartitioning[3]) + "\t"
                                                + str(precedencePartitioning[4]) + "\t"
                                                + str(precedencePartitioning[5])
                                                )

                                # sv.print_solution(solution)
                                # sv.plot_graph(solution)
