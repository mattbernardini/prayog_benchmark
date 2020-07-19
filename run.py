import sys
import os
from datetime import datetime

start_time = datetime.now()
os.system(f"python3 resnet.py 2>&1 | tee resnet.log")
print(f"\n resnet.py took {datetime.now() - start_time} to finish\n")

start_time = datetime.now()
os.system(f"python3 googlenet.py 2>&1 | tee googlenet.log")
print(f"\n googlenet.py took {datetime.now() - start_time} to finish\n")

start_time = datetime.now()
os.system(f"python3 standard_lstm.py 2>&1 | tee standard_lstm.log")
print(f"\n standard_lstm.py took {datetime.now() - start_time} to finish\n")

start_time = datetime.now()
os.system(f"python3 standard_tcn.py 2>&1 | tee standard_tcn.log")
print(f"\n standard_tcn.py took {datetime.now() - start_time} to finish\n")

start_time = datetime.now()
os.system(f"python3 ridiculous_tcn.py 2>&1 | tee ridiculous_tcn.log")
print(f"\n ridiculous_tcn.py took {datetime.now() - start_time} to finish\n")

start_time = datetime.now()
os.system(f"python3 ridiculous_lstm.py 2>&1 | tee ridiculous_lstm.log")
print(f"\n ridiculous_lstm.py took {datetime.now() - start_time} to finish\n")