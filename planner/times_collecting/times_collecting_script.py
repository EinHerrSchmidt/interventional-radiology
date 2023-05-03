import os

if __name__ == '__main__':
    if(not os.path.isdir("./planner/times_collecting/times")):
        os.mkdir("./planner/times_collecting/times")
    # vanilla
    # os.system("python -m planner.times_collecting.main_vanilla")
    # LBBD (heuristic rule)
    os.system("python -m planner.times_collecting.main_LBBD True 30")
    # LBBD (Vanilla)
    # os.system("python -m planner.times_collecting.main_LBBD False 30")