import sys
import threading
from tkinter import *
from tkinter.ttk import *

from click import command
from data_maker import DataDescriptor, DataMaker, TruncatedNormalParameters
import fast_complete_heuristic as fce
import fast_complete_heuristic_variant as fcev
import slow_complete_heuristic as sce
import slow_complete_heuristic_variant as scev
import LBBD_planner as lbbd
import LBBD_planner_3_phase as lbbd3p
import greedy_planner as greedy

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

    def round_value(self, value):
        if(self.type == "int"):
            self.variable.set(round(float(value)))
        else:
            self.variable.set(round(float(value), 2))

    def __init__(self, master, type, from_, to, value, orient, labelText):
        super(ScaleWithEntry, self).__init__(master=master)
        self.labelText = StringVar()
        self.labelText.set(labelText)
        self.label = Label(master=self, textvariable=self.labelText)
        self.label.pack(side=TOP, anchor=NW)

        self.variable = None
        self.type = type
        if(type == "int"):
            self.variable = IntVar(value=value)
        else:
            self.variable = DoubleVar(value=value)
        self.slider = Scale(
            master=self,
            from_=from_,
            to=to,
            variable=self.variable,
            # resolution=resolution,
            orient=orient,
            # label=label,
            command=self.round_value
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

    def clear_output(self):
        self.textBox.delete(1.0, END)
        self.textBox.config(state=NORMAL)

    def manage_solver(self, arg):
        if(self.selectedMethod.get() == "greedy"):
            self.solversComboBox.config(state="disabled")
        else:
            self.solversComboBox.config(state="readonly")


    def t_main(self):
        thread = threading.Thread(target=self.main, args=[])
        thread.start()

    def main(self):
        dataDescriptor = DataDescriptor()

        dataDescriptor.patients = self.patients.variable.get()
        dataDescriptor.days = 5
        dataDescriptor.anesthetists = self.anesthetists.variable.get()
        dataDescriptor.covidFrequence = self.covid.variable.get()
        dataDescriptor.anesthesiaFrequence = self.anesthesia.variable.get()
        dataDescriptor.specialtyBalance = 0.17
        dataDescriptor.operatingDayDuration = 270
        dataDescriptor.anesthesiaTime = 270

        dataDescriptor.priorityDistribution = TruncatedNormalParameters(low=1,
                                                                        high=120,
                                                                        mean=60,
                                                                        stdDev=10)
        dataMaker = DataMaker(seed=52876)
        dataContainer = dataMaker.create_data_container(dataDescriptor)
        dataDictionary = dataMaker.create_data_dictionary(dataContainer, dataDescriptor)


        planner = None
        if(self.selectedMethod.get() == "LBBD"):
            planner = lbbd.Planner(timeLimit=self.timeLimit.value.get(), gap=self.gap.value.get()/100, solver=self.selectedSolver.get())
        elif(self.selectedMethod.get() == "FCE"):
            planner = fce.Planner(timeLimit=self.timeLimit.value.get(), gap=self.gap.value.get()/100, solver=self.selectedSolver.get())
        elif(self.selectedMethod.get() == "SCE"):
            planner = sce.Planner(timeLimit=self.timeLimit.value.get(), gap=self.gap.value.get()/100, solver=self.selectedSolver.get())
        elif(self.selectedMethod.get() == "LBBD - 3 Phase Variant"):
            planner = lbbd3p.Planner(timeLimit=self.timeLimit.value.get(), gap=self.gap.value.get()/100, solver=self.selectedSolver.get())
        elif(self.selectedMethod.get() == "FCE - Variant"):
            planner = fcev.Planner(timeLimit=self.timeLimit.value.get(), gap=self.gap.value.get()/100, solver=self.selectedSolver.get())
        elif(self.selectedMethod.get() == "SCE - Variant"):
            planner = scev.Planner(timeLimit=self.timeLimit.value.get(), gap=self.gap.value.get()/100, solver=self.selectedSolver.get())
        else:
            planner = greedy.Planner()

        print("Patients to be operated:\n")
        dataMaker.print_data(dataDictionary)
        runInfo = planner.solve_model(dataDictionary)
        solution = planner.extract_solution()

        sv = SolutionVisualizer()
        sv.print_solution(solution)
        print("Objective function value: " + str(sv.compute_solution_value(solution)))
        sv.plot_graph(solution)

    def initializeUI(self):
        self.parametersFrame = Frame(master=self.master)
        self.parametersFrame.pack(side=LEFT)

        self.patients = ScaleWithEntry(master=self.parametersFrame,
                                       type="int",
                                       from_=1,
                                       to=200,
                                       value=60,
                                       orient="horizontal",
                                       labelText="Patients")
        self.covid = ScaleWithEntry(master=self.parametersFrame,
                                    type="double",
                                    from_=0, to=1,
                                    value=0.2,
                                    orient="horizontal",
                                    labelText="Covid frequency")
        self.anesthesia = ScaleWithEntry(master=self.parametersFrame,
                                         type="double",
                                         from_=0, to=1,
                                         value=0.2,
                                         orient="horizontal",
                                         labelText="Anesthesia frequency")
        self.anesthetists = ScaleWithEntry(master=self.parametersFrame,
                                           type="int",
                                           from_=0,
                                           to=10,
                                           value=1,
                                           orient="horizontal",
                                           labelText="Anesthetists")

        self.patients.pack()
        self.covid.pack()
        self.anesthesia.pack()
        self.anesthetists.pack()

        # solver selection combo
        self.selectedSolver = StringVar()
        self.selectedSolver.set("Select solver")
        self.solvers = ["cplex", "cbc"]
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
        self.selectedMethod.set("Select method")
        self.methods = ["greedy", "FCE", "FCE - Variant", "SCE", "SCE - Variant", "LBBD", "LBBD - 3 Phase Variant"]
        self.methodsComboBox = Combobox(master=self.parametersFrame,
                                        textvariable=self.selectedMethod,
                                        values=self.methods,
                                        state="readonly")
        self.methodsComboBox.bind("<<ComboboxSelected>>", self.manage_solver)
        self.methodsComboBox.pack()

        # run button
        self.runButton = Button(master=self.parametersFrame, width=20, text="Solve", command=self.t_main)
        self.runButton.pack(padx=10)

        # clear output button
        self.clearOutputButton = Button(master=self.parametersFrame, width=20, text="Clear output", command=self.clear_output)
        self.clearOutputButton.pack(padx=10)

        # output frame
        self.textFrame = Frame(master=self.master)
        self.textFrame.pack(side=RIGHT)

        self.scrollBar = Scrollbar(self.textFrame)
        self.scrollBar.pack(side=RIGHT, fill=Y)

        self.textBox = Text(
            master=self.textFrame,
            height=40,
            width=160
        )
        self.textBox.pack(side=LEFT, expand=True)
        self.textBox.config(background="#000000", fg="#ffffff")
        self.textBox.config(yscrollcommand=self.scrollBar.set) # to resize correctly scrollbar

        self.scrollBar.config(command=self.textBox.yview)

        sys.stdout = StdoutRedirector(self.textBox)




ws = Tk()
ws.title("Mini-GUI")
# ws.geometry("")
# ws.config(bg="#bff4da")

# Create a style
style = Style(ws)

# Set the theme with the theme_use method
style.theme_use('winnative')  # put the theme name here, that you want to use

gui = MiniGUI(ws)



ws.mainloop()
