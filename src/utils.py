from numpy import sort
import plotly.express as px
import pandas as pd
import datetime

from pyparsing import PrecededBy

from model import Patient

class SolutionVisualizer:

    def __init__(self):
        pass

    def compute_solution_value(self, solution):
        KT = max(solution.keys())
        K = KT[0]
        T = KT[1]

        value = 0
        for t in range(1, T + 1):
            for k in range(1, K + 1):
                for patient in solution[(k, t)]:
                    value = value + patient.priority
        return value

    def print_patients_by_precedence(self, solution):
        KT = max(solution.keys())
        K = KT[0]
        T = KT[1]

        PO = 0
        PR = 0
        SO = 0
        SR = 0
        CO = 0
        CR = 0
        for t in range(1, T + 1):
            for k in range(1, K + 1):
                for patient in solution[(k, t)]:
                    if(patient.precedence == 1):
                        PO += 1
                    elif(patient.precedence == 2):
                        PR += 1
                    elif(patient.precedence == 3):
                        SO += 1
                    elif(patient.precedence == 4):
                        SR += 1
                    elif(patient.precedence == 5):
                        CO += 1
                    elif(patient.precedence == 6):
                        CR += 1
        print("PO: " + str(PO) + "\n" + "PR " + str(PR) + "\n" + "SO: " + str(SO) + "\n" + "SR: " + str(SR) + "\n" + "CO: " + str(CO) + "\n" + "CR: " + str(CR) + "\n")

    def compute_solution_partitioning_by_precedence(self, solution):
        KT = max(solution.keys())
        K = KT[0]
        T = KT[1]

        PO = 0
        PR = 0
        SO = 0
        SR = 0
        CO = 0
        CR = 0
        for t in range(1, T + 1):
            for k in range(1, K + 1):
                for patient in solution[(k, t)]:
                    if(patient.precedence == 1):
                        PO += 1
                    elif(patient.precedence == 2):
                        PR += 1
                    elif(patient.precedence == 3):
                        SO += 1
                    elif(patient.precedence == 4):
                        SR += 1
                    elif(patient.precedence == 5):
                        CO += 1
                    elif(patient.precedence == 6):
                        CR += 1

        return [PO, PR, SO, SR, CO, CR]


    def print_solution(self, solution):
        if(solution is None):
            print("No solution was found!")
            return

        KT = max(solution.keys())
        K = KT[0]
        T = KT[1]

        print("Operated patients, for each day and for each room:\n")

        operatedPatients = 0
        for t in range(1, T + 1):
            for k in range(1, K + 1):
                print("Day: " + str(t) + "; Operating Room: S" + str(k))
                if(len(solution[(k, t)]) == 0):
                    print("---")
                for patient in solution[(k, t)]:
                    print(patient)
                    operatedPatients += 1
                print("\n")
        print("Total number of operated patients: " + str(operatedPatients))

    def solution_as_string(self, solution):
        KT = max(solution.keys())
        K = KT[0]
        T = KT[1]

        result = "Operated patients, for each day and for each room:\n"
        for t in range(1, T + 1):
            for k in range(1, K + 1):
                result += "Day: " + str(t) + "; Operating Room: S" + str(k) + "\n"
                if(len(solution[(k, t)]) == 0):
                    result += "---" + "\n"
                for patient in solution[(k, t)]:
                    result += str(patient) + "\n"
                result += "\n"
        return result

    def count_operated_patients(self, solution):
        KT = max(solution.keys())
        K = KT[0]
        T = KT[1]

        operatedPatients = 0
        for t in range(1, T + 1):
            for k in range(1, K + 1):
                operatedPatients += len(solution[(k, t)])
        return operatedPatients

    def compute_solution_partitioning_by_precedence(self, solution):
        KT = max(solution.keys())
        K = KT[0]
        T = KT[1]

        PO = 0
        PR = 0
        SO = 0
        SR = 0
        CO = 0
        CR = 0
        for t in range(1, T + 1):
            for k in range(1, K + 1):
                for patient in solution[(k, t)]:
                    if(patient.precedence == 1):
                        PO += 1
                    elif(patient.precedence == 2):
                        PR += 1
                    elif(patient.precedence == 3):
                        SO += 1
                    elif(patient.precedence == 4):
                        SR += 1
                    elif(patient.precedence == 5):
                        CO += 1
                    elif(patient.precedence == 6):
                        CR += 1

        return [PO, PR, SO, SR, CO, CR]

    def plot_graph(self, solution):
        if(solution is None):
            print("No solution exists to be plotted!")
            return

        KT = max(solution.keys())
        K = KT[0]
        T = KT[1]

        dataFrames = []
        dff = pd.DataFrame([])
        for t in range(1, T + 1):
            df = pd.DataFrame([])
            for k in range(1, K + 1):
                patients = solution[(k, t)]
                for idx in range(0, len(patients)):
                    patient = patients[idx]
                    start = datetime.datetime(1970, 1, t, 8, 0, 0) + datetime.timedelta(minutes=round(patient.order))
                    finish = start + datetime.timedelta(minutes=round(patient.operatingTime))
                    room = "S" + str(k)
                    covid = "Y" if patient.covid == 1 else "N"
                    precedence = patient.precedence
                    anesthesia = "Y" if patient.anesthesia == 1 else "N"
                    anesthetist = "A" + str(patient.anesthetist) if patient.anesthetist != 0 else ""
                    if(precedence == 1):
                        precedence = "Clean procedure, on schedule"
                    elif(precedence == 2):
                        precedence = "Clean procedure, delay expected"
                    elif(precedence == 3):
                        precedence = "Dirty procedure, on schedule"
                    elif(precedence == 4):
                        precedence = "Dirty procedure, delay expected"
                    elif(precedence == 5):
                        precedence = "Covid-19 patient, on schedule"
                    elif(precedence == 6):
                        precedence = "Covid-19 patient, delay expected"
                    dataFrameToAdd = pd.DataFrame([dict(Start=start, Finish=finish, Room=room, Covid=covid, Precedence=precedence, Anesthesia=anesthesia, Anesthetist=anesthetist)])
                    df = pd.concat([df, dataFrameToAdd])
            dataFrames.append(df)
            dff = pd.concat([df, dff])

        # sort legend's labels
        sortingOrder = ["Clean procedure, on schedule", "Clean procedure, delay expected",
                        "Dirty procedure, on schedule", "Dirty procedure, delay expected",
                        "Covid-19 patient, on schedule", "Covid-19 patient, delay expected"]
        order  = []
        for precedenceValue in dff["Precedence"].tolist():
            if(not precedenceValue in order):
                order.append(precedenceValue)
        order.sort(key=sortingOrder.index)
        dff = dff.set_index('Precedence')
        dff= dff.T[order].T.reset_index()

        color_discrete_map = {'Clean procedure, on schedule': '#38A6A5', 'Clean procedure, delay expected': '#0F8554',
                                'Dirty procedure, on schedule': '#73AF48', 'Dirty procedure, delay expected': '#EDAD08',
                                'Covid-19 patient, on schedule': '#E17C05', 'Covid-19 patient, delay expected': '#CC503E'}

        fig = px.timeline(dff,
                          x_start="Start",
                          x_end="Finish",
                          y="Room",
                          color="Precedence",
                          text="Anesthetist",
                          labels={"Start": "Procedure start", "Finish": "Procedure end", "Room": "Operating room",
                                  "Covid": "Covid patient", "Precedence": "Procedure Type and Delay", "Anesthesia": "Need for anesthesia", "Anesthetist": "Assigned anesthetist"},
                          hover_data=["Anesthesia", "Anesthetist", "Precedence", "Covid"],
                          color_discrete_map=color_discrete_map
                          )

        fig.update_xaxes(
        rangebreaks=[
        dict(bounds=['1970-01-01 12:30:00','1970-01-02 08:00:00']),
        dict(bounds=['1970-01-02 12:30:00','1970-01-03 08:00:00']),
        dict(bounds=['1970-01-03 12:30:00','1970-01-04 08:00:00']),
        dict(bounds=['1970-01-04 12:30:00','1970-01-05 08:00:00'])
        ]
        )

        fig.add_vline(x='1970-01-01 08:00:00', line_width=1, line_dash="solid", line_color="black")
        fig.add_vline(x='1970-01-02 08:00:00', line_width=1, line_dash="solid", line_color="black")
        fig.add_vline(x='1970-01-03 08:00:00', line_width=1, line_dash="solid", line_color="black")
        fig.add_vline(x='1970-01-04 08:00:00', line_width=1, line_dash="solid", line_color="black")
        fig.add_vline(x='1970-01-05 08:00:00', line_width=1, line_dash="solid", line_color="black")
        fig.add_vline(x='1970-01-05 12:30:00', line_width=1, line_dash="solid", line_color="black")

        fig.update_layout(xaxis=dict(title='Timetable', tickformat='%H:%M:%S',), legend={"traceorder": "normal"})
        fig.update_layout(legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
        ))
        fig.update_yaxes(categoryorder='category descending')
        fig.show()

    def compute_room_utilization(self, solution, dataDictionary):
        if(solution is None):
            return {"Specialty1ORUsage": -1,
                "Specialty2ORUsage": -1,
                "Specialty1SelectedRatio": -1,
                "Specialty2SelectedRatio": -1
            }
        overallPatients = []
        for i in range(1, dataDictionary[None]["I"][None] + 1):
            overallPatients.append(Patient(id=i,
                                            priority=dataDictionary[None]["r"][i],
                                            room=0,
                                            specialty=dataDictionary[None]["specialty"][i],
                                            day=0,
                                            operatingTime=dataDictionary[None]["p"][i],
                                            covid=dataDictionary[None]["c"][i],
                                            precedence=dataDictionary[None]["precedence"][i],
                                            delayWeight=None,
                                            anesthesia=dataDictionary[None]["a"][i],
                                            anesthetist=0,
                                            order=0)
                                    )

        specialty1TotalPatients = sum(map(lambda _: 1, list(filter(lambda p: p.specialty == 1, overallPatients))))
        specialty2TotalPatients = sum(map(lambda _: 1, list(filter(lambda p: p.specialty == 2, overallPatients))))

        KT = max(solution.keys())
        K = KT[0]
        T = KT[1]
        specialty1TotalTime = 0
        specialty2TotalTime = 0

        specialty1UsedTime = 0
        specialty2UsedTime = 0

        specialty1SelectedPatients = 0
        specialty2SelectedPatients = 0

        for t in range(1, T + 1):
            for k in range(1, K + 1):
                if(k == 1 or k == 2):
                    specialty1TotalTime += dataDictionary[None]["s"][(k, t)]
                else:
                    specialty2TotalTime += dataDictionary[None]["s"][(k, t)]
                for patient in solution[(k, t)]:
                    if(patient.specialty == 1):
                        specialty1UsedTime += patient.operatingTime
                        specialty1SelectedPatients += 1
                    else:
                        specialty2UsedTime += patient.operatingTime
                        specialty2SelectedPatients += 1

        return {"Specialty1ORUsage": specialty1UsedTime / specialty1TotalTime,
                "Specialty2ORUsage": specialty2UsedTime / specialty2TotalTime,
                "Specialty1SelectedRatio": specialty1SelectedPatients / specialty1TotalPatients,
                "Specialty2SelectedRatio": specialty2SelectedPatients / specialty2TotalPatients
        }