import logging
import time
from pyomo.util.infeasible import log_infeasible_constraints
from data_maker import DataDescriptor, DataMaker, TruncatedNormalParameters
from LBBDPlanner import Planner
from utils import SolutionVisualizer
if __name__ == '__main__':

    planner = Planner(timeLimit=30, solver="cplex")
    dataDescriptor = DataDescriptor()

    # complicated instance
    dataDescriptor.patients = 60
    dataDescriptor.days = 5
    dataDescriptor.anesthetists = 2
    dataDescriptor.covidFrequence = 0.8
    dataDescriptor.anesthesiaFrequence = 0.7
    dataDescriptor.specialtyBalance = 0.17
    dataDescriptor.operatingDayDuration = 180
    dataDescriptor.anesthesiaTime = 180

    # dataDescriptor.patients = 180
    # dataDescriptor.days = 5
    # dataDescriptor.anesthetists = 2
    # dataDescriptor.covidFrequence = 0.2
    # dataDescriptor.anesthesiaFrequence = 0.2
    # dataDescriptor.specialtyBalance = 0.17
    # dataDescriptor.operatingDayDuration = 240
    # dataDescriptor.anesthesiaTime = 240
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
    # dataMaker.print_data(dataDictionary)
    runInfo = planner.solve_model(dataDictionary)
    elapsed = (time.time() - t)

    logging.basicConfig(filename='times.log',
                        encoding='utf-8', level=logging.INFO)
    logging.info(
        "MP_building_time\tSP_overall_building_time\tTotal_run_time\tSolver_time\tStatus_OK\tObjective_Function_Value\tIterations")
    logging.info(str(runInfo["MPBuildingTime"]) + "\t"
                 + str(runInfo["overallSPBuildingTime"]) + "\t"
                 + str(round(elapsed, 2)) + "\t"
                 + str(runInfo["solutionTime"]) + "\t"
                 + str(runInfo["statusOk"]) + "\t"
                 + str(runInfo["objectiveValue"]) + "\t"
                 + str(runInfo["iterations"]))

    solution = planner.extract_solution()

    sv = SolutionVisualizer()
    sv.print_solution(solution)
    sv.plot_graph(solution)
