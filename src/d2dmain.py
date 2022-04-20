from daily_planner import ModelType, Planner
from data_maker import DataContainer, DataDescriptor, DataMaker, TruncatedNormalParameters

if __name__ == '__main__':

    planner = Planner(timeLimit=900,
                      modelType=ModelType.START_TIME_ORDERING,
                      solver="cplex")

    dataDescriptor = DataDescriptor()
    dataDescriptor.patients = 60
    dataDescriptor.days = 1
    dataDescriptor.anesthetists = 2
    dataDescriptor.covidFrequence = 0.5
    dataDescriptor.anesthesiaFrequence = 0.2
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

    print("Data description:\n")
    print(dataDescriptor)
    print("\nPatients to be operated:\n")
    # dataMaker.print_data(dataDictionary)
    planner.solve_model(dataMaker, dataContainer, dataDescriptor)
    print("Possible solution, for each day and for each room:\n")
    planner.print_solution()
    # planner.plot_graph()