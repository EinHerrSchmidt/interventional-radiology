from enum import Enum
import math
from matplotlib import scale
from scipy.stats import truncnorm
from scipy.stats import binom
from scipy.stats import uniform
import numpy as np
import planner.sample_data as sd

from planner.model import Patient


class DataDescriptor:
    """Used to define properties of the sample to be generated."""

    def __init__(self):
        self._patients = None
        self._specialties = 2
        self._operatingRooms = 4
        self._days = None
        self._anesthetists = None
        self._covidFrequence = None
        self._anesthesiaFrequence = None
        self._specialtyBalance = None
        self._operatingDayDuration = None
        self._anesthesiaTime = None
        self._delayWeight = None

    @property
    def patients(self):
        """Get number of patients."""
        return self._patients

    @patients.setter
    def patients(self, value):
        self._patients = value

    @property
    def specialties(self):
        """Get number of specialties."""
        return self._specialties

    @property
    def operatingRooms(self):
        """Get number of operating rooms."""
        return self._operatingRooms

    @property
    def days(self):
        """Get number of days in the planning horizon."""
        return self._days

    @days.setter
    def days(self, value):
        self._days = value

    @property
    def anesthetists(self):
        """Get number of anesthetists."""
        return self._anesthetists

    @anesthetists.setter
    def anesthetists(self, value):
        self._anesthetists = value

    @property
    def covidFrequence(self):
        """Get Covid infection frequency."""
        return self._covidFrequence

    @covidFrequence.setter
    def covidFrequence(self, value):
        self._covidFrequence = value

    @property
    def anesthesiaFrequence(self):
        """Get anesthesia need frequency."""
        return self._anesthesiaFrequence

    @anesthesiaFrequence.setter
    def anesthesiaFrequence(self, value):
        self._anesthesiaFrequence = value

    @property
    def specialtyBalance(self):
        """Get specialty balance."""
        return self._specialtyBalance

    @specialtyBalance.setter
    def specialtyBalance(self, value):
        self._specialtyBalance = value

    @property
    def operatingDayDuration(self):
        """Get operating day duration."""
        return self._operatingDayDuration

    @operatingDayDuration.setter
    def operatingDayDuration(self, value):
        self._operatingDayDuration = value

    @property
    def anesthesiaTime(self):
        """Get anesthesia time at disposal for each anesthetist."""
        return self._anesthesiaTime

    @anesthesiaTime.setter
    def anesthesiaTime(self, value):
        self._anesthesiaTime = value

    @property
    def delayWeight(self):
        """Get the delay weight."""
        return self._delayWeight

    @delayWeight.setter
    def delayWeight(self, value):
        self._delayWeight = value

    def initialize(self, patients, days, anesthetists, covidFrequence, anesthesiaFrequence, specialtyBalance):
        self.patients = patients
        self.days = days
        self.anesthetists = anesthetists
        self.covidFrequence = covidFrequence
        self.anesthesiaFrequence = anesthesiaFrequence
        self.specialtyBalance = specialtyBalance

    def __str__(self):
        return f'Patients:{self.patients:17}\nDays:{self.days:21}\nAnesthetists:{self.anesthetists:13}\nCovid frequence:{self.covidFrequence:10}\nAnesthesia frequence:{self.anesthesiaFrequence:5}\nSpecialty balance:{self.specialtyBalance:8}'

class SurgeryType(Enum):
    CLEAN = 1
    DIRTY = 2
    COVID = 3

