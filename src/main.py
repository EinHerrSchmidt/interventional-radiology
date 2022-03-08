from planner import Planner
from data_maker import DataMaker
import sys
import os

if __name__ == '__main__':
    logDir = 'log'
    logFile = 'log.txt'
    if(not os.path.exists('../' + logDir)):
        os.mkdir('../' + logDir)

    planner = Planner()

    data = DataMaker().generate_example_data()
    print(data)

    planner.solve_model(data)



    sys.stdout = open('../' + logDir + '/' + logFile, 'w')
    planner.modelInstance.display()
    sys.stdout.close()
