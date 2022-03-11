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
        print(str(sum(sample)))
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

    def create_room_timetable(self, K, T):
        dict = {}
        for k in range(0, K):
            for t in range(0, T):
                dict[(k + 1, t + 1)] = 480
        return dict

    def create_anestethists_timetable(self, A, T):
        dict = {}
        for a in range(0, A):
            for t in range(0, T):
                dict[(a + 1, t + 1)] = 480
        return dict

    def create_patient_specialty_table(self, I, J, specialtyLabels):
        dict = {}
        for i in range(0, I):
            for j in range(0, J):
                if(specialtyLabels[(i + 1)] == j + 1):
                    dict[(i + 1, j + 1)] = 1
                else:
                    dict[(i + 1, j + 1)] = 0
        return dict

    def create_room_specialty_assignment(self, J, K, T):
        dict = {}
        for j in range(0, J):
            for k in range(0, K):
                for t in range(0, T):
                    if((j + 1 == 1 and (k + 1 == 1 or k + 1 == 2)) or (j + 1 == 2 and (k + 1 == 3 or k + 1 == 4))):
                        dict[(j + 1, k + 1, t + 1)] = 1
                    else:
                        dict[(j + 1, k + 1, t + 1)] = 0
        return dict

    def generate_example_data(self):
        np.random.seed(seed=54667)
        patients = 50
        totalSpecialties = 2
        operatingRooms = 4
        days = 1
        anesthetists = 2
        operatingRoomTimes = self.create_room_timetable(operatingRooms, days)
        anesthetistsTimes = self.create_anestethists_timetable(anesthetists, days)
        operatingTimes = self.generate_truncnorm_sample(patients, 30, 120, 60, 20, isTime=True)
        priorities = self.generate_truncnorm_sample(patients, lower=1, upper=120, mean=60, stdDev=10, isTime=False)
        anesthesiaFlags = self.generate_binomial_sample(patients, 0.5, isSpecialty=False)
        covidFlags = self.generate_binomial_sample(patients, 0.3, isSpecialty=False)
        specialtyLabels = self.generate_binomial_sample(patients, 0.4, isSpecialty=True)
        return {None: {
            'I': {None: patients},
            'J': {None: totalSpecialties},
            'K': {None: operatingRooms},
            'T': {None: days},
            'A': {None: anesthetists},
            'M': {None: 5},
            's': operatingRoomTimes,
            'An': anesthetistsTimes,
            'tau': self.create_room_specialty_assignment(totalSpecialties, operatingRooms, days),
            'p': operatingTimes,
            'r': priorities,
            'a': anesthesiaFlags,
            'c': covidFlags,
            'specialty': specialtyLabels,
            'rho': self.create_patient_specialty_table(patients, totalSpecialties, specialtyLabels),
            'bigM': {
                1: patients,
                2: 5000,
                3: patients,
                4: 5000,
                5: patients
            }
        }}
