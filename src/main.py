from planner import ModelType, Planner
from data_maker import DataDescriptor, DataMaker, TruncatedNormalParameters

if __name__ == '__main__':

    planner = Planner(timeLimit=900,
                      modelType=ModelType.TWO_PHASE_START_TIME_ORDERING,
                      solver="cbc")

    dataDescriptor = DataDescriptor()
    dataDescriptor.patients = 150
    dataDescriptor.days = 5
    dataDescriptor.anesthetists = 2
    dataDescriptor.covidFrequence = 0.5
    dataDescriptor.anesthesiaFrequence = 0.2
    dataDescriptor.specialtyBalance = 0.17
    dataDescriptor.operatingTimeDistribution = TruncatedNormalParameters(low=30,
                                                                         high=120,
                                                                         mean=60,
                                                                         stdDev=20)
    dataDescriptor.priorityDistribution = TruncatedNormalParameters(low=1,
                                                                    high=120,
                                                                    mean=60,
                                                                    stdDev=10)
    dataMaker = DataMaker()
    data = dataMaker.generate_data(dataDescriptor, seed=52876)

    print("Data description:\n")
    print(dataDescriptor)
    print("\nPatients to be operated:\n")
    dataMaker.print_data(data)
    planner.solve_model(data)
    print("Possible solution, for each day and for each room:\n")
    planner.print_solution()
    planner.plot_graph()