class DataMaker:
    def __init__(self, seed):
        np.random.seed(seed=seed)
        self.dirtySurgeryMapping = sd.dirtySurgeryMapping
        self.surgeryFrequencyMapping = sd.surgeryFrequencyMapping
        self.UOFrequencyMapping = sd.UOFrequencyMapping
        self.surgeryRoomOccupancyMapping = sd.surgeryRoomOccupancyMapping
        self.delayFrequencyByOperation = sd.delayFrequencyByOperation
        self.delayFrequencyByUO = sd.delayFrequencyByUO
        self.operationGivenUO = sd.operationGivenUO

    def generate_uniform_sample(self, patients, lower, upper):
        uniformDistribution = uniform(loc=lower, scale=upper - lower)
        sample = uniformDistribution.rvs(patients)
        return sample

    def generate_binomial_sample(self, patients, p, isSpecialty):
        sample = binom.rvs(1, p, size=patients)
        if(isSpecialty):
            sample = sample + 1
        return sample

    def create_dictionary_entry(self, sample, toRound):
        dict = {}
        for i in range(0, len(sample)):
            if(toRound):
                dict[(i + 1)] = round(sample[i])
            else:
                dict[(i + 1)] = sample[i]
        return dict

    def create_room_timetable(self, K, T, operatingDayDuration):
        dict = {}
        for k in range(0, K):
            for t in range(0, T):
                dict[(k + 1, t + 1)] = operatingDayDuration
        return dict

    def create_anestethists_timetable(self, A, T, anesthesiaTime):
        dict = {}
        for a in range(0, A):
            for t in range(0, T):
                dict[(a + 1, t + 1)] = anesthesiaTime
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

    def setup_u_parameter(self, precedences):
        dict = {}
        for i1 in range(1, len(precedences) + 1):
            for i2 in range(1, len(precedences) + 1):
                dict[(i1, i2)] = 0
                dict[(i2, i1)] = 0
                if(i1 == i2):
                    continue
                if(precedences[i1 - 1] < precedences[i2 - 1]):
                    dict[(i1, i2)] = 1
                    continue
                if(precedences[i2 - 1] < precedences[i1 - 1]):
                    dict[(i2, i1)] = 1
                    continue
        return dict

    def generate_data(self, dataDescriptor: DataDescriptor):
        return self.create_data_dictionary(dataDescriptor)
        
    def compute_surgery_types(self, surgeryIds, covidFlags):
        surgeryTypes = []
        for i in range(0, len(surgeryIds)):
            if(covidFlags[i] == 1):
                surgeryTypes.append(SurgeryType.COVID)
                continue
            if(self.dirtySurgeryMapping[surgeryIds[i]] == 1):
                surgeryTypes.append(SurgeryType.DIRTY)
                continue
            surgeryTypes.append(SurgeryType.CLEAN)
        return surgeryTypes

    def draw_delay_flags_by_UO(self, UOs):
        draws = uniform.rvs(size=len(UOs))
        delayFlags = []
        for i in range(0, len(draws)):
            if(draws[i] <= self.delayFrequencyByUO[UOs[i]]):
                delayFlags.append(1)
            else:
                delayFlags.append(0)
        return delayFlags

    def draw_delay_flags_by_operation(self, patientSurgeryIds):
        draws = uniform.rvs(size=len(patientSurgeryIds))
        delayFlags = []
        for i in range(0, len(draws)):
            if(draws[i] <= self.delayFrequencyByOperation[patientSurgeryIds[i]]):
                delayFlags.append(1)
            else:
                delayFlags.append(0)
        return delayFlags

    def compute_delay_weights(self, delayFlags, delayWeight):
        delayWeights = []
        for df in delayFlags:
            if(df == 1):
                delayWeights.append(delayWeight)
            else:
                delayWeights.append(1.0)
        return delayWeights

    def compute_precedences(self, surgeryTypes):
        precedences = []
        for i in range(0, len(surgeryTypes)):
            if(surgeryTypes[i] == SurgeryType.CLEAN):
                precedences.append(1)
            if(surgeryTypes[i] == SurgeryType.DIRTY):
                precedences.append(3)
            if(surgeryTypes[i] == SurgeryType.COVID):
                precedences.append(5)
        return precedences

    def draw_UO(self, n):
        UOIds = list(self.UOFrequencyMapping.keys())
        UOIdsFrequencies = list(self.UOFrequencyMapping.values())
        cumulativeSum = np.cumsum(UOIdsFrequencies)
        draws = uniform.rvs(size=n)
        UOs = [""] * n
        for i in range(0, len(draws)):
            for j in range(0, len(cumulativeSum)):
                if(draws[i] <= cumulativeSum[j]):
                    UOs[i] = UOIds[j]
                    break
            if(UOs[i] == ""):
                UOs[i] = UOIds[-1]
        return UOs

    def draw_operations_given_UO(self, UOs):
        n = len(UOs)
        draws = uniform.rvs(size=n)
        operations = []
        for i in range(0, n):
            surgeryIds = list(self.operationGivenUO[UOs[i]].keys())
            surgeryIdsFrequencies = list(self.operationGivenUO[UOs[i]].values())
            cumulativeSum = np.cumsum(surgeryIdsFrequencies)
            times = np.zeros(n) - 1
            for j in range(0, len(cumulativeSum)):
                if(draws[i] <= cumulativeSum[j]):
                    times[i] = self.surgeryRoomOccupancyMapping[surgeryIds[j]]
                    operations.append(surgeryIds[j])
                    break
            if(times[i] == -1):
                times[i] = self.surgeryRoomOccupancyMapping[surgeryIds[-1]]
                operations.append(surgeryIds[-1])
        return operations

    def compute_operating_times(self, operations):
        times = []
        for operation in operations:
            times.append(self.surgeryRoomOccupancyMapping[operation])
        return times

    def create_data_dictionary(self, dataDescriptor: DataDescriptor):
        operatingRoomTimes = self.create_room_timetable(dataDescriptor.operatingRooms, dataDescriptor.days, dataDescriptor.operatingDayDuration)
        anesthetistsTimes = self.create_anestethists_timetable(dataDescriptor.anesthetists, dataDescriptor.days, dataDescriptor.anesthesiaTime)
        UOs = self.draw_UO(dataDescriptor.patients)
        operations = self.draw_operations_given_UO(UOs)
        operatingTimes = operatingTimes = self.compute_operating_times(operations)
        priorities = self.generate_uniform_sample(dataDescriptor.patients, 10, 120)
        anesthesiaFlags = self.generate_binomial_sample(dataDescriptor.patients, dataDescriptor.anesthesiaFrequence, isSpecialty=False)
        covidFlags = self.generate_binomial_sample(dataDescriptor.patients, dataDescriptor.covidFrequence, isSpecialty=False)
        specialties = self.generate_binomial_sample(dataDescriptor.patients, dataDescriptor.specialtyBalance, isSpecialty=True)
        ids = [i for i in range(1, len(operatingTimes) + 1)]
        # for now we assume same duration for each room, on each day
        maxOperatingRoomTime = dataDescriptor.operatingDayDuration
        surgeryTypes = self.compute_surgery_types(operations, covidFlags)

        precedences = self.compute_precedences(surgeryTypes)

        return {
            None: {
                'I': {None: dataDescriptor.patients},
                'J': {None: dataDescriptor.specialties},
                'K': {None: dataDescriptor.operatingRooms},
                'T': {None: dataDescriptor.days},
                'A': {None: dataDescriptor.anesthetists},
                'M': {None: 7},
                's': operatingRoomTimes,
                'An': anesthetistsTimes,
                'tau': self.create_room_specialty_assignment(dataDescriptor.specialties, dataDescriptor.operatingRooms, dataDescriptor.days),
                'p': self.create_dictionary_entry(operatingTimes, toRound=False),
                'r': self.create_dictionary_entry(priorities, toRound=True),
                'a': self.create_dictionary_entry(anesthesiaFlags, toRound=False),
                'c': self.create_dictionary_entry(covidFlags, toRound=False),
                'u': self.setup_u_parameter(precedences),
                'patientId': self.create_dictionary_entry(ids, toRound=False),
                'specialty': self.create_dictionary_entry(specialties, toRound=False),
                'precedence': self.create_dictionary_entry(precedences, toRound=False),
                'bigM': {
                    1: math.floor(maxOperatingRoomTime/min(operatingTimes)),
                    2: maxOperatingRoomTime,
                    3: maxOperatingRoomTime,
                    4: maxOperatingRoomTime,
                    5: maxOperatingRoomTime,
                    6: dataDescriptor.patients
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
            covid = data[None]['c'][(i + 1)]
            anesthesia = data[None]['a'][(i + 1)]
            precedence = data[None]['precedence'][(i + 1)]
            print(Patient(id=id,
                          priority=priority,
                          specialty=specialty,
                          operatingTime=operatingTime,
                          covid=covid,
                          precedence=precedence,
                          delayWeight=None,
                          anesthesia=anesthesia,
                          room="N/A",
                          day="N/A",
                          anesthetist="N/A",
                          order="N/A"
                          ))
        print("\n")
