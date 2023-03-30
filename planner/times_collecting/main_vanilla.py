import logging
import sys
import time
from planner import SimplePlanner
from planner.utils import SolutionVisualizer
from planner.data_maker import DataDescriptor, DataMaker

solvers = ["cplex"]
size = [100, 150, 200]
covid = [0.25]
anesthesia = [0.2, 0.5, 0.8]
anesthetists = [1, 2]
robustness_parameter = [0, 2, 3, 5]

logging.basicConfig(filename='./planner/times_collecting/times/vanilla_times.log', encoding='utf-8', level=logging.INFO)
logging.info("Solver\tSize\tCovid\tAnesthesia\tAnesthetists\tBuilding_time\tRun_time\tSolverTime\tStatus_OK\tObjective_Function_Value\tTime_Limit_Hit\tUpper_bound\tGap\tspecialty_1_OR_utilization\tspecialty_2_OR_utilization\tspecialty_1_selection_ratio\tspecialty_2_selection_ratio\tgenerated_constraints\tdiscarded_constraints\tdiscarded_constraints_ratio")

for solver in solvers:
    for robustness in robustness_parameter:
        for s in size:
            for c in covid:
                for a in anesthesia:
                    for at in anesthetists:

                        planner = SimplePlanner(300, 0.0, solver)

                        data_descriptor = DataDescriptor(patients=s,
                                                        days=5,
                                                        anesthetists=at,
                                                        infection_frequency=c,
                                                        anesthesia_frequency=a,
                                                        specialty_frequency=[0.83, 0.17],
                                                        robustness_parameter=robustness)

                        dataMaker = DataMaker(seed=52876, data_descriptor=data_descriptor)
                        dataDictionary = dataMaker.create_data_dictionary()
                        t = time.time()
                        dataMaker.print_data(dataDictionary)
                        planner.solve_model(dataDictionary)
                        run_info = planner.extract_run_info()
                        elapsed = (time.time() - t)

                        solution = planner.extract_solution()
                        if solution:
                            sv = SolutionVisualizer()
                            # sv.print_solution(solution)
                            # sv.plot_graph(solution)

                        logging.info(solver + "\t"
                                        + str(s) + "\t"
                                        + str(c) + "\t"
                                        + str(a) + "\t"
                                        + str(at) + "\t"
                                        + str(run_info["cumulated_building_time"]) + "\t"
                                        + str(round(elapsed, 2)) + "\t"
                                        + str(run_info["solver_time"]) + "\t"
                                        + str(run_info["status_ok"]) + "\t"
                                        + str(run_info["objective_function_value"]) + "\t"
                                        + str(run_info["time_limit_hit"]) + "\t"
                                        + str(run_info["upper_bound"]) + "\t"
                                        + str(run_info["gap"]) + "\t"
                                        + str(run_info["specialty_1_OR_utilization"]) + "\t"
                                        + str(run_info["specialty_2_OR_utilization"]) + "\t"
                                        + str(run_info["specialty_1_selection_ratio"]) + "\t"
                                        + str(run_info["specialty_2_selection_ratio"]) +"\t"
                                        + str(run_info["generated_constraints"]) + "\t"
                                        + str(run_info["discarded_constraints"]) + "\t"
                                        + str(run_info["discarded_constraints_ratio"])
                                        )


