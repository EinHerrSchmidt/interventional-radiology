from model import Patient


class Planner:

    def __init__(self, dataDictionary):
        self.dataDictionary = dataDictionary
        self.create_room_specialty_map()
        self.create_room_anesthetist_map()
        self.create_patients_list()
        self.solution = {}

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
                                         anesthesia=self.dataDictionary[None]["a"][i],
                                         anesthetist=0,
                                         order=0)
                                 )
        # sort patients by r_i
        self.patients.sort(key=lambda x: x.priority)

    # fill rooms, for each day
    def fill_rooms(self):
        for t in range(1, self.dataDictionary[None]["T"][None] + 1):
            for k in range(1, self.dataDictionary[None]["K"][None] + 1):
                selectedPatients = []
                roomCapacity = self.dataDictionary[None]["s"][(k, t)]
                tmpPatients = self.patients
                idx = 0
                for patient in tmpPatients:
                    if(self.roomSpecialtyMapping[k] == patient.specialty and patient.operatingTime <= roomCapacity):
                        selectedPatients.append(patient)
                        roomCapacity = roomCapacity - patient.operatingTime
                        self.patients.pop(idx)
                    idx = idx + 1
                self.solution[(k, t)] = selectedPatients

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
                                        # sort by operating time
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
                selectedPatients = self.solution[(k, t)]
                roomCapacity = self.dataDictionary[None]["s"][(k, t)] - sum(p.operatingTime for p in selectedPatients)
                tmpPatients = self.patients
                idx = 0
                for patient in tmpPatients:
                    if(patient.anesthesia == 0 and self.roomSpecialtyMapping[k] == patient.specialty and patient.operatingTime <= roomCapacity):
                        selectedPatients.append(patient)
                        roomCapacity = roomCapacity - patient.operatingTime
                        self.patients.pop(idx)
                    idx = idx + 1
                self.solution[(k, t)] = selectedPatients

    # fix order
    def compute_patients_order(self):
        for k in range(1, self.dataDictionary[None]["K"][None] + 1):
            for t in range(1, self.dataDictionary[None]["T"][None] + 1):
                patients = self.solution[(k, t)]
                patients.sort(key=lambda x: x.covid)
                for i in range(1, len(patients)):
                    patients[i].order = sum(p.operatingTime for p in patients[:i])
                patients.sort(key=lambda x: x.order)
                self.solution[(k, t)] = patients

    def compute_solution(self):
        self.fill_rooms()
        self.assign_anesthetists()
        self.swap_anesthesia_patients()
        self.fill_discarded_slots()
        self.compute_patients_order()
        return self.solution

    def compute_objective_value(self):
        value = 0
        for k in range(1, self.dataDictionary[None]["K"][None] + 1):
            for t in range(1, self.dataDictionary[None]["T"][None] + 1):
                for p in self.solution[(k, t)]:
                    value = value + p.priority
        return value