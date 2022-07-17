import os

if __name__ == '__main__':
    # "slow" complete heuristic
    # os.system("python main_SCE.py False")
    # "fast" complete heuristic
    # os.system("python main_FCE.py False")
    # vanilla
    # os.system("python main_vanilla.py")
    # LBBD
    os.system("python main_LBBD.py False 10")
    # 3-phase LBBD
    os.system("python main_LBBD.py False 10")