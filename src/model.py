class Patient:
    def __init__(self, id, room, specialty, day, operatingTime, covid, anesthesia, anesthetist, order):
        self.id = id
        self.room = room
        self.specialty = specialty
        self.day = day
        self.operatingTime = operatingTime
        self.covid = covid
        self.anesthesia = anesthesia
        self.anesthetist = anesthetist
        self.order = order

    def __str__(self):
        return f'id:{self.id:10}; room:{self.room:10}; specialty:{self.specialty:10}; day:{self.day:10}; operatingTime:{self.operatingTime:10}; covid:{self.covid:10}; anesthesia:{self.anesthesia:10}; anesthetist:{self.anesthetist:10}; order:{self.order:10};'
