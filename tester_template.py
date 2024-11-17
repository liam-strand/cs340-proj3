import os
import subprocess, sys

# Runs every .event file in the directory and stores all output into .txt files.
for file in os.listdir(os.getcwd()):
    if file.endswith(".event"):
        print("Running LINK_STATE")
        os.system("python sim.py LINK_STATE {} &>> ls_test.txt".format(file))
        print("Running DISTANCE_VECTOR")
        os.system("python sim.py DISTANCE_VECTOR {} &>> dv_test.txt".format(file))
