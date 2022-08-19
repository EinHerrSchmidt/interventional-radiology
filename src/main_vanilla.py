import logging
import sys
import time
from data_maker import DataDescriptor, DataMaker
import planners
from utils import SolutionVisualizer
if __name__ == '__main__':

    solvers = ["cplex"]
    size = [140]
    covid = [0.2, 0.5, 0.8]
    anesthesia = [0.0]
    anesthetists = [1]
    delayWeights = [0.25, 0.5, 0.75]
    delayEstimate = ["UO", "procedure"]

    logging.basicConfig(filename='./times/vanilla_times.log', encoding='utf-8', level=logging.INFO)
    logging.info("Solver\tSize\tCovid\tAnesthesia\tAnesthetists\tDelayEstimation\tDelayWeight\tBuilding_time\tRun_time\tSolverTime\tStatus_OK\tObjective_Function_Value\tTime_Limit_Hit\tUpper_bound\tGap\tSpecialty_1_OR_usage\tSpecialty_2_OR_usage\tSpecialty_1_selected_ratio\tSpecialty_2_selected_ratio\tPO\tPR\tSO\tSR\tCO\tCR")

    for solver in solvers:
        for s in size:
            for c in covid:
                for a in anesthesia:
                    for at in anesthetists:
                        for dw in delayWeights:
                            for de in delayEstimate:
                        
                                planner = planners.SinglePhaseStartingMinutePlanner(600, 0.0, solver)

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
                                # sv.print_solution(solution)
                                # sv.plot_graph(solution)

                                logging.info(solver + "\t"
                                                + str(s) + "\t"
                                                + str(c) + "\t"
                                                + str(a) + "\t"
                                                + str(at) + "\t"
                                                + str(de) + "\t"
                                                + str(dw) + "\t"
                                                + str(runInfo["BuildingTime"]) + "\t"
                                                + str(round(elapsed, 2)) + "\t"
                                                + str(runInfo["SolverTime"]) + "\t"
                                                + str(runInfo["StatusOK"]) + "\t"
                                                + str(sv.compute_solution_value(solution)) + "\t"
                                                + str(runInfo["TimeLimitHit"]) + "\t"
                                                + str(runInfo["UpperBound"]) + "\t"
                                                + str(runInfo["Gap"]) + "\t"
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


