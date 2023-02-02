import logging
import sys
import time
from planner import HeuristicLBBDPlanner, VanillaLBBDPlanner
from planner.utils import SolutionVisualizer
from planner.data_maker import DataDescriptor, DataMaker

variant = sys.argv[1] == "True"
maxIterations = int(sys.argv[2])

solvers = ["cplex"]
size = [100, 150, 200]
covid = [0.25]
anesthesia = [0.2, 0.5, 0.8]
anesthetists = [1, 2]
robustness_parameter = [0, 3]

logging.basicConfig(filename='./planner/times_collecting/times/vanilla_LBBD_times.log', encoding='utf-8', level=logging.INFO)
logging.info("Solver\tSize\tRobustness\tCovid\tAnesthesia\tAnesthetists\tcumulated_building_time\tTotal_run_time\tSolver_time\tStatus_OK\tObjective_Function_Value\tGap\tMP_Time_Limit_Hit\tSP_Time_Limit_Hit\tIterations\tSpecialty_1_OR_usage\tSpecialty_2_OR_usage\tSpecialty_1_selected_ratio\tSpecialty_2_selected_ratio\tgenerated_constraints\tdiscarded_constraints\tdiscarded_constraints_ratio")

for solver in solvers:
    for robustness in robustness_parameter:
        for s in size:
            for c in covid:
                for a in anesthesia:
                    for at in anesthetists:

                        planner = VanillaLBBDPlanner(timeLimit=290, gap = 0.0, iterations_cap=maxIterations, solver=solver)

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
                            sv.print_solution(solution)
                            sv.plot_graph(solution)

                        logging.info(solver + "\t"
                                        + str(s) + "\t"
                                        + str(robustness) + "\t"
                                        + str(c) + "\t"
                                        + str(a) + "\t"
                                        + str(at) + "\t"
                                        + str(run_info["cumulated_building_time"]) + "\t"
                                        + str(round(elapsed, 2)) + "\t"
                                        + str(run_info["solver_time"]) + "\t"
                                        + str(run_info["status_ok"]) + "\t"
                                        + str(run_info["objective_function_value"]) + "\t"
                                        + str(run_info["gap"]) + "\t"
                                        + str(run_info["MP_time_limit_hit"]) + "\t"
                                        + str(run_info["time_limit_hit"]) + "\t"
                                        + str(run_info["iterations"]) + "\t"
                                        + str(run_info["specialty_1_OR_utilization"]) + "\t"
                                        + str(run_info["specialty_2_OR_utilization"]) + "\t"
                                        + str(run_info["specialty_1_selection_ratio"]) + "\t"
                                        + str(run_info["specialty_2_selection_ratio"]) + "\t"
                                        + str(run_info["generated_constraints"]) + "\t"
                                        + str(run_info["discarded_constraints"]) + "\t"
                                        + str(run_info["discarded_constraints_ratio"])
                                        )
