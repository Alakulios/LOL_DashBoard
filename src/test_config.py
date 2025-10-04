# test_config.py
from config import queue_types
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
print("Python path:", sys.path)
print(queue_types)