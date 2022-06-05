import os

if __name__ == '__main__':
    # vanilla LBBD
    os.system("python main_LBBD.py False 50")
    # 3-phase LBBD
    os.system("python main_LBBD.py True 50")