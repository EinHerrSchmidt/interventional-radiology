import logging
import sys
import time
from data_maker import DataDescriptor, DataMaker
import LBBD_planner as lbbd
import LBBD_planner_3_phase as lbbdv
from utils import SolutionVisualizer
if __name__ == '__main__':

    variant = sys.argv[1] == "True"
    maxIterations = int(sys.argv[2])

    solvers = ["cplex"]
    size = [100, 140, 180]
    covid = [0.2, 0.5, 0.8]
    anesthesia = [0.2, 0.5, 0.8]
    anesthetists = [1, 2]

    if(variant):
        logging.basicConfig(filename='./times/3Phase_LBBD_times.log', encoding='utf-8', level=logging.INFO)
    else:
        logging.basicConfig(filename='./times/vanilla_LBBD_times.log', encoding='utf-8', level=logging.INFO)
    logging.info("Solver\tSize\tCovid\tAnesthesia\tAnesthetists\tMP_building_time\tSP_building_time\tTotal_run_time\tSolver_time\tStatus_OK\tObjective_Function_Value\tMP_Time_Limit_Hit\tSP_Time_Limit_Hit\tWorst_MP_Bound_Time_Limit\tIterations\tFailed\tSpecialty_1_OR_usage\tSpecialty_2_OR_usage\tSpecialty_1_selected_ratio\tSpecialty_2_selected_ratio")

    for solver in solvers:
        for s in size:
            for c in covid:
                for a in anesthesia:
                    for at in anesthetists:

                        planner = None
                        if(variant):
                            planner = lbbdv.Planner(timeLimit=600, gap = 0.0, iterationsCap=maxIterations, solver=solver)
                        else:
                            planner = lbbd.Planner(timeLimit=600, gap = 0.0, iterationsCap=maxIterations, solver=solver)

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
                        runInfo = planner.solve_model(dataDictionary)
                        elapsed = (time.time() - t)

                        if(runInfo["fail"] == False):
                            solution = planner.extract_solution()
                            sv = SolutionVisualizer()
                            usageInfo = sv.compute_room_utilization(solution=solution, dataDictionary=dataDictionary)

                        logging.info(solver + "\t"
                                        + str(s) + "\t"
                                        + str(c) + "\t"
                                        + str(a) + "\t"
                                        + str(at) + "\t"
                                        + str(runInfo["MPBuildingTime"]) + "\t"
                                        + str(runInfo["SPBuildingTime"]) + "\t"
                                        + str(round(elapsed, 2)) + "\t"
                                        + str(runInfo["solutionTime"]) + "\t"
                                        + str(runInfo["statusOk"]) + "\t"
                                        + str(runInfo["objectiveValue"]) + "\t"
                                        + str(runInfo["MPTimeLimitHit"]) + "\t"
                                        + str(runInfo["SPTimeLimitHit"]) + "\t"
                                        + str(runInfo["worstMPBoundTimeLimitHit"]) + "\t"
                                        + str(runInfo["iterations"]) + "\t"
                                        + str(runInfo["fail"]) + "\t"
                                        + str(usageInfo["Specialty1ORUsage"]) + "\t"
                                        + str(usageInfo["Specialty2ORUsage"]) + "\t"
                                        + str(usageInfo["Specialty1SelectedRatio"]) + "\t"
                                        + str(usageInfo["Specialty2SelectedRatio"])
                                        )

                        # sv.print_solution(solution)
                        # sv.plot_graph(solution)
