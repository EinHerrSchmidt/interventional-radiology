from enum import Enum
import math
from scipy.stats import binom
from scipy.stats import uniform
import numpy as np
import planner.sample_data as sd

from planner.model import Patient


class DataDescriptor:
    """Used to define properties of the sample to be generated."""

    def __init__(self, patients, specialties=2, specialty_frequency=[0.83, 0.17], operating_rooms=4, days=5, anesthetists=2, infection_frequency=0.5, anesthesia_frequency=0.5, robustness_parameter=3):
        self.patients = patients
        self.specialties = [i for i in range(1, specialties + 1)]
        self.operating_rooms = operating_rooms
        self.days = days
        self.anesthetists = anesthetists
        self.infection_frequency = infection_frequency
        self.anesthesia_frequency = anesthesia_frequency
        self.specialty_frequency = specialty_frequency
        self.robustness_parameter = robustness_parameter

        self.operating_day_duration_table = sd.operating_day_duration_table
        self.anesthesia_time_table = sd.anesthesia_time_table
        self.robustness_table = sd.robustness_table
        self.operating_room_specialty_table = sd.operating_room_specialty_table

        self.dirty_surgery_mapping = sd.dirty_surgery_mapping
        self.ward_frequency_mapping = sd.ward_frequency_mapping
        self.surgery_room_occupancy_mapping = sd.surgery_room_occupancy_mapping
        self.ward_arrival_delay_mapping = sd.ward_arrival_delay_mapping
        self.surgery_frequency_given_ward_mapping = sd.surgery_frequency_given_ward_mapping


class SurgeryType(Enum):
    CLEAN = 1
    DIRTY = 2
    COVID = 3


