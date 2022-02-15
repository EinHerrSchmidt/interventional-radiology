from venv import create
from scipy.stats import truncnorm


class DataMaker:
    def __init__(self):
        pass

    def generate_truncnorm_surgery_times(self, patients):
        lower, upper = 30, 120
        mean, stdDev = 60, 20
        truncatedNormal = truncnorm((lower - mean) / stdDev, (upper - mean) / stdDev,
                                    loc=mean,
                                    scale=stdDev)
        sample = truncatedNormal.rvs(patients)
        return self.create_dictionary_entry(sample, True)

    def generate_truncnorm_urgency_coefficients(self, patients):
        lower, upper = 1, 10
        mean, stdDev = 5, 3
        truncatedNormal = truncnorm((lower - mean) / stdDev, (upper - mean) / stdDev,
                                    loc=mean,
                                    scale=stdDev)
        sample = truncatedNormal.rvs(patients)
        return self.create_dictionary_entry(sample, False)

    def generate_truncnorm_distance_coefficients(self, patients):
        lower, upper = 1, 6
        mean, stdDev = 2, 3
        truncatedNormal = truncnorm((lower - mean) / stdDev, (upper - mean) / stdDev,
                                    loc=mean,
                                    scale=stdDev)
        sample = truncatedNormal.rvs(patients)
        return self.create_dictionary_entry(sample, False)

    def create_dictionary_entry(self, sample, isTime):
        dict = {}
        for i in range(0, len(sample)):
            if(isTime):
                dict[(i + 1)] = int(sample[i]) - int(sample[i]) % 10
            else:
                dict[(i + 1)] = int(sample[i])
        return dict

    def make_example_data(self):
        patients = 150
        return {None: {
            'I': {None: patients},
            'K': {None: 2},
            'T': {None: 5},
            's': {
                (1, 1): 480, # 480 minutes, 8 hours availability
                (1, 2): 120,
                (1, 3): 360,
                (1, 4): 480,
                (1, 5): 120,
                (2, 1): 480,
                (2, 2): 360,
                (2, 3): 120,
                (2, 4): 480,
                (2, 5): 360,
            },
            'p': self.generate_truncnorm_surgery_times(patients),
            'r': self.generate_truncnorm_urgency_coefficients(patients),
            'd': self.generate_truncnorm_distance_coefficients(patients)
        }}
