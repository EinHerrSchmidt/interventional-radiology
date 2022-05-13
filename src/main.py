import logging
import time
from pyomo.util.infeasible import log_infeasible_constraints
from data_maker import DataDescriptor, DataMaker, TruncatedNormalParameters
from lbbd_planner import Planner
if __name__ == '__main__':

    solvers = ["cplex", "gurobi", "cbc"]
    for solver in solvers:
        logging.basicConfig(filename='times.log', encoding='utf-8', level=logging.INFO)
        logging.info(solver)
        logging.info("\n")

        # planner = Planner(timeLimit=900, solver="cbc")
        planner = Planner(timeLimit=900, solver=solver)

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

        # dataDescriptor.patients = 80
        # dataDescriptor.days = 5
        # dataDescriptor.anesthetists = 2
        # dataDescriptor.covidFrequence = 0.4
        # dataDescriptor.anesthesiaFrequence = 0.5
        # dataDescriptor.specialtyBalance = 0.17
        # dataDescriptor.operatingDayDuration = 240
        # dataDescriptor.anesthesiaTime = 240

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
        dataDictionary = dataMaker.create_data_dictionary(dataContainer, dataDescriptor)

        print("Data description:\n")
        print(dataDescriptor)
        t = time.time()
        # print("\nPatients to be operated:\n")
        # dataMaker.print_data(dataDictionary)
        planner.solve_model(dataDictionary)
        # print("Possible solution, for each day and for each room:\n")
        elapsed = (time.time() - t)
        logging.basicConfig(filename='times.log', encoding='utf-8', level=logging.INFO)
        logging.info("Overall elapsed time: " + str(round(elapsed, 2)) + "s")
        planner.print_solution()
        planner.plot_graph()
