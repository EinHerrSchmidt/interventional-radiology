import logging
import sys
import time
from data_maker import DataDescriptor, DataMaker
from utils import SolutionVisualizer
from greedy_planner import Planner

if __name__ == '__main__':

    variant = sys.argv[1] == "True"

    size = [100, 140, 180]
    covid = [0.2, 0.5, 0.8]
    anesthesia = [0.0]
    anesthetists = [1]
    delayWeights = [0.25, 0.5, 0.75]
    delayEstimate = ["UO", "procedure"]

    anesthetistAssignmentStrategy = None

    if(variant):
        logging.basicConfig(filename='./times/greedy_WIS_times.log', encoding='utf-8', level=logging.INFO)
        anesthetistAssignmentStrategy = "WIS"
    else:
        logging.basicConfig(filename='./times/greedy_standard_times.log', encoding='utf-8', level=logging.INFO)
        anesthetistAssignmentStrategy = "single_anesthetist_per_room"
    logging.info("Solver\tSize\tCovid\tAnesthesia\tAnesthetists\tSolving_time\tObjective_function_value\tSpecialty_1_OR_usage\tSpecialty_2_OR_usage\tSpecialty_1_selected_ratio\tSpecialty_2_selected_ratio")

    for s in size:
        for c in covid:
            for a in anesthesia:
                for at in anesthetists:
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
                    planner = Planner(packingStrategy=None, anesthetistAssignmentStrategy=anesthetistAssignmentStrategy)
                    planner.solve_model(dataDictionary)
                    elapsed = (time.time() - t)

                    solution = planner.extract_solution()
                    sv = SolutionVisualizer()
                    usageInfo = sv.compute_room_utilization(solution=solution, dataDictionary=dataDictionary)

                    logging.info(str(s) + "\t"
                                    + str(c) + "\t"
                                    + str(a) + "\t"
                                    + str(at) + "\t"
                                    + str(round(elapsed, 2)) + "\t"
                                    + str(planner.compute_objective_value()) + "\t"
                                    + str(usageInfo["Specialty1ORUsage"]) + "\t"
                                    + str(usageInfo["Specialty2ORUsage"]) + "\t"
                                    + str(usageInfo["Specialty1SelectedRatio"]) + "\t"
                                    + str(usageInfo["Specialty2SelectedRatio"])
                                    )
                    
                    # solution = planner.extract_solution()
                    # sv = SolutionVisualizer()
                    # print("Objective function value: " + str(planner.compute_objective_value()))
