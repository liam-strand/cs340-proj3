import os
import subprocess as sp

for file in sorted(os.listdir(os.getcwd() + "/adversarial_cases")):
    if file.endswith(".event"):
        print(f"Running LINK_STATE on {file}")
        res = sp.run(["python3", "sim.py", "LINK_STATE", "testing_suite/" + file], 
                     stdout=sp.PIPE, stderr=sp.STDOUT)
        if b"incorrect" in res.stdout:
            print("FAILURE!!")
            print(res.stdout.decode())
        else:
            print("SUCCESS!!")
