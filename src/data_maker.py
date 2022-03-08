from venv import create
from xmlrpc.client import MAXINT
from scipy.stats import truncnorm
from scipy.stats import binom
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

    def generate_binomial_sample(self, patients, p, isSpecialty):
        sample = binom.rvs(1, p, size=patients)
        if(isSpecialty):
            sample = sample + 1
        return self.create_dictionary_entry(sample, isTime=False)

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
        patients = 20
        return {None: {
            'I': {None: patients},
            'J': {None: 2},
            'K': {None: 4},
            'T': {None: 5},
            'A': {None: 2},
            'M': {None: 5},
            's': {
                (1, 1): 480, (2, 1): 480, (3, 1): 480, (4, 1): 480,
                (1, 2): 480, (2, 2): 480, (3, 2): 480, (4, 2): 480,
                (1, 3): 480, (2, 3): 480, (3, 3): 480, (4, 3): 480,
                (1, 4): 480, (2, 4): 480, (3, 4): 480, (4, 4): 480,
                (1, 5): 480, (2, 5): 480, (3, 5): 480, (4, 5): 480,
            },
            'An': {
                (1, 1): 480, (1, 2): 480, (1, 3): 480, (1, 4): 480, (1, 5): 480,
                (2, 1): 480, (2, 2): 480, (2, 3): 480, (2, 4): 480, (2, 5): 480,
            },
            'tau': {
                (1, 1, 1): 1, (1, 2, 1): 1, (2, 3, 1): 1, (2, 4, 1): 1,
                (1, 1, 2): 1, (1, 2, 2): 1, (2, 3, 2): 1, (2, 4, 2): 1,
                (1, 1, 3): 1, (1, 2, 3): 1, (2, 3, 3): 1, (2, 4, 3): 1,
                (1, 1, 4): 1, (1, 2, 4): 1, (2, 3, 4): 1, (2, 4, 4): 1,
                (1, 1, 5): 1, (1, 2, 5): 1, (2, 3, 5): 1, (2, 4, 5): 1,

                (2, 1, 1): 0, (2, 2, 1): 0, (1, 3, 1): 0, (1, 4, 1): 0,
                (2, 1, 2): 0, (2, 2, 2): 0, (1, 3, 2): 0, (1, 4, 2): 0,
                (2, 1, 3): 0, (2, 2, 3): 0, (1, 3, 3): 0, (1, 4, 3): 0,
                (2, 1, 4): 0, (2, 2, 4): 0, (1, 3, 4): 0, (1, 4, 4): 0,
                (2, 1, 5): 0, (2, 2, 5): 0, (1, 3, 5): 0, (1, 4, 5): 0,
            },
            'p': self.generate_truncnorm_sample(patients, 30, 120, 60, 20, isTime=True),
            'r': self.generate_truncnorm_sample(patients, lower=1, upper=120, mean=60, stdDev=10, isTime=False),
            'a': self.generate_binomial_sample(patients, 0.1, isSpecialty=False),
            'c': self.generate_binomial_sample(patients, 0.2, isSpecialty=False),
            'specialty': self.generate_binomial_sample(patients, 0.3, isSpecialty=True),
            'bigM': {
                1: 1000000,
                2: 1000000,
                3: 1000000,
                4: 1000000,
                5: 1000000
            }
        }}
