import os

if __name__ == '__main__':
    if(not os.path.isdir("./planner/times_collecting/times")):
        os.mkdir("./planner/times_collecting/times")
    # lagrangian "slow" complete heuristic
    os.system("python -m planner.times_collecting.main_SCH True")
    # lagrangian "fast" complete heuristic
    os.system("python -m planner.times_collecting.main_FCH True")
    # "slow" complete heuristic
    os.system("python -m planner.times_collecting.main_SCH False")
    # "fast" complete heuristic
    os.system("python -m planner.times_collecting.main_FCH False")
    # vanilla
    os.system("python -m planner.times_collecting.main_vanilla")
    # LBBD
    os.system("python -m planner.times_collecting.main_LBBD False 10")
    # 3-phase LBBD
    os.system("python -m planner.times_collecting.main_LBBD.py True 10")