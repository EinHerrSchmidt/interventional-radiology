import logging
import sys
import time
from data_maker import DataDescriptor, DataMaker, TruncatedNormalParameters
import LBBD_planner as lbbd
import LBBD_planner_3_phase as lbbdv
if __name__ == '__main__':

    variant = sys.argv[1] == "True"
    maxIterations = int(sys.argv[2])

    solvers = ["cplex"]
    size = [60, 120, 180]
    covid = [0.2, 0.5, 0.8]
    anesthesia = [0.0, 0.2, 0.5, 0.8, 1.0]
    anesthetists = [1, 2]

    if(variant):
        logging.basicConfig(filename='3Phase_LBBD_times.log', encoding='utf-8', level=logging.INFO)
    else:
        logging.basicConfig(filename='vanilla_LBBD_times.log', encoding='utf-8', level=logging.INFO)
    logging.info("Solver\tSize\tCovid\tAnesthesia\tAnesthetists\tMP_building_time\tSP_building_time\tTotal_run_time\tSolver_time\tStatus_OK\tObjective_Function_Value\tMP_Time_Limit_Hit\tWorst_MP_Bound_Time_Limit\tIterations")

    for solver in solvers:
        for s in size:
            for c in covid:
                for a in anesthesia:
                    for at in anesthetists:

                        planner = None
                        if(variant):
                            planner = lbbdv.Planner(timeLimit=300, gap = 0.05, iterationsCap=maxIterations, solver=solver)
                        else:
                            planner = lbbd.Planner(timeLimit=300, gap = 0.05, iterationsCap=maxIterations, solver=solver)

                        dataDescriptor = DataDescriptor()

                        dataDescriptor.patients = s
                        dataDescriptor.days = 5
                        dataDescriptor.anesthetists = at
                        dataDescriptor.covidFrequence = c
                        dataDescriptor.anesthesiaFrequence = a
                        dataDescriptor.specialtyBalance = 0.17
                        dataDescriptor.operatingDayDuration = 270
                        dataDescriptor.anesthesiaTime = 270
                        dataDescriptor.operatingTimeDistribution = TruncatedNormalParameters(low=30,
                                                                                                high=120,
                                                                                                mean=60,
                                                                                                stdDev=20)
                        dataDescriptor.priorityDistribution = TruncatedNormalParameters(low=1,
                                                                                        high=120,
                                                                                        mean=60,
                                                                                        stdDev=10)
                        dataMaker = DataMaker(seed=52876)
                        dataContainer = dataMaker.create_data_container(dataDescriptor)
                        dataDictionary = dataMaker.create_data_dictionary(
                            dataContainer, dataDescriptor)
                        print("Data description:\n")
                        print(dataDescriptor)
                        t = time.time()
                        # print("\nPatients to be operated:\n")
                        dataMaker.print_data(dataDictionary)
                        runInfo = planner.solve_model(dataDictionary)
                        elapsed = (time.time() - t)

                        logging.basicConfig(filename='times.log', encoding='utf-8', level=logging.INFO)
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
                                        + str(runInfo["worstMPBoundTimeLimitHit"]) + "\t"
                                        + str(runInfo["iterations"]))

                        # solution = planner.extract_solution()

                        # sv = SolutionVisualizer()
                        # sv.print_solution(solution)
                        # sv.plot_graph(solution)
