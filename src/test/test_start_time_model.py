import unittest

from numpy import size
from data_maker import DataDescriptor, DataMaker, TruncatedNormalParameters

from planner import ModelType, Planner


class TestStartTimeModel(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        planner = Planner(timeLimit=900,
                               modelType=ModelType.START_TIME_ORDERING,
                               solver="cplex")

        self.dataDescriptor = DataDescriptor()
        self.dataDescriptor.patients = 100
        self.dataDescriptor.days = 5
        self.dataDescriptor.anesthetists = 2
        self.dataDescriptor.covidFrequence = 0.5
        self.dataDescriptor.anesthesiaFrequence = 0.2
        self.dataDescriptor.specialtyBalance = 0.17
        self.dataDescriptor.operatingDayDuration = 480
        self.dataDescriptor.anesthesiaTime = 480
        self.dataDescriptor.operatingTimeDistribution = TruncatedNormalParameters(low=30,
                                                                                  high=120,
                                                                                  mean=60,
                                                                                  stdDev=20)
        self.dataDescriptor.priorityDistribution = TruncatedNormalParameters(low=1,
                                                                             high=120,
                                                                             mean=60,
                                                                             stdDev=10)
        dataMaker = DataMaker()
        data = dataMaker.generate_data(self.dataDescriptor, seed=52876)
        planner.solve_model(data)
        self.solution = planner.extract_solution()

    def test_non_overlapping_patients(self):
        K = self.dataDescriptor.operatingRooms
        T = self.dataDescriptor.days
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

    def test_non_overlapping_anesthetists(self):
        K = self.dataDescriptor.operatingRooms
        T = self.dataDescriptor.days
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

    def test_surgery_time_constraint(self):
        K = self.dataDescriptor.operatingRooms
        T = self.dataDescriptor.days
        for k in range(1, K + 1):
            for t in range(1, T + 1):
                patients = self.solution[(k, t)]
                patientsNumber = len(patients)
                if(patientsNumber == 0):
                    continue
                totalOperatingTime = sum(
                    map(lambda p: p.operatingTime, patients))
                self.assertTrue(totalOperatingTime <= self.dataDescriptor.operatingDayDuration)

    def test_end_of_day_constraint(self):
        K = self.dataDescriptor.operatingRooms
        T = self.dataDescriptor.days
        for k in range(1, K + 1):
            for t in range(1, T + 1):
                patients = self.solution[(k, t)]
                patientsNumber = len(patients)
                if(patientsNumber == 0):
                    continue
                for i in range(0, patientsNumber):
                    self.assertTrue(patients[i].order + patients[i].operatingTime <= self.dataDescriptor.operatingDayDuration)

    def test_anesthesia_total_time_constraint(self):
        K = self.dataDescriptor.operatingRooms
        T = self.dataDescriptor.days
        A = self.dataDescriptor.anesthetists
        for t in range(1, T + 1):
            patients = []
            for k in range(1, K + 1):
                patients.append(self.solution[(k, t)])
            patients = [p for subList in patients for p in subList]
            for a in range(1, A + 1):
                patientsWithAnesthetist = list(
                    filter(lambda p: p.anesthetist and p.anesthetist == a, patients))
                if(len(patientsWithAnesthetist) == 0):
                    continue
                self.assertTrue(sum(map(lambda p: p.operatingTime, patientsWithAnesthetist)) <= self.dataDescriptor.anesthesiaTime)

    def test_single_surgery(self):
        K = self.dataDescriptor.operatingRooms
        T = self.dataDescriptor.days
        patients = []
        for k in range(1, K + 1):
            for t in range(1, T + 1):
                patients.append(self.solution[(k, t)])
        patients = [p for subList in patients for p in subList]
        patientIds = list(map(lambda p : p.id, patients))
        self.assertTrue(len(patientIds) == len(set(patientIds)))

    def test_anesthetist_assignment(self):
        K = self.dataDescriptor.operatingRooms
        T = self.dataDescriptor.days
        for k in range(1, K + 1):
            for t in range(1, T + 1):
                for patient in self.solution[(k, t)]:
                    if(patient.anesthesia == 1):
                        self.assertTrue(patient.anesthetist > 0)
                    else:
                        self.assertTrue(patient.anesthetist == 0)

if __name__ == '__main__':
    unittest.main()
