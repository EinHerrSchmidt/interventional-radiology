import sys
import threading
import time
from tkinter import *
from tkinter.ttk import Combobox
from data_maker import DataDescriptor, DataMaker, TruncatedNormalParameters
import fast_complete_heuristic as fce

from utils import SolutionVisualizer


class StdoutRedirector(object):
    def __init__(self, textWidget):
        self.textSpace = textWidget

    def write(self, string):
        self.textSpace.insert("end", string)
        self.textSpace.see("end")

    def flush(self):
        pass


class EntryWithLabel(Frame):
    def __init__(self, master, value, labelText):
        super(EntryWithLabel, self).__init__(master=master)
        self.labelText = StringVar()
        self.labelText.set(labelText)
        self.label = Label(master=self, textvariable=self.labelText)
        self.label.pack(side=LEFT)

        self.value = DoubleVar()
        self.value.set(value)
        self.entry = Entry(
            master=self,
            textvariable=self.value,
            width=5
        )
        self.entry.pack(expand=True, side=LEFT)


class ScaleWithEntry(Frame):

    def __init__(self, master, type, from_, to, value, resolution, orient, label):
        super(ScaleWithEntry, self).__init__(master=master)
        self.variable = None
        if(type == "int"):
            self.variable = IntVar(value=value)
        else:
            self.variable = DoubleVar(value=value)
        self.slider = Scale(
            master=self,
            from_=from_,
            to=to,
            variable=self.variable,
            resolution=resolution,
            orient=orient,
            label=label
        )
        self.slider.pack(side=LEFT)

        self.entry = Entry(
            master=self,
            textvariable=self.variable,
            width=4
        )
        self.entry.pack(expand=True, side=RIGHT)


class MiniGUI(object):
    def __init__(self, master):
        self.master = master
        self.initializeUI()
        # button = Button(self.parent, text="Start", command=self.main)
        # button.grid(column=0, row=1, columnspan=2)

    def t_main(self):
        thread = threading.Thread(target=self.main, args=[])
        thread.start()

    def main(self):
        print("Hello!")
        planner = fce.Planner(timeLimit=self.timeLimit.value.get(), gap=self.gap.value.get()/100, solver=self.selectedSolver.get())

        dataDescriptor = DataDescriptor()

        dataDescriptor.patients = self.patients.variable.get()
        dataDescriptor.days = 5
        dataDescriptor.anesthetists = self.anesthetists.variable.get()
        dataDescriptor.covidFrequence = self.covid.variable.get()
        dataDescriptor.anesthesiaFrequence = self.anesthesia.variable.get()
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
        t = time.time()
        # print("\nPatients to be operated:\n")
        dataMaker.print_data(dataDictionary)
        runInfo = planner.solve_model(dataDictionary)
        elapsed = (time.time() - t)

        solution = planner.extract_solution()

        sv = SolutionVisualizer()
        sv.print_solution(solution)
        sv.plot_graph(solution)

    def initializeUI(self):
        self.parametersFrame = Frame(master=self.master)
        self.parametersFrame.pack(side=LEFT)

        self.patients = ScaleWithEntry(master=self.parametersFrame,
                                       type="int",
                                       from_=1,
                                       to=200,
                                       value=60,
                                       resolution=1,
                                       orient="horizontal",
                                       label="Patients")
        self.covid = ScaleWithEntry(master=self.parametersFrame,
                                    type="double",
                                    from_=0, to=1,
                                    value=0.2,
                                    resolution=0.01,
                                    orient="horizontal",
                                    label="Covid frequency")
        self.anesthesia = ScaleWithEntry(master=self.parametersFrame,
                                         type="double",
                                         from_=0, to=1,
                                         value=0.2,
                                         resolution=0.01,
                                         orient="horizontal",
                                         label="Anesthesia frequency")
        self.anesthetists = ScaleWithEntry(master=self.parametersFrame,
                                           type="int",
                                           from_=0,
                                           to=10,
                                           value=1,
                                           resolution=1,
                                           orient="horizontal",
                                           label="Anesthetists")

        self.patients.pack()
        self.covid.pack()
        self.anesthesia.pack()
        self.anesthetists.pack()

        # solver selection combo
        self.selectedSolver = StringVar()
        self.selectedSolver.set("Select solver")
        self.solvers = ["cplex", "gurobi", "cbc"]
        self.solversComboBox = Combobox(master=self.parametersFrame,
                                        textvariable=self.selectedSolver,
                                        values=self.solvers,
                                        state="readonly")
        self.solversComboBox.pack()

        # solver's parameters
        self.timeLimit = EntryWithLabel(
            master=self.parametersFrame, value=300, labelText="Time limit (s)")
        self.timeLimit.pack(anchor=E)

        self.gap = EntryWithLabel(
            master=self.parametersFrame, value=1, labelText="Gap (%)")
        self.gap.pack(anchor=E)

        # method selection combo
        self.selectedMethod = StringVar()
        self.selectedMethod.set("Select resolution method")
        self.methods = ["greedy", "FCE", "SCE", "LBBD"]
        self.methodsComboBox = Combobox(master=self.parametersFrame,
                                        textvariable=self.selectedMethod,
                                        values=self.methods,
                                        state="readonly")
        self.methodsComboBox.pack()

        # run button
        self.runButton = Button(
            master=self.parametersFrame, width=20, text="Solve", command=self.t_main)
        self.runButton.pack(padx=10)

        # output frame
        self.textFrame = Frame(master=self.master)
        self.textFrame.pack(side=RIGHT)

        self.textBox = Text(
            master=self.textFrame,
            height=40,
            width=200
        )
        self.textBox.pack(expand=True)
        self.textBox.config(background="#000000", fg="#ffffff")

        sys.stdout = StdoutRedirector(self.textBox)


ws = Tk()
ws.title("Mini-GUI")
# ws.geometry("")
# ws.config(bg="#bff4da")

gui = MiniGUI(ws)

ws.mainloop()
