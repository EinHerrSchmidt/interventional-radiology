from loader import CSVWriter, ExcelLoader

if __name__ == "__main__":
    header = ["DATE", "TIME", "GENDER", "BIRTH_DATE", "SERVICE", "CLINICAL_QUESTION", "DIAGNOSTIC", "ORDER__STATUS",
                      "MEDICAL_DOCTOR", "HOSPITAL_WARD", "REQUEST_NUMBER", "ACCESS_NUMBER", "PATIENT_ID", "EPISODE_NUMBER", "OR_ENTRANCE", "OR_LEAVE", "OR_OCCUPATION"]
    xlsx_loader = ExcelLoader("./xlsx")
    procedures = xlsx_loader.get_procedures()
    procedures_as_lists = []
    for p in procedures:
        procedures_as_lists.append(p.to_list())
    csv_writer = CSVWriter("procedures.csv")
    csv_writer.write(header, procedures_as_lists)
