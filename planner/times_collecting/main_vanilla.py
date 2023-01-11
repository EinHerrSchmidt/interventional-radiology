import logging
import sys
import time
from planner import SimplePlanner
from planner.utils import SolutionVisualizer
from planner.data_maker import DataDescriptor, DataMaker
if __name__ == '__main__':

    solvers = ["cplex"]
    size = [100, 140, 180]
    covid = [0.2, 0.5, 0.8]
    anesthesia = [0.2, 0.5, 0.8]
    anesthetists = [1, 2]

    logging.basicConfig(filename='./planner/times_collecting/times/vanilla_times.log', encoding='utf-8', level=logging.INFO)
    logging.info("Solver\tSize\tCovid\tAnesthesia\tAnesthetists\tBuilding_time\tRun_time\tSolverTime\tStatus_OK\tObjective_Function_Value\tTime_Limit_Hit\tUpper_bound\tGap\tSpecialty_1_OR_usage\tSpecialty_2_OR_usage\tSpecialty_1_selected_ratio\tSpecialty_2_selected_ratio")

    for solver in solvers:
        for s in size:
            for c in covid:
                for a in anesthesia:
                    for at in anesthetists:
                        
                        planner = SimplePlanner(600, 0.05, solver)

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
                        dataDictionary = dataMaker.create_data_dictionary(dataDescriptor)
                        t = time.time()
                        dataMaker.print_data(dataDictionary)
                        planner.solve_model(dataDictionary)
                        elapsed = (time.time() - t)

                        run_info = planner.extract_run_info()
                        solution = planner.extract_solution()
                        sv = SolutionVisualizer()
                        usageInfo = sv.compute_room_utilization(solution=solution, dataDictionary=dataDictionary)
                        # sv.print_solution(solution)
                        # sv.plot_graph(solution)

                        logging.info(solver + "\t"
                                        + str(s) + "\t"
                                        + str(c) + "\t"
                                        + str(a) + "\t"
                                        + str(at) + "\t"
                                        + str(run_info["cumulated_building_time"]) + "\t"
                                        + str(round(elapsed, 2)) + "\t"
                                        + str(run_info["solver_time"]) + "\t"
                                        + str(run_info["status_ok"]) + "\t"
                                        + str(sv.compute_solution_value(solution)) + "\t"
                                        + str(run_info["time_limit_hit"]) + "\t"
                                        + str(run_info["upper_bound"]) + "\t"
                                        + str(run_info["gap"]) + "\t"
                                        + str(usageInfo["Specialty1ORUsage"]) + "\t"
                                        + str(usageInfo["Specialty2ORUsage"]) + "\t"
                                        + str(usageInfo["Specialty1SelectedRatio"]) + "\t"
                                        + str(usageInfo["Specialty2SelectedRatio"])
                                        )


