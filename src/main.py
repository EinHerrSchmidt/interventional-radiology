from planner import Planner
from data_maker import DataMaker
import sys
import os

if __name__ == '__main__':
    planner = Planner()
    data = DataMaker().generate_example_data()
    planner.solve(data)

    logDir = 'log'
    logFile = 'log.txt'

    if(not os.path.exists('../' + logDir)):
        os.mkdir('../' + logDir)

    sys.stdout = open('../' + logDir + '/' + logFile, 'w')
    planner.secondaryModelInstance.display()
    sys.stdout.close()
