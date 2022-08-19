from bisect import bisect
import copy
from enum import unique
from re import I
from select import select
from turtle import update
from model import Patient


class Planner:

    def __init__(self, packingStrategy, anesthetistAssignmentStrategy):
        self.solution = {}
        self.packingStrategy = packingStrategy
        self.anesthetistAssignmentStrategy = anesthetistAssignmentStrategy


    def create_room_specialty_map(self):
        self.roomSpecialtyMapping = {}
        for k in range(1, self.dataDictionary[None]["K"][None] + 1):
            if(k == 1 or k == 2):
                self.roomSpecialtyMapping[k] = 1
            else:
                self.roomSpecialtyMapping[k] = 2

    def create_room_anesthetist_map(self):
        self.roomAnesthetistPresence = {}
        for k in range(1, self.dataDictionary[None]["K"][None] + 1):
            for t in range(1, self.dataDictionary[None]["T"][None] + 1):
                self.roomAnesthetistPresence[(k, t)] = []

    def create_patients_list(self):
        self.patients = []
        for i in range(1, self.dataDictionary[None]["I"][None] + 1):
            self.patients.append(Patient(id=i,
                                         priority=self.dataDictionary[None]["r"][i],
                                         room=0,
                                         specialty=self.dataDictionary[None]["specialty"][i],
                                         day=0,
                                         operatingTime=self.dataDictionary[None]["p"][i],
                                         covid=self.dataDictionary[None]["c"][i],
                                         precedence=self.dataDictionary[None]["precedence"][i],
                                         delayWeight=self.dataDictionary[None]["d"][i],
                                         anesthesia=self.dataDictionary[None]["a"][i],
                                         anesthetist=0,
                                         order=0)
                                 )
        # sort patients by r_i * d_i / p_i (non-decreasing order): get the most bang for your buck, while considering delay weight
        self.patients.sort(key=lambda x: x.priority * x.delayWeight / x.operatingTime, reverse=True)

    # fill rooms, for each day
    def fill_rooms(self):
        tmpPatients = []
        for t in range(1, self.dataDictionary[None]["T"][None] + 1):
            for k in range(1, self.dataDictionary[None]["K"][None] + 1):
                self.solution[(k, t)] = []
                roomCapacity = self.dataDictionary[None]["s"][(k, t)]
                for patient in self.patients:
                    if(self.roomSpecialtyMapping[k] == patient.specialty and patient.operatingTime <= roomCapacity):
                        self.solution[(k, t)].append(patient)
                        roomCapacity = roomCapacity - patient.operatingTime
                        tmpPatients.append(patient.id)
                self.patients = [p for p in self.patients if p.id not in tmpPatients]

    def fill_rooms_first_fit(self):
        roomCapacities = copy.deepcopy(self.dataDictionary[None]["s"])
        for t in range(1, self.dataDictionary[None]["T"][None] + 1):
            for k in range(1, self.dataDictionary[None]["K"][None] + 1):
                self.solution[(k, t)] = []

        tmpPatients = []
        for patient in self.patients:
            assigned = False
            for t in range(1, self.dataDictionary[None]["T"][None] + 1):
                for k in range(1, self.dataDictionary[None]["K"][None] + 1):
                    if(self.roomSpecialtyMapping[k] == patient.specialty and patient.operatingTime <= roomCapacities[(k, t)]):
                        self.solution[(k, t)].append(patient)
                        roomCapacities[(k, t)] = roomCapacities[(k, t)] - patient.operatingTime
                        assigned = True
                    if(assigned):
                        break
                if(assigned):
                    break
            if(not assigned):
                tmpPatients.append(patient)
        self.patients = tmpPatients

    def fill_rooms_best_fit(self):
        roomCapacities = copy.deepcopy(self.dataDictionary[None]["s"])
        for t in range(1, self.dataDictionary[None]["T"][None] + 1):
            for k in range(1, self.dataDictionary[None]["K"][None] + 1):
                self.solution[(k, t)] = []

        tmpPatients = []
        for patient in self.patients:
            bestSlot = (0,0)
            minimumResidual = 99999999
            for t in range(1, self.dataDictionary[None]["T"][None] + 1):
                for k in range(1, self.dataDictionary[None]["K"][None] + 1):
                    if(self.roomSpecialtyMapping[k] == patient.specialty and patient.operatingTime <= roomCapacities[(k, t)] and roomCapacities[(k, t)] - patient.operatingTime < minimumResidual):
                        minimumResidual = roomCapacities[(k, t)] - patient.operatingTime
                        bestSlot = (k, t)
            if(bestSlot != (0, 0)):
                self.solution[bestSlot].append(patient)
                roomCapacities[bestSlot] = minimumResidual
            else:
                tmpPatients.append(patient)
        self.patients = tmpPatients

    # assign anesthetists to most rewarding room
    def assign_anesthetists(self):
        for t in range(1, self.dataDictionary[None]["T"][None] + 1):
            for a in range(1, self.dataDictionary[None]["A"][None] + 1):
                maxGain = 0
                bestRoom = 0
                for k in range(1, self.dataDictionary[None]["K"][None] + 1):
                    gain = 0
                    anesthetistTime = self.dataDictionary[None]["An"][(a, t)]
                    for patient in self.solution[(k, t)]:
                        # if patient has operating time lower than anesthetist's residual time AND patient is not yet assigned an anesthetist AND patient needs anesthesia
                        if(anesthetistTime >= patient.operatingTime and patient.anesthetist == 0 and patient.anesthesia == 1):
                            anesthetistTime = anesthetistTime - patient.operatingTime
                            gain = gain + patient.priority
                            patient.anesthetist = a
                    if(gain > maxGain):
                        maxGain = gain
                        bestRoom = k
                if(maxGain == 0):
                    continue
                self.roomAnesthetistPresence[(bestRoom, t)].append(a)
                # unmark patients in rooms which are not bestRoom, for anesthetist a
                for k in range(1, self.dataDictionary[None]["K"][None] + 1):
                    if(k != bestRoom):
                        for patient in self.solution[(k, t)]:
                            if(patient.anesthetist == a):
                                patient.anesthetist = 0

    # try to move discarded anesthesia patients to a room with anesthetist
    def swap_anesthesia_patients(self):
        for t in range(1, self.dataDictionary[None]["T"][None] + 1):
            for k1 in range(1, self.dataDictionary[None]["K"][None] + 1):
                if(not self.roomAnesthetistPresence[(k1, t)]):
                    k1Patients = self.solution[(k1, t)]
                    for k1Patient in k1Patients:
                        # patient with anesthesia, must check whether she can be swapped, or discard her otherwise
                        if(k1Patient.anesthesia == 1):
                            mustDiscard = True
                            for k2 in range(1, self.dataDictionary[None]["K"][None] + 1):
                                # room in which patient may be sent (same specialty)
                                if(self.roomSpecialtyMapping[k2] == k1Patient.specialty):
                                    for a in self.roomAnesthetistPresence[(k2, t)]:
                                        anesthetistResidualTime = self.dataDictionary[None]["An"][(a, t)] - sum(ap.operatingTime for ap in self.solution[(k2, t)] if ap.anesthetist == a)
                                        k1ResidualTime = self.dataDictionary[None]["s"][(k1, t)] - sum(p.operatingTime for p in self.solution[(k1, t)])
                                        k2ResidualTime = self.dataDictionary[None]["s"][(k2, t)] - sum(p.operatingTime for p in self.solution[(k2, t)])
                                        k2Patients = self.solution[(k2, t)]
                                        # sort: try to swap with the patient with shortest operating time
                                        k2Patients.sort(key=lambda x: x.operatingTime)
                                        for k2Patient in k2Patients:
                                            # check if we can swap
                                            if(k2Patient.anesthesia == 0 
                                                and k2Patient.operatingTime + k2ResidualTime >= k1Patient.operatingTime
                                                and k1Patient.operatingTime + k1ResidualTime >= k2Patient.operatingTime
                                                and anesthetistResidualTime >= k1Patient.operatingTime):
                                                self.solution[(k1, t)] = [x for x in self.solution[(k1, t)] if x.id != k1Patient.id]
                                                self.solution[(k1, t)].append(k2Patient)
                                                k1Patient.anesthetist = a
                                                self.solution[(k2, t)] = [x for x in self.solution[(k2, t)] if x.id != k2Patient.id]
                                                self.solution[(k2, t)].append(k1Patient)
                                                mustDiscard = False
                                                break
                                        if(not mustDiscard):
                                            break
                            if(mustDiscard):
                                self.solution[(k1, t)] = [x for x in self.solution[(k1, t)] if x.id != k1Patient.id]

    # add no-anesthesia patient where anesthesia patient were discarded
    def fill_discarded_slots(self):
        for t in range(1, self.dataDictionary[None]["T"][None] + 1):
            for k in range(1, self.dataDictionary[None]["K"][None] + 1):
                roomCapacity = self.dataDictionary[None]["s"][(k, t)] - sum(p.operatingTime for p in self.solution[(k, t)])
                tmpPatients = []
                for patient in self.patients:
                    if(patient.anesthesia == 0 and self.roomSpecialtyMapping[k] == patient.specialty and patient.operatingTime <= roomCapacity):
                        self.solution[(k, t)].append(patient)
                        roomCapacity = roomCapacity - patient.operatingTime
                    else:
                        tmpPatients.append(patient)
                self.patients = tmpPatients

    def fill_discarded_slots_first_fit(self):
        roomCapacities = copy.deepcopy(self.dataDictionary[None]["s"])
        for t in range(1, self.dataDictionary[None]["T"][None] + 1):
            for k in range(1, self.dataDictionary[None]["K"][None] + 1):
                roomCapacities[(k, t)] = self.dataDictionary[None]["s"][(k, t)] - sum(p.operatingTime for p in self.solution[(k, t)])

        tmpPatients = []
        for patient in self.patients:
            assigned = False
            for t in range(1, self.dataDictionary[None]["T"][None] + 1):
                for k in range(1, self.dataDictionary[None]["K"][None] + 1):
                    if(patient.anesthesia == 0 and self.roomSpecialtyMapping[k] == patient.specialty and patient.operatingTime <= roomCapacities[(k, t)]):
                        self.solution[(k, t)].append(patient)
                        roomCapacities[(k, t)] = roomCapacities[(k, t)] - patient.operatingTime
                        assigned = True
                    if(assigned):
                        break
                if(assigned):
                    break
            if(not assigned):
                tmpPatients.append(patient)
        self.patients = tmpPatients

    def fill_discarded_slots_best_fit(self):
        roomCapacities = copy.deepcopy(self.dataDictionary[None]["s"])
        for t in range(1, self.dataDictionary[None]["T"][None] + 1):
            for k in range(1, self.dataDictionary[None]["K"][None] + 1):
                roomCapacities[(k, t)] = self.dataDictionary[None]["s"][(k, t)] - sum(p.operatingTime for p in self.solution[(k, t)])

        tmpPatients = []
        for patient in self.patients:
            bestSlot = (0,0)
            minimumResidual = 99999999
            for t in range(1, self.dataDictionary[None]["T"][None] + 1):
                for k in range(1, self.dataDictionary[None]["K"][None] + 1):
                    if(self.roomSpecialtyMapping[k] == patient.specialty and patient.operatingTime <= roomCapacities[(k, t)] and roomCapacities[(k, t)] - patient.operatingTime < minimumResidual):
                        minimumResidual = roomCapacities[(k, t)] - patient.operatingTime
                        bestSlot = (k, t)
            if(bestSlot != (0, 0)):
                self.solution[bestSlot].append(patient)
                roomCapacities[bestSlot] = roomCapacities[bestSlot] - patient.operatingTime
            else:
                tmpPatients.append(patient)
        self.patients = tmpPatients

    # fix order
    def compute_patients_order(self):
        for k in range(1, self.dataDictionary[None]["K"][None] + 1):
            for t in range(1, self.dataDictionary[None]["T"][None] + 1):
                patients = self.solution[(k, t)]
                patients.sort(key=lambda x: x.precedence)
                for i in range(1, len(patients)):
                    patients[i].order = sum(p.operatingTime for p in patients[:i])
                patients.sort(key=lambda x: x.order)
                self.solution[(k, t)] = patients

    def solve_model(self, dataDictionary):
        self.dataDictionary = dataDictionary
        self.create_room_specialty_map()
        self.create_room_anesthetist_map()
        self.create_patients_list()

        if(self.packingStrategy == "first fit"):
            self.fill_rooms_first_fit()
        elif(self.packingStrategy == "best fit"):
            self.fill_rooms_best_fit()
        else:
            self.fill_rooms()

        # WIS
        if(self.anesthetistAssignmentStrategy == "WIS"):
            self.compute_patients_order()
            self.select_non_overlapping()
            self.remove_patients_without_anesthetist()
            self.fill_empty_space()
        elif(self.anesthetistAssignmentStrategy == "single_anesthetist_per_room"):
            self.assign_anesthetists()
            self.swap_anesthesia_patients()
            if(self.packingStrategy == "first fit"):
                self.fill_discarded_slots_first_fit()
            elif(self.packingStrategy == "best fit"):
                self.fill_discarded_slots_best_fit()
            else:
                self.fill_discarded_slots()
            self.compute_patients_order()

    def compute_objective_value(self):
        value = 0
        for k in range(1, self.dataDictionary[None]["K"][None] + 1):
            for t in range(1, self.dataDictionary[None]["T"][None] + 1):
                for p in self.solution[(k, t)]:
                    value = value + p.priority
        return value

    def extract_solution(self):
        return self.solution

    # for now, pretend anesthetist has the same span of operating room time
    def select_non_overlapping(self):
        for a in range(1, self.dataDictionary[None]["A"][None] + 1):
            for t in range(1, self.dataDictionary[None]["T"][None] + 1):
                anesthesiaPatients = []
                for k in range(1, self.dataDictionary[None]["K"][None] + 1):
                    for p in self.solution[(k, t)]:
                        if(p.anesthesia == 1 and p.anesthetist == 0):
                            anesthesiaPatients.append(p)

                if(anesthesiaPatients == []):
                    continue
                anesthesiaPatients.sort(key=lambda x: x.order + x.operatingTime)
                pValues = [bisect(list(map((lambda ap: ap.order + ap.operatingTime), anesthesiaPatients)), patient.order) - 1 for patient in anesthesiaPatients]
                optima = [0 for _ in anesthesiaPatients]
                optima[0] = anesthesiaPatients[0].priority

                for i in range(1, len(anesthesiaPatients)):
                    optPi = 0
                    if(pValues[i] != -1):
                        optPi = optima[pValues[i]]
                    optima[i] = max(anesthesiaPatients[i].priority + optPi, optima[i - 1])

                selected = self.find_solution(len(anesthesiaPatients) - 1, anesthesiaPatients, pValues, optima)

                for k in range(1, self.dataDictionary[None]["K"][None] + 1):
                    updatedSolution = []
                    for p in self.solution[(k, t)]:
                        if(p.id in selected):
                            p.anesthetist = a
                        updatedSolution.append(p)
                    self.solution[(k, t)] = updatedSolution

    def remove_patients_without_anesthetist(self):
        for k in range(1, self.dataDictionary[None]["K"][None] + 1):
            for t in range(1, self.dataDictionary[None]["T"][None] + 1):
                updatedSolution = []
                for p in self.solution[(k, t)]:
                    if(p.anesthesia == 0 or p.anesthetist > 0):
                        updatedSolution.append(p)
                self.solution[(k, t)] = updatedSolution


    def find_solution(self, idx, anesthesiaPatients, pValues, optima):
        if(idx == -1):
            return []
        else:
            if(anesthesiaPatients[idx].priority + optima[pValues[idx]] >= optima[idx - 1]):
                return [anesthesiaPatients[idx].id] + self.find_solution(pValues[idx], anesthesiaPatients, pValues, optima)
            else:
                return self.find_solution(idx - 1, anesthesiaPatients, pValues, optima)

    def fill_empty_space(self):
        for k in range(1, self.dataDictionary[None]["K"][None] + 1):
            for t in range(1, self.dataDictionary[None]["T"][None] + 1):
                solutionPatients = self.solution[(k, t)]
                selectedIds = []
                for i in range(0, len(solutionPatients)):
                    validPatients = []
                    residualTime = 0
                    previousPatientFinishing = 0
                    if(i == 0):
                        validPatients = list(filter(lambda p: p.precedence <= solutionPatients[i].precedence and p.anesthesia == 0, self.patients))
                        residualTime = solutionPatients[i].order
                    elif(i < len(solutionPatients) - 1):
                        validPatients = list(filter(lambda p: solutionPatients[i - 1].precedence <= p.precedence and p.precedence <= solutionPatients[i].precedence and p.anesthesia == 0, self.patients))
                        residualTime = solutionPatients[i].order - (solutionPatients[i - 1].order + solutionPatients[i - 1].operatingTime)
                        previousPatientFinishing = solutionPatients[i - 1].order + solutionPatients[i - 1].operatingTime
                    else:
                        validPatients = list(filter(lambda p: solutionPatients[i].precedence <= p.precedence and p.anesthesia == 0, self.patients))
                        residualTime = self.dataDictionary[None]["s"][(k, t)] - (solutionPatients[i].order + solutionPatients[i].operatingTime)
                        previousPatientFinishing = solutionPatients[i].order + solutionPatients[i].operatingTime
                    validPatients = sorted(validPatients, key=lambda x: (x.precedence, x.priority * x.delayWeight / x.operatingTime))
                    for vp in validPatients:
                        if(residualTime - vp.operatingTime < 0 or vp.specialty != self.roomSpecialtyMapping[k]):
                            continue
                        vp.order = previousPatientFinishing
                        previousPatientFinishing = vp.order + vp.operatingTime
                        self.solution[(k, t)].append(vp)
                        self.solution[(k, t)] = sorted(self.solution[(k, t)], key=lambda x: x.order)
                        selectedIds.append(vp.id)
                        residualTime = residualTime - vp.operatingTime
                self.patients = [p for p in self.patients if p.id not in selectedIds]
