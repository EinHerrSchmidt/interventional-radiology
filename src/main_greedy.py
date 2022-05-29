import logging
import copy
from numpy import empty
from pyomo.util.infeasible import log_infeasible_constraints
from data_maker import DataDescriptor, DataMaker, TruncatedNormalParameters
from model import Patient
import slow_complete_heuristic as sce
import slow_complete_heuristic_variant as scev
from utils import SolutionVisualizer

if __name__ == '__main__':

    def to_patients(dict):
        solution = copy.deepcopy(dict)
        for k in range(1, dataDictionary[None]["K"][None] + 1):
            for t in range(1, dataDictionary[None]["T"][None] + 1):
                patients = []
                for p in dict[(k, t)]:
                    patients.append(Patient(p[5], p[0], k, p[2], t, p[1], p[6], p[3], p[4], 0))
                patients.sort(key=lambda x: x.order)
                solution[(k, t)] = patients

        # fix order
        for k in range(1, dataDictionary[None]["K"][None] + 1):
            for t in range(1, dataDictionary[None]["T"][None] + 1):
                patients = solution[(k, t)]
                patients.sort(key=lambda x: x.covid)
                for i in range(1, len(patients)):
                    patients[i].order = sum(p.operatingTime for p in patients[:i])
                patients.sort(key=lambda x: x.order)
                solution[(k, t)] = patients

        return solution

    def compute_objective_value(solution):
        value = 0
        for k in range(1, dataDictionary[None]["K"][None] + 1):
            for t in range(1, dataDictionary[None]["T"][None] + 1):
                for p in solution[(k, t)]:
                    value = value + p.priority
        return value

    dataDescriptor = DataDescriptor()

    dataDescriptor.patients = 180
    dataDescriptor.days = 5
    dataDescriptor.anesthetists = 2
    dataDescriptor.covidFrequence = 0.5
    dataDescriptor.anesthesiaFrequence = 1.0
    dataDescriptor.specialtyBalance = 0.17
    dataDescriptor.operatingDayDuration = 270
    dataDescriptor.anesthesiaTime = 270
    dataDescriptor.operatingTimeDistribution = TruncatedNormalParameters(low=30,
                                                                         high=120,
                                                                         mean=60,
                                                                         stdDev=20)
    dataDescriptor.priorityDistribution = TruncatedNormalParameters(low=1,
                                                                    high=120,
                                                                    mean=60,
                                                                    stdDev=10)
    dataMaker = DataMaker(seed=52876)
    dataContainer = dataMaker.create_data_container(dataDescriptor)
    dataDictionary = dataMaker.create_data_dictionary(
        dataContainer, dataDescriptor)

    print("Data description:\n")
    print(dataDescriptor)
    dataMaker.print_data(dataDictionary)

    roomSpecialtyMapping = {1: 1,
                            2: 1,
                            3: 2,
                            4: 2}
    roomAnesthetistPresence = {(1, 1): [],
                               (2, 1): [],
                               (3, 1): [],
                               (4, 1): [],
                               (1, 2): [],
                               (2, 2): [],
                               (3, 2): [],
                               (4, 2): [],
                               (1, 3): [],
                               (2, 3): [],
                               (3, 3): [],
                               (4, 3): [],
                               (1, 4): [],
                               (2, 4): [],
                               (3, 4): [],
                               (4, 4): [],
                               (1, 5): [],
                               (2, 5): [],
                               (3, 5): [],
                               (4, 5): []
                               }

    patients = []
    for i in range(1, dataDictionary[None]["I"][None] + 1):
        patients.append([dataDictionary[None]["r"][i],
                         dataDictionary[None]["p"][i],
                         dataDictionary[None]["specialty"][i],
                         dataDictionary[None]["a"][i],
                         0,  # used to track to what anesthetist the patient is assigned
                         i,
                         dataDictionary[None]["c"][i]])
    # sort patients by r_i/p_i (most bang for the buck)
    patients.sort(key=lambda x: x[0]/x[1])

    dict = {}
    # fill rooms, for each day
    for t in range(1, dataDictionary[None]["T"][None] + 1):
        for k in range(1, dataDictionary[None]["K"][None] + 1):
            selectedPatients = []
            roomCapacity = dataDictionary[None]["s"][(k, t)]
            tmpPatients = patients
            idx = 0
            for patient in tmpPatients:
                if(roomSpecialtyMapping[k] == patient[2] and patient[1] <= roomCapacity):
                    selectedPatients.append(patient)
                    roomCapacity = roomCapacity - patient[1]
                    patients.pop(idx)
                idx = idx + 1
            dict[(k, t)] = selectedPatients

    # assign anesthetists to most rewarding room
    for t in range(1, dataDictionary[None]["T"][None] + 1):
        for a in range(1, dataDictionary[None]["A"][None] + 1):
            maxGain = 0
            bestRoom = 0
            for k in range(1, dataDictionary[None]["K"][None] + 1):
                gain = 0
                anesthetistTime = dataDictionary[None]["An"][(a, t)]
                for patient in dict[(k, t)]:
                    # if patient has operating time lower than anesthetist's residual time AND patient is not yet assigned an anesthetist
                    if(anesthetistTime >= patient[1] and patient[4] == 0):
                        anesthetistTime = anesthetistTime - patient[1]
                        gain = gain + patient[0]
                        patient[4] = a
                if(gain > maxGain):
                    maxGain = gain
                    bestRoom = k
            if(maxGain == 0):
                continue
            roomAnesthetistPresence[(bestRoom, t)].append(a)
            # remove marked patients in rooms which are not bestRoom, for anesthetist a
            for k in range(1, dataDictionary[None]["K"][None] + 1):
                if(k != bestRoom):
                    for patient in dict[(k, t)]:
                        if(patient[4] == a):
                            patient[4] = 0

    solution = to_patients(dict)
    sv = SolutionVisualizer()
    sv.print_solution(solution)
    sv.plot_graph(solution)

    # try to move anesthesia patients to anesthetist's room
    for t in range(1, dataDictionary[None]["T"][None] + 1):
        for k1 in range(1, dataDictionary[None]["K"][None] + 1):
            if(not roomAnesthetistPresence[(k1, t)]):
                k1Patients = dict[(k1, t)]
                for k1Patient in k1Patients:
                    # patient with anesthesia, must check whether she can be swapped, or discard her otherwise
                    if(k1Patient[3] == 1):
                        mustDiscard = True
                        for k2 in range(1, dataDictionary[None]["K"][None] + 1):
                            # room in which patient may be sent (same specialty)
                            if(roomSpecialtyMapping[k2] == k1Patient[2]):
                                for a in roomAnesthetistPresence[(k2, t)]:
                                    anesthetistResidualTime = dataDictionary[None]["An"][(a, t)] - sum(ap[1] for ap in dict[(k2, t)] if ap[4] == a)
                                    k1ResidualTime = dataDictionary[None]["s"][(k1, t)] - sum(p[1] for p in dict[(k1, t)])
                                    k2ResidualTime = dataDictionary[None]["s"][(k2, t)] - sum(p[1] for p in dict[(k2, t)])
                                    k2Patients = dict[(k2, t)]
                                    k2Patients.sort(key=lambda x: x[1]) # sort by operating time
                                    for k2Patient in k2Patients:
                                        # check if we can swap
                                        if(k2Patient[3] == 0 and k2Patient[1] + k2ResidualTime >= k1Patient[1] and k1Patient[1] + k1ResidualTime >= k2Patient[1]
                                            and anesthetistResidualTime >= k1Patient[1]):
                                            dict[(k1, t)].remove(k1Patient)
                                            dict[(k1, t)].append(k2Patient)
                                            k1Patient[4] = a
                                            dict[(k2, t)].remove(k2Patient)
                                            dict[(k2, t)].append(k1Patient)
                                            mustDiscard = False
                                            break
                                    if(not mustDiscard):
                                        break
                            if(mustDiscard):
                                dict[(k1, t)] = [x for x in dict[(k1, t)] if x[5] != k1Patient[5]]
                                fff = 4

    print(dict)

    # add no-anesthesia patient where anesthesia patient were discarded
    for t in range(1, dataDictionary[None]["T"][None] + 1):
        for k in range(1, dataDictionary[None]["K"][None] + 1):
            selectedPatients = dict[(k, t)]
            roomCapacity = dataDictionary[None]["s"][(k, t)] - sum(p[1] for p in selectedPatients)
            tmpPatients = patients
            idx = 0
            for patient in tmpPatients:
                if(patient[3] == 0 and roomSpecialtyMapping[k] == patient[2] and patient[1] <= roomCapacity):
                    selectedPatients.append(patient)
                    roomCapacity = roomCapacity - patient[1]
                    patients.pop(idx)
                idx = idx + 1
            dict[(k, t)] = selectedPatients

    solution = to_patients(dict)

    sv = SolutionVisualizer()
    sv.print_solution(solution)
    sv.plot_graph(solution)

    print("Objective function value: " + str(compute_objective_value(solution)))
