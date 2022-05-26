import logging
import time
from pyomo.util.infeasible import log_infeasible_constraints
from data_maker import DataDescriptor, DataMaker, TruncatedNormalParameters
from fast_complete_heuristic import Planner
from utils import SolutionVisualizer
if __name__ == '__main__':

    solvers = ["cplex"]
    size = [60, 120, 180]
    covid = [0.0, 0.2, 0.5, 0.8, 1.0]
    anesthesia = [0.0, 0.2, 0.5, 0.8, 1.0]
    anesthetists = [1, 2]

    logging.basicConfig(filename='times.log', encoding='utf-8', level=logging.INFO)
    logging.info("Solver\tSize\tCovid\tAnesthesia\tAnesthetists\tMP_building_time\tSP_building_time\tTotal_run_time\tSolver_time\tStatus_OK\tMP_Objective_Function_Value\tSP_Objective_Function_Value\tMP_Upper_Bound\tMP_Time_Limit_Hit\tSP_Time_Limit_Hit")

    for solver in solvers:
        for s in size:
            for c in covid:
                for a in anesthesia:
                    for at in anesthetists:

                        planner = Planner(timeLimit=300, solver=solver)
                        dataDescriptor = DataDescriptor()

                        # complicated instance
                        # dataDescriptor.patients = 120
                        # dataDescriptor.days = 5
                        # dataDescriptor.anesthetists = 2
                        # dataDescriptor.covidFrequence = 0.8
                        # dataDescriptor.anesthesiaFrequence = 0.7
                        # dataDescriptor.specialtyBalance = 0.17
                        # dataDescriptor.operatingDayDuration = 180
                        # dataDescriptor.anesthesiaTime = 180

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
                                        + str(runInfo["MPobjectiveValue"]) + "\t"
                                        + str(runInfo["SPobjectiveValue"]) + "\t"
                                        + str(runInfo["MPUpperBound"]) + "\t"
                                        + str(runInfo["MPTimeLimitHit"]) + "\t"
                                        + str(runInfo["SPTimeLimitHit"]))

                        solution = planner.extract_solution()

                        sv = SolutionVisualizer()
                        sv.print_solution(solution)
                        # sv.plot_graph(solution)
