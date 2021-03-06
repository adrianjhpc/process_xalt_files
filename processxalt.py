#!/usr/bin/python3
#
# xalt: hash_id and xaltlinkT:Build.UUID are both mechanisms to link between
# the link information and the run information. They can be used interchangeably
# but are not the same values.
#

import sys
import json
import os
import math
import numpy as np
import matplotlib
matplotlib.use('agg') 
import matplotlib.pyplot as plt  

def plot_bar_graph(data, filename, xlabel, ylabel):
    data.sort()

#    plt.locator_params(axis='x', nbins=10)
    labels, ys = zip(*data)

    width = 1
    fig = plt.figure()                                                               
    ax = fig.gca()
    ax.bar(labels, ys, width, align='center')

    plt.xlim(left=labels[0]-1)
    plt.xlim(right=labels[-1]+1)

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    
    plt.savefig(filename + '.png')

    ax.scatter(labels, ys)

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.ylim(bottom=0)

    plt.savefig(filename+'_scatter.png')
    
                        
def process_files(file_path, defined_process_limit = -1):

    root_path = file_path
    
    executables = []
    jobs = []
    
    files_processed = 0
    link_files_processed = 0
    run_files_processed = 0
    
    # Define the number of tasks per node normally, i.e. number of cores
    node_tasks = 24
    
    # Number of files to process before finishing
    process_limit = defined_process_limit
    
    directories = os.listdir(root_path)

    for dir in directories:
        if(process_limit != -1 and files_processed > process_limit): break
        files = os.listdir(root_path+"/"+dir)
        local_executables = []
        for file in files:
            if 'link.' in file:            
                files_processed = files_processed + 1
                link_files_processed = link_files_processed + 1
                with open(root_path+"/"+dir+"/"+file, "r") as read_file:
                    try:
                        data = json.load(read_file)
                        new_executable = {}
                        new_executable["exec"] = data["exec_path"]
                        new_executable["hash"] = data["hash_id"]
                        new_executable["compiler"] = data["link_program"]
                        new_executable["openmp"] = False
                        new_executable["mpi"] = False
                        new_executable["pthread"] = False
                        linkA = data["linkA"]
                        openmp = False
                        mpi = False
                        pthread = False
                        for link in linkA:
                            if 'libomp.' in link[0] or 'libgomp.' in link[0] or 'libiomp.' in link[0]:
                                new_executable["openmp"] = True
                                openmp = True
                            elif 'libmpich' in link[0]:
                                new_executable["mpi"] = True
                                mpi = True
                            elif 'pthread' in link[0]:
                                new_executable["pthread"] = True
                                pthread = True
                                if openmp and mpi and pthread:
                                    break
                            
                        executables.append(new_executable)
                        local_executables.append(new_executable)
                    except:
                        print("Problem with " + root_path+"/"+dir+"/"+file)

        for file in files:
            if 'run.' in file:
                files_processed = files_processed + 1
                run_files_processed = run_files_processed + 1
                with open(root_path+"/"+dir+"/"+file, "r") as read_file:
                    try:
                        data = json.load(read_file)
                        new_job = {}
                        new_job["hash"] = data["hash_id"]
                        userT = data["userT"]
                        valid_data = True
                        for user in userT:
                            if 'num_tasks' in user:
                                new_job["tasks"]  = userT[user]
                                # If the user has specified a stupid number of tasks to aprun then drop this record
                                if(userT[user]  > 200000):
                                    valid_data = False

                            elif 'num_threads' in user:
                                new_job["threads"] = userT[user]
                            elif 'tasksnode' in user:
                                new_job["taskspernode"] = userT[user]
                            elif 'run_time' in user:
                                new_job["runtime"] = userT[user]
                            elif 'hwthreads' in user:
                                new_job["hwthreads"] = userT[user]


                        if(new_job["taskspernode"] == 0):
                            if(new_job["hwthreads"] == 0 or new_job["hwthreads"] == 1):
                                new_job["taskspernode"] =  node_tasks
                            elif(new_job["hwthreads"] == 2):
                                new_job["taskspernode"] = 2 * node_tasks
                            else:
                                new_job["taskspernode"] = node_tasks

                                
                        new_job["found"] = False
                        for link in local_executables:
                            if link["hash"] == new_job["hash"]:
                                new_job["mpi"] = link["mpi"]
                                new_job["openmp"] = link["openmp"]
                                new_job["pthread"] = link["pthread"]
                                new_job["found"] = True
                                break
                            
                        if(valid_data):
                            jobs.append(new_job)
                            
                    except:
                        print("Problem with " + root_path+"/"+dir+"/"+file)
                                                
    
    for idx,job in enumerate(jobs):
        if(not job["found"]):
            for link in executables:
                if link["hash"] == job["hash"]:
                    jobs[idx]["mpi"] = link["mpi"]
                    jobs[idx]["openmp"] = link["openmp"]
                    jobs[idx]["pthread"] = link["pthread"]
                    jobs[idx]["found"] = True
                    break


    total = 0
    mpi = 0
    openmp = 0
    pthread = 0
    hybrid = 0
    pthread_hybrid = 0
    openmp_pthread = 0
    cray = 0
    gnu = 0
    intel = 0
    fortran = 0
    c = 0
    cplusplus = 0
    for executable in executables:
        total = total + 1
        if(executable["mpi"]): mpi = mpi + 1
        if(executable["openmp"]): openmp = openmp + 1
        if(executable["pthread"]): pthread = pthread + 1
        if(executable["mpi"] and executable["openmp"]): hybrid = hybrid + 1
        if(executable["mpi"] and executable["pthread"]): pthread_hybrid = pthread_hybrid + 1
        if(executable["openmp"] and executable["pthread"]): openmp_pthread = openmp_pthread + 1
        if(executable["compiler"] == "ifort"):
            intel = intel + 1
            fortran = fortran + 1
        elif(executable["compiler"] == "icc"):
            intel = intel + 1
            c = c + 1
        elif(executable["compiler"] == "icpc"):
            intel = intel + 1
            cplusplus = cplusplus + 1
        elif(executable["compiler"] == "gfortran"):
            gnu = gnu + 1
            fortran = fortran + 1
        elif(executable["compiler"] == "gcc"):
            gnu = gnu + 1
            c = c + 1
        elif(executable["compiler"] == "g++" or executable["compiler"] == "c++"):
            gnu = gnu + 1
            cplusplus = cplusplus + 1
        elif(executable["compiler"] == "ftn_driver.exe"):
            cray = cray + 1
            fortran = fortran + 1
        elif(executable["compiler"] == "driver.cc"):
            cray = cray + 1
            c = c + 1
        elif(executable["compiler"] == "driver.CC"):
            cray = cray + 1
            cplusplus = cplusplus + 1
        else:
            print("Compiler is : " + executable["compiler"] + " " + executable["exec"])
            
    print("Total files processed: " + str(files_processed))
    print("Link files processed: " + str(link_files_processed))
    print("Run files processed: " + str(run_files_processed))
    
    print("Total link instances: " + str(total))
    print("MPI: " + str(mpi))
    print("OpenMP: " + str(openmp))
    print("PThreads: " + str(pthread))
    print("Hybrid (OpenMP + MPI): " + str(hybrid))
    print("Hybrid (PThreads + MPI): " + str(pthread_hybrid))
    print("Hybrid (OpenMP + PThreads): " + str(openmp_pthread))
    print("Cray compiler: " + str(cray))
    print("GNU compiler: " + str(gnu))
    print("Intel compiler: " + str(intel))
    print("Fortran: " + str(fortran))
    print("C: " + str(c))
    print("C++: " + str(cplusplus))

    # Free up memory for the data analysis
    del executable

    total = 0
    max_tasks = 0
    max_threads = 0
    total_runtime = 0
    openmp_job_count = 0
    mpi_job_count = 0
    hybrid_job_count = 0
    unknown_job_count = 0
    mpi_runtime = 0
    openmp_runtime = 0
    hybrid_runtime = 0
    unknown_runtime = 0
    mpi_nodetime = 0
    openmp_nodetime = 0
    hybrid_nodetime = 0
    mpi_jobs = []
    hybrid_jobs = []
    hybrid_thread_counts = []
    unknown_jobs = []
    for job in jobs:
        total = total + 1
        runtime = job["runtime"]
        total_runtime = total_runtime + runtime
        if(job["tasks"] > max_tasks): max_tasks = job["tasks"]
        if(job["threads"] > max_threads): max_threads = job["threads"]
        if("openmp" in job):
            if(job["openmp"] and not job["mpi"]):
                openmp_job_count = openmp_job_count + 1
                openmp_runtime = openmp_runtime + runtime
            elif(job["mpi"] and not job["openmp"]):
                mpi_job_count = mpi_job_count + 1
                mpi_runtime = mpi_runtime + runtime
                number_of_nodes = math.ceil(job["tasks"]/job["taskspernode"])
                if(number_of_nodes > 4920):
                    print("High node count: ")
                    print(number_of_nodes,job["tasks"],job["taskspernode"])
                    # Setting the maximum number of node on ARCHER
                    number_of_nodes = 4920
                mpi_jobs.append([number_of_nodes,runtime])
            elif(job["mpi"] and job["openmp"]):
                hybrid_job_count = hybrid_job_count + 1
                hybrid_runtime = hybrid_runtime + runtime
                number_of_nodes = math.ceil(job["tasks"]/job["taskspernode"])
                threads = job["threads"]
                hybrid_jobs.append([number_of_nodes,runtime])
                hybrid_thread_counts.append([threads,runtime])
            else:
                print("only pthreads",job["openmp"],job["mpi"])
        # This job was not matched with a link file so we cannot determine the programming approach
        # being used
        else:
            unknown_job_count = unknown_job_count + 1
            unknown_runtime = unknown_runtime + runtime
            number_of_nodes = math.ceil(job["tasks"]/job["taskspernode"])
            unknown_jobs.append([number_of_nodes,runtime])
                
    print("Total run instances: " + str(total))
    print("Total runtime: " + str(total_runtime))
    print("Number of OpenMP jobs: " + str(openmp_job_count))
    print("Number of MPI jobs: " + str(mpi_job_count))
    print("Number of Hybrid jobs: " + str(hybrid_job_count))
    print("Number of Unknown jobs: " + str(unknown_job_count))
    print("MPI runtime: " + str(mpi_runtime))
    print("Hybrid runtime: " + str(hybrid_runtime))
    print("OpenMP runtime: " + str(openmp_runtime))
    print("Unknown runtime: "+ str(unknown_runtime))
    print("Max tasks: " + str(max_tasks))
    print("Max threads: " + str(max_threads))

    mpi_job_counts = []
    mpi_job_runtimes = []

    for job in mpi_jobs:
        number_of_nodes = job[0]
        runtime = job[1]
        found = False
        # Here we are assuming mpi_job_counts and mpi_job_runtimes have the same structure, i.e. the same node count elements. This is true
        # because the additions to the list (in the not found branch below) are done symmetrically.
        for idx,item in enumerate(mpi_job_counts):
            if(item[0] == number_of_nodes):
                found = True
                mpi_job_counts[idx][1] = mpi_job_counts[idx][1] + 1
                mpi_job_runtimes[idx][1] = mpi_job_runtimes[idx][1] + runtime
                break
            
        # This maintains the coupling between the counts and runtimes lists to ensure the node orders are the same in both the lists.
        if(not found):
            mpi_job_counts.append([number_of_nodes,1])
            mpi_job_runtimes.append([number_of_nodes,runtime])


    if(len(mpi_job_counts) > 0):
       plot_bar_graph(mpi_job_counts, 'mpi_jobs_counts', 'number of nodes', 'number of jobs')
       plot_bar_graph(mpi_job_runtimes, 'mpi_jobs_runtimes', 'number of nodes', 'cumulative runtime (seconds)') 

    del mpi_jobs
    del mpi_job_counts
    del mpi_job_runtimes

    hybrid_job_counts = []
    hybrid_job_runtimes = []
    
    for job in hybrid_jobs:
        number_of_nodes = job[0]
        runtime = job[1]
        found = False
        # Here we are assuming hybrid_job_counts and hybrid_job_runtimes have the same structure, i.e. the same node count elements. This is true
        # because the additions to the list (in the not found branch below) are done symmetrically.
        for idx,item in enumerate(hybrid_job_counts):
            if(item[0] == number_of_nodes):
                found = True
                hybrid_job_counts[idx][1] = hybrid_job_counts[idx][1] + 1
                hybrid_job_runtimes[idx][1] = hybrid_job_runtimes[idx][1] + runtime
                break
            
        # This maintains the coupling between the counts and runtimes lists to ensure the node orders are the same in both the lists.
        if(not found):
            hybrid_job_counts.append([number_of_nodes,1])
            hybrid_job_runtimes.append([number_of_nodes,runtime])

    if(len(hybrid_job_counts) > 0):            
        plot_bar_graph(hybrid_job_counts, 'hybrid_jobs_counts', 'number of nodes', 'number of jobs')
        plot_bar_graph(hybrid_job_runtimes, 'hybrid_jobs_runtimes', 'number of nodes', 'cumulative runtime (seconds)')

    del hybrid_jobs
    del hybrid_job_counts
    del hybrid_job_runtimes

    hybrid_job_thread_counts = []
    hybrid_job_thread_runtimes = []
        
    for job in hybrid_thread_counts:
        number_of_threads = job[0]
        runtime = job[1]
        found = False
        for idx,item in enumerate(hybrid_job_thread_counts):
            if(item[0] == number_of_threads):
                found = True
                hybrid_job_thread_counts[idx][1] = hybrid_job_thread_counts[idx][1] + 1
                hybrid_job_thread_runtimes[idx][1] = hybrid_job_thread_runtimes[idx][1] + 1
                break
        
        if(not found):
            hybrid_job_thread_counts.append([number_of_threads,1])
            hybrid_job_thread_runtimes.append([number_of_threads,runtime])


    if(len(hybrid_job_thread_counts) > 0):
        plot_bar_graph(hybrid_job_thread_counts, 'hybrid_jobs_thread_counts', 'number of threads used', 'number of jobs')
        plot_bar_graph(hybrid_job_thread_runtimes, 'hybrid_jobs_thread_runtimes', 'number of threads used', 'cumulative runtime (seconds)') 

    unknown_job_counts = []
    unknown_job_runtimes = []

    for job in unknown_jobs:
        number_of_nodes = job[0]
        runtime = job[1]
        found = False
        # Here we are assuming unknown_job_counts and unknown_job_runtimes have the same structure, i.e. the same node count elements. This is true
        # because the additions to the list (in the not found branch below) are done symmetrically.
        for idx,item in enumerate(unknown_job_counts):
            if(item[0] == number_of_nodes):
                found = True
                unknown_job_counts[idx][1] = unknown_job_counts[idx][1] + 1
                unknown_job_runtimes[idx][1] = unknown_job_runtimes[idx][1] + runtime
                break
            
        # This maintains the coupling between the counts and runtimes lists to ensure the node orders are the same in both the lists.
        if(not found):
            unknown_job_counts.append([number_of_nodes,1])
            unknown_job_runtimes.append([number_of_nodes,runtime])

    if(len(unknown_job_counts) > 0):
        plot_bar_graph(unknown_job_counts, 'unknown_jobs_counts', 'number of nodes', 'number of jobs')
        plot_bar_graph(unknown_job_runtimes, 'unknown_jobs_runtimes', 'number of nodes', 'cumulative runtime (seconds)')


def main(argv):

    if(len(sys.argv) > 3 or len(sys.argv) < 2):
        print("Expecting the path to the xalt files (and an optional parameter specifying how many files to process).")
        print("Incorrect number of parameters passed so...")
        print("Exiting")
        return
    
    filepath = sys.argv[1]
    process_limit = -1
    if(len(sys.argv) == 3):
        process_limit = int(sys.argv[2])
   
    print("Running the analysis on files in " + filepath)
    if(process_limit != -1):
        print("Limiting to processing approximately " + str(process_limit) + " files")     
    process_files(filepath, process_limit)

if __name__ == "__main__":
    main(sys.argv)
