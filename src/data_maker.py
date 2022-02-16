from venv import create
from scipy.stats import truncnorm
import numpy as np


class DataMaker:
    def __init__(self):
        pass

    def generate_truncnorm_sample(self, patients, lower, upper, mean, stdDev, isTime):
        truncatedNormal = truncnorm((lower - mean) / stdDev, (upper - mean) / stdDev,
                                    loc=mean,
                                    scale=stdDev)
        sample = truncatedNormal.rvs(patients)
        return self.create_dictionary_entry(sample, isTime)

    def create_dictionary_entry(self, sample, isTime):
        dict = {}
        for i in range(0, len(sample)):
            if(isTime):
                dict[(i + 1)] = int(sample[i]) - int(sample[i]) % 10
            else:
                dict[(i + 1)] = int(sample[i])
        return dict

    def generate_example_data(self):
        np.random.seed(seed=54667)
        patients = 150
        return {None: {
            'I': {None: patients},
            'K': {None: 2},
            'T': {None: 5},
            's': {
                (1, 1): 480,  # 480 minutes, 8 hours availability
                (1, 2): 480,
                (1, 3): 480,
                (1, 4): 480,
                (1, 5): 480,
                (2, 1): 480,
                (2, 2): 480,
                (2, 3): 480,
                (2, 4): 480,
                (2, 5): 480,
            },
            'p': self.generate_truncnorm_sample(patients, 30, 120, 60, 20, isTime=True), # surgery times
            'r': self.generate_truncnorm_sample(patients, 1, 10, 5, 3, isTime=False), # urgency coefficients
            'd': self.generate_truncnorm_sample(patients, 1, 6, 2, 3, isTime=False) # distances
        }}
