import sys
try:
    import torch
    print(f"torch: {torch.__version__}")
except ImportError:
    print("torch: not installed")

try:
    import numpy
    print(f"numpy: {numpy.__version__}")
except ImportError:
    print("numpy: not installed")
