import logging
import sys
import time
from planner import FastCompleteHeuristicPlanner, FastCompleteLagrangeanHeuristicPlanner
from planner.utils import SolutionVisualizer
from planner.data_maker import DataDescriptor, DataMaker

variant = sys.argv[1] == "True"

solvers = ["cplex"]
size = [100, 140, 180]
covid = [0.2, 0.5, 0.8]
anesthesia = [0.2, 0.5, 0.8]
anesthetists = [1, 2]

logging.basicConfig(filename='./planner/times_collecting/times/fch_times.log',
                    encoding='utf-8',
                    level=logging.INFO,
                    filemode="w")
logging.info("Solver\tSize\tCovid\tAnesthesia\tAnesthetists\tCumulated_building_time\tTotal_run_time\tSolver_time\tStatus_OK\tMP_Objective_Function_Value\tSP_Objective_Function_Value\tMP_Upper_Bound\tMP_Time_Limit_Hit\tSP_Time_Limit_Hit\tObjective_Function_LB\tSpecialty_1_OR_usage\tSpecialty_2_OR_usage\tSpecialty_1_selected_ratio\tSpecialty_2_selected_ratio")

for solver in solvers:
    for s in size:
        for c in covid:
            for a in anesthesia:
                 for at in anesthetists:

                    planner = None
                    if(variant):
                        planner = FastCompleteLagrangeanHeuristicPlanner(
                        timeLimit=590, gap=0.0, solver=solver)
                    else:
                        planner = FastCompleteHeuristicPlanner(
                        timeLimit=590, gap=0.0, solver=solver)

                    dataDescriptor = DataDescriptor()

                    dataDescriptor.patients = s
                    dataDescriptor.days = 5
                    dataDescriptor.anesthetists = at
                    dataDescriptor.covidFrequence = c
                    dataDescriptor.anesthesiaFrequence = a
                    dataDescriptor.specialtyBalance = 0.17
                    dataDescriptor.operatingDayDuration = 270
                    dataDescriptor.anesthesiaTime = 270

                    dataMaker = DataMaker(seed=52876)
                    dataDictionary = dataMaker.create_data_dictionary(
                        dataDescriptor)
                    t = time.time()
                    dataMaker.print_data(dataDictionary)
                    planner.solve_model(dataDictionary)
                    run_info = planner.extract_run_info()
                    elapsed = (time.time() - t)

                    solution = planner.extract_solution()
                    sv = SolutionVisualizer()
                    usageInfo = sv.compute_room_utilization(
                        solution=solution, dataDictionary=dataDictionary)

                    logging.info(solver + "\t"
                                    + str(s) + "\t"
                                    + str(c) + "\t"
                                    + str(a) + "\t"
                                    + str(at) + "\t"
                                    + str(run_info["cumulated_building_time"]) + "\t"
                                    + str(round(elapsed, 2)) + "\t"
                                    + str(run_info["solver_time"]) + "\t"
                                    + str(run_info["status_ok"]) + "\t"
                                    + str(run_info["MP_objective_function_value"]) + "\t"
                                    + str(run_info["objective_function_value"]) + "\t"
                                    + str(run_info["MP_upper_bound"]) + "\t"
                                    + str(run_info["MP_time_limit_hit"]) + "\t"
                                    + str(run_info["time_limit_hit"]) + "\t"
                                    + str(usageInfo["Specialty1ORUsage"]) + "\t"
                                    + str(usageInfo["Specialty2ORUsage"]) + "\t"
                                    + str(usageInfo["Specialty1SelectedRatio"]) + "\t"
                                    + str(usageInfo["Specialty2SelectedRatio"])
                                    )

                    # sv.print_solution(solution)
                    # sv.plot_graph(solution)
