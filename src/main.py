from planner import ModelType, Planner
from data_maker import DataDescriptor, DataMaker, TruncatedNormalParameters

if __name__ == '__main__':
    #logDir = 'log'
    #logFile = 'log.txt'
    #if(not os.path.exists('../' + logDir)):
    #    os.mkdir('../' + logDir)

    planner = Planner(timeLimit=900,
                      modelType=ModelType.SIMPLE_ORDERING,
                      solver="cplex")

    dataDescriptor = DataDescriptor()
    dataDescriptor.patients = 60
    dataDescriptor.days = 5
    dataDescriptor.anesthetists = 2
    dataDescriptor.covidFrequence = 0.8
    dataDescriptor.anesthesiaFrequence = 0.2
    dataDescriptor.specialtyBalance = 0.3
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

    # sys.stdout = open('../' + logDir + '/' + logFile, 'w')
    print("Data description:\n")
    print(dataDescriptor)
    print("\nPatients to be operated:\n")
    dataMaker.print_data(data)

    print("\nCreating model instance...")
    planner.create_model_instance(data)
    print("Model instance created.")

    print("Beginning solving instance.")
    planner.solve_model()
    # planner.modelInstance.display()
    print("Possible solution, for each day and for each room:\n")
    planner.print_solution()
    # sys.stdout.close()

    # sys.stdout = sys.__stdout__
    solution = planner.extract_solution()
    
    planner.plot_graph()