class Procedure():
    def __init__(self, date, time, patient_gender, patient_birth_date, service, clinical_question, diagnostic, order_status, medical_doctor, hospital_ward, request_number, access_number, patient_id, episode_number, or_entrance, or_leave):
        self.date = date
        self.time = time
        self.patient_gender = patient_gender
        self.patient_birth_date = patient_birth_date
        self.service = service
        self.clinical_question = clinical_question
        self.diagnostic = diagnostic
        self.order_status = order_status
        self.medical_doctor = medical_doctor
        self.hospital_ward = hospital_ward
        self.request_number = request_number
        self.access_number = access_number
        self.patient_id = patient_id
        self.episode_number = episode_number
        self.or_entrance = or_entrance
        self.or_leave = or_leave

    def to_list(self):
        return [self.date,
                self.time,
                self.patient_gender,
                self.patient_birth_date,
                self.service,
                self.clinical_question,
                self.diagnostic,
                self.order_status,
                self.medical_doctor,
                self.hospital_ward,
                self.request_number,
                self.access_number,
                self.patient_id,
                self.episode_number,
                self.or_entrance,
                self.or_leave]

    def __str__(self):
        return str(self.date) + " " + str(self.time) + " " + self.patient_gender + " " + str(self.patient_birth_date) + " " + self.service + " " + self.clinical_question + " " + self.diagnostic + " " + self.order_status + " " + self.medical_doctor + " " + self.hospital_ward + " " + self.request_number + " " + self.access_number + " " + self.patient_id + " " + self.episode_number + " " + str(self.or_entrance) + " " + str(self.or_leave)
