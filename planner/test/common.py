import unittest
from data_maker import DataDescriptor, DataMaker


def build_data_dictionary():
    dataDescriptor = DataDescriptor()
    dataDescriptor.patients = 60
    dataDescriptor.days = 5
    dataDescriptor.anesthetists = 2
    dataDescriptor.covidFrequence = 0.5
    dataDescriptor.anesthesiaFrequence = 0.2
    dataDescriptor.specialtyBalance = 0.17
    dataDescriptor.operatingDayDuration = 270
    dataDescriptor.anesthesiaTime = 270
    dataDescriptor.delayWeight = 0.75

    dataMaker = DataMaker(seed=52876)
    return dataMaker.create_data_dictionary(dataDescriptor)


class TestCommon(unittest.TestCase):

    def non_empty_solution(self):
        operated = 0
        K = self.dataDictionary[None]["K"][None]
        T = self.dataDictionary[None]["T"][None]
        for k in range(1, K + 1):
            for t in range(1, T + 1):
                operated = operated + len(self.solution[(k, t)])
        self.assertTrue(operated > 0)

    def non_overlapping_patients(self):
        K = self.dataDictionary[None]["K"][None]
        T = self.dataDictionary[None]["T"][None]
        for k in range(1, K + 1):
            for t in range(1, T + 1):
                patients = self.solution[(k, t)]
                patientsNumber = len(patients)
                if(patientsNumber == 0):
                    continue
                for i1 in range(0, patientsNumber):
                    for i2 in range(0, patientsNumber):
                        if(i1 != i2):
                            self.assertTrue((patients[i1].order + patients[i1].operatingTime <= patients[i2].order or patients[i2].order + patients[i2].operatingTime <= patients[i1].order)
                                            and not (patients[i1].order + patients[i1].operatingTime <= patients[i2].order and patients[i2].order + patients[i2].operatingTime <= patients[i1].order))

    def non_overlapping_anesthetists(self):
        K = self.dataDictionary[None]["K"][None]
        T = self.dataDictionary[None]["T"][None]
        for t in range(1, T + 1):
            for k1 in range(1, K + 1):
                for k2 in range(1, K + 1):
                    if(k1 == k2):
                        continue
                    k1Patients = self.solution[(k1, t)]
                    k1PatientsNumber = len(k1Patients)
                    k2Patients = self.solution[(k2, t)]
                    k2PatientsNumber = len(k2Patients)
                    if(k1PatientsNumber == 0 or k2PatientsNumber == 0):
                        continue
                    for i1 in range(0, k1PatientsNumber):
                        for i2 in range(0, k2PatientsNumber):
                            if(k1Patients[i1].anesthetist and k2Patients[i2].anesthetist and k1Patients[i1].anesthetist == k2Patients[i2].anesthetist):
                                self.assertTrue((k1Patients[i1].order + k1Patients[i1].operatingTime <= k2Patients[i2].order or k2Patients[i2].order + k2Patients[i2].operatingTime <= k1Patients[i1].order)
                                 and not (k1Patients[i1].order + k1Patients[i1].operatingTime <= k2Patients[i2].order and k2Patients[i2].order + k2Patients[i2].operatingTime <= k1Patients[i1].order))

    def priority_constraints(self):
        K = self.dataDictionary[None]["K"][None]
        T = self.dataDictionary[None]["T"][None]
        sorted = True
        for k in range(1, K + 1):
            for t in range(1, T + 1):
                patients = self.solution[(k, t)]
                patientsNumber = len(patients)
                if(patientsNumber <= 1):
                    continue
                for i in range(1, patientsNumber):
                    if(patients[i].covid < patients[i - 1].covid):
                        sorted = False
        self.assertTrue(sorted)

    def surgery_time_constraint(self):
        K = self.dataDictionary[None]["K"][None]
        T = self.dataDictionary[None]["T"][None]
        for k in range(1, K + 1):
            for t in range(1, T + 1):
                patients = self.solution[(k, t)]
                patientsNumber = len(patients)
                if(patientsNumber == 0):
                    continue
                totalOperatingTime = sum(map(lambda p: p.operatingTime, patients))
                self.assertTrue(totalOperatingTime <= self.dataDictionary[None]["s"][(k, t)])

    def end_of_day_constraint(self):
        K = self.dataDictionary[None]["K"][None]
        T = self.dataDictionary[None]["T"][None]
        for k in range(1, K + 1):
            for t in range(1, T + 1):
                patients = self.solution[(k, t)]
                patientsNumber = len(patients)
                if(patientsNumber == 0):
                    continue
                for i in range(0, patientsNumber):
                    self.assertTrue(patients[i].order + patients[i].operatingTime <= self.dataDictionary[None]["s"][(k, t)])

    def anesthesia_total_time_constraint(self):
        K = self.dataDictionary[None]["K"][None]
        T = self.dataDictionary[None]["T"][None]
        A = self.dataDictionary[None]["A"][None]
        for t in range(1, T + 1):
            patients = []
            for k in range(1, K + 1):
                patients.extend(self.solution[(k, t)])
            for a in range(1, A + 1):
                patientsWithAnesthetist = list(
                    filter(lambda p: p.anesthetist and p.anesthetist == a, patients))
                if(len(patientsWithAnesthetist) == 0):
                    continue
                self.assertTrue(sum(map(lambda p: p.operatingTime, patientsWithAnesthetist)) <= self.dataDictionary[None]["An"][(a, t)])

    def single_surgery(self):
        K = self.dataDictionary[None]["K"][None]
        T = self.dataDictionary[None]["T"][None]
        patients = []
        for k in range(1, K + 1):
            for t in range(1, T + 1):
                patients.extend(self.solution[(k, t)])
        patientIds = list(map(lambda p : p.id, patients))
        self.assertTrue(len(patientIds) == len(set(patientIds)))

    def anesthetist_assignment(self):
        K = self.dataDictionary[None]["K"][None]
        T = self.dataDictionary[None]["T"][None]
        for k in range(1, K + 1):
            for t in range(1, T + 1):
                for patient in self.solution[(k, t)]:
                    if(patient.anesthesia == 1):
                        self.assertTrue(patient.anesthetist > 0)
                    else:
                        self.assertTrue(patient.anesthetist == 0)