class DataMaker:
    def __init__(self, seed, data_descriptor: DataDescriptor):
        np.random.seed(seed=seed)
        self.data_descriptor = data_descriptor

        self.origin_wards = self.draw_origin_wards()
        self.operations = self.draw_operations_given_origin_ward()
        self.operating_times = self.compute_operating_times()
        self.priorities = self.generate_priorities()
        self.anesthesia_flags = self.generate_anesthesia_flags()
        self.infection_flags = self.generate_infection_flags()
        self.specialties = self.draw_specialties()
        self.surgery_types = self.compute_patients_surgery_types()
        self.precedences = self.compute_precedences()
        self.arrival_delays = self.compute_arrival_delays()

    def generate_uniform_sample(self, patients, lower, upper):
        uniformDistribution = uniform(loc=lower, scale=upper - lower)
        sample = uniformDistribution.rvs(patients)
        return sample

    def generate_binomial_sample(self, patients, p, isSpecialty):
        sample = binom.rvs(1, p, size=patients)
        if(isSpecialty):
            sample = sample + 1
        return sample

    def create_dictionary_entry(self, sample):
        dict = {}
        for i in range(0, len(sample)):
            dict[(i + 1)] = sample[i]
        return dict

    def generate_u_parameter(self):
        dict = {}
        for i1 in range(1, len(self.precedences) + 1):
            for i2 in range(1, len(self.precedences) + 1):
                dict[(i1, i2)] = 0
                dict[(i2, i1)] = 0
                if(i1 == i2):
                    continue
                if(self.precedences[i1 - 1] < self.precedences[i2 - 1]):
                    dict[(i1, i2)] = 1
                    continue
                if(self.precedences[i2 - 1] < self.precedences[i1 - 1]):
                    dict[(i2, i1)] = 1
                    continue
        return dict

    def generate_data(self, data_descriptor: DataDescriptor):
        return self.create_data_dictionary(data_descriptor)

    def compute_patients_surgery_types(self):
        surgery_types = []
        for i in range(0, self.data_descriptor.patients):
            if(self.infection_flags[(i)] == 1):
                surgery_types.append(SurgeryType.COVID)
                continue
            if(self.data_descriptor.dirty_surgery_mapping[self.operations[(i)]] == 1):
                surgery_types.append(SurgeryType.DIRTY)
                continue
            surgery_types.append(SurgeryType.CLEAN)
        return surgery_types

    def compute_precedences(self):
        precedences = []
        for i in range(0, self.data_descriptor.patients):
            if(self.surgery_types[i] == SurgeryType.CLEAN):
                precedences.append(1)
            if(self.surgery_types[i] == SurgeryType.DIRTY):
                precedences.append(3)
            if(self.surgery_types[i] == SurgeryType.COVID):
                precedences.append(5)
        return precedences

    def draw_origin_wards(self):
        origin_ward_ids = list(
            self.data_descriptor.ward_frequency_mapping.keys())
        origin_ward_ids_frequencies = list(
            self.data_descriptor.ward_frequency_mapping.values())
        cumulativeSum = np.cumsum(origin_ward_ids_frequencies)
        draws = uniform.rvs(size=self.data_descriptor.patients)
        origin_wards = [""] * self.data_descriptor.patients
        for i in range(0, len(draws)):
            for j in range(0, len(cumulativeSum)):
                if(draws[i] <= cumulativeSum[j]):
                    origin_wards[i] = origin_ward_ids[j]
                    break
            if(origin_wards[i] == ""):
                origin_wards[i] = origin_ward_ids[-1]
        return origin_wards

    def draw_operations_given_origin_ward(self):
        n = len(self.origin_wards)
        draws = uniform.rvs(size=n)
        operations = []
        for i in range(0, n):
            surgery_ids = list(self.data_descriptor.surgery_frequency_given_ward_mapping[self.origin_wards[i]].keys())
            surgeryIdsFrequencies = list(self.data_descriptor.surgery_frequency_given_ward_mapping[self.origin_wards[i]].values())
            cumulativeSum = np.cumsum(surgeryIdsFrequencies)
            times = np.zeros(n) - 1
            for j in range(0, len(cumulativeSum)):
                if(draws[i] <= cumulativeSum[j]):
                    times[i] = self.data_descriptor.surgery_room_occupancy_mapping[surgery_ids[j]]
                    operations.append(surgery_ids[j])
                    break
            if(times[i] == -1):
                times[i] = self.data_descriptor.surgery_room_occupancy_mapping[surgery_ids[-1]]
                operations.append(surgery_ids[-1])
        return operations

    def compute_operating_times(self):
        times = []
        for operation in self.operations:
            times.append(
                self.data_descriptor.surgery_room_occupancy_mapping[operation])
        return times

    def compute_arrival_delays(self):
        times = []
        for ward in self.origin_wards:
            times.append(
                self.data_descriptor.ward_arrival_delay_mapping[ward])
        return times

    def create_delay_table(self):
        dict = {}
        i = 0
        for ward in self.origin_wards:
            dict[(1, i + 1)] = self.data_descriptor.ward_arrival_delay_mapping[ward]
            i += 1
        return dict

    def generate_priorities(self):
        return self.generate_uniform_sample(self.data_descriptor.patients, 10, 120)

    def generate_anesthesia_flags(self):
        return self.generate_binomial_sample(self.data_descriptor.patients,
                                             self.data_descriptor.anesthesia_frequency,
                                             isSpecialty=False)

    def generate_infection_flags(self):
        return self.generate_binomial_sample(self.data_descriptor.patients,
                                             self.data_descriptor.infection_frequency,
                                             isSpecialty=False)

    def draw_specialties(self):
        specialty_frequency_cumulative_sum = np.cumsum(
            self.data_descriptor.specialty_frequency)
        draws = uniform.rvs(size=self.data_descriptor.patients)
        specialties = [""] * self.data_descriptor.patients
        for i in range(0, len(draws)):
            for j in range(0, len(specialty_frequency_cumulative_sum)):
                if(draws[i] <= specialty_frequency_cumulative_sum[j]):
                    specialties[i] = self.data_descriptor.specialties[j]
                    break
            if(specialties[i] == ""):
                specialties[i] = self.data_descriptor.specialties[-1]
        return specialties

    def generate_tau_parameters(self):
        specialty_table = self.data_descriptor.operating_room_specialty_table
        tau = {}
        for j in range(1, len(self.data_descriptor.specialties) + 1):
            for k in range(1, self.data_descriptor.operating_rooms + 1):
                for t in range(1, self.data_descriptor.days + 1):
                    if specialty_table[(k, t)] == j:
                        tau[(j, k, t)] = 1
                    else:
                        tau[(j, k, t)] = 0
        return tau

    def generate_anesthetists_availability(self):
        availability = {}
        for alpha in range(1, self.data_descriptor.anesthetists + 1):
            for t in range(1, self.data_descriptor.days + 1):
                availability[(alpha, t)] = 270 # assume fixed for now
        return availability

    # assumes same robustness parameter Gamma is used in each (k, t) slot
    # and a single delay type is possible (index q = 1)
    def generate_robustness_table(self):
        robustness_table = {}
        for k in range(1, self.data_descriptor.operating_rooms + 1):
            for t in range(1, self.data_descriptor.days + 1):
                robustness_table[(1, k, t)] = self.data_descriptor.robustness_parameter

        return robustness_table

    def create_data_dictionary(self):
        # for now we assume same duration for each room, on each day
        maxOperatingRoomTime = 270
        return {
            None: {
                'I': {None: self.data_descriptor.patients},
                'J': {None: len(self.data_descriptor.specialties)},
                'K': {None: self.data_descriptor.operating_rooms},
                'T': {None: self.data_descriptor.days},
                'A': {None: self.data_descriptor.anesthetists},
                'M': {None: 7},
                'Q': {None: 1},
                's': self.data_descriptor.operating_day_duration_table,
                'An': self.generate_anesthetists_availability(),
                'Gamma': self.generate_robustness_table(),
                'tau': self.generate_tau_parameters(),
                'p': self.create_dictionary_entry(self.operating_times),
                'd': self.create_delay_table(),
                'r': self.create_dictionary_entry(self.priorities),
                'a': self.create_dictionary_entry(self.anesthesia_flags),
                'c': self.create_dictionary_entry(self.infection_flags),
                'u': self.generate_u_parameter(),
                'patientId': self.create_dictionary_entry([i for i in range(1, self.data_descriptor.patients + 1)]),
                'specialty': self.create_dictionary_entry(self.specialties),
                'precedence': self.create_dictionary_entry(self.precedences),
                'bigM': {
                    1: math.floor(maxOperatingRoomTime/min(self.operating_times)),
                    2: maxOperatingRoomTime
                }
            }
        }

    def print_data(self, data):
        patientNumber = data[None]['I'][None]
        for i in range(0, patientNumber):
            id = i + 1
            priority = data[None]['r'][(i + 1)]
            specialty = data[None]['specialty'][(i + 1)]
            operatingTime = data[None]['p'][(i + 1)]
            arrival_delay = data[None]['d'][(1, i + 1)]
            covid = data[None]['c'][(i + 1)]
            anesthesia = data[None]['a'][(i + 1)]
            precedence = data[None]['precedence'][(i + 1)]
            print(Patient(id=id,
                          priority=priority,
                          specialty=specialty,
                          operatingTime=operatingTime,
                          arrival_delay=arrival_delay,
                          covid=covid,
                          precedence=precedence,
                          delayWeight=None,
                          anesthesia=anesthesia,
                          room="N/A",
                          day="N/A",
                          anesthetist="N/A",
                          order="N/A",
                          delay="N/A"
                          ))
        print("\n")
