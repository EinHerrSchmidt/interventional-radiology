from planner import Planner
from data_maker import DataMaker
import sys

if __name__ == '__main__':
    planner = Planner()
    data = DataMaker().generate_example_data()
    planner.solve(data)

    sys.stdout = open('../logs/log.txt', 'w')
    planner.secondaryModelInstance.display()
    sys.stdout.close()
