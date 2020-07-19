import sys
import os
from datetime import datetime

start_time = datetime.now()
os.system(f"python3 resnet_prayog10.py 2>&1 | tee resnet.log")
print(f"\n resnet_prayog10.py took {datetime.now() - start_time} to finish\n")

start_time = datetime.now()
os.system(f"python3 googlenet_prayog10.py 2>&1 | tee googlenet.log")
print(f"\n googlenet_prayog10.py took {datetime.now() - start_time} to finish\n")

start_time = datetime.now()
os.system(f"python3 standard_lstm_prayog10.py 2>&1 | tee standard_lstm.log")
print(f"\n standard_lstm_prayog10.py took {datetime.now() - start_time} to finish\n")

start_time = datetime.now()
os.system(f"python3 standard_tcn_prayog10.py 2>&1 | tee standard_tcn.log")
print(f"\n standard_tcn_prayog10.py took {datetime.now() - start_time} to finish\n")

start_time = datetime.now()
os.system(f"python3 ridiculous_tcn_prayog10.py 2>&1 | tee ridiculous_tcn.log")
print(f"\n ridiculous_tcn_prayog10.py took {datetime.now() - start_time} to finish\n")

start_time = datetime.now()
os.system(f"python3 ridiculous_lstm_prayog10.py 2>&1 | tee ridiculous_lstm.log")
print(f"\n ridiculous_lstm_prayog10.py took {datetime.now() - start_time} to finish\n")