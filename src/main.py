from planner import ModelType, Planner
from data_maker import DataDescriptor, DataMaker, TruncatedNormalParameters

if __name__ == '__main__':

    planner = Planner(timeLimit=900,
                      modelType=ModelType.TWO_PHASE_START_TIME_ORDERING,
                      solver="cplex")

    dataDescriptor = DataDescriptor()
    dataDescriptor.patients = 150
    dataDescriptor.days = 5
    dataDescriptor.anesthetists = 2
    dataDescriptor.covidFrequence = 0.5
    dataDescriptor.anesthesiaFrequence = 0.0
    dataDescriptor.specialtyBalance = 0.17
    dataDescriptor.operatingDayDuration = 240
    dataDescriptor.anesthesiaTime = 240
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

    print("Data description:\n")
    print(dataDescriptor)
    print("\nPatients to be operated:\n")
    dataMaker.print_data(dataDictionary)
    planner.solve_model(dataDictionary)
    print("Possible solution, for each day and for each room:\n")
    planner.print_solution()
    planner.plot_graph()