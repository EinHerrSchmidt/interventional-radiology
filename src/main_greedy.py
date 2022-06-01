from data_maker import DataDescriptor, DataMaker, TruncatedNormalParameters
from utils import SolutionVisualizer
from greedy_planner import Planner

if __name__ == '__main__':

    size = [60, 120, 180]
    covid = [0.5]
    anesthesia = [0.8]
    anesthetists = [1, 2]
    for s in size:
        for c in covid:
            for a in anesthesia:
                for at in anesthetists:
                    dataDescriptor = DataDescriptor()

                    dataDescriptor.patients = 80
                    dataDescriptor.days = 5
                    dataDescriptor.anesthetists = 2
                    dataDescriptor.covidFrequence = 0.5
                    dataDescriptor.anesthesiaFrequence = 0.5
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
                    dataDictionary = dataMaker.create_data_dictionary(dataContainer, dataDescriptor)

                    # print("Data description:\n")
                    # print(dataDescriptor)
                    # dataMaker.print_data(dataDictionary)

                    planner = Planner(dataDictionary)

                    solution = planner.compute_solution()
                    sv = SolutionVisualizer()
                    sv.print_solution(solution)
                    sv.plot_graph(solution)

                    print("Objective function value: " + str(planner.compute_objective_value()))
