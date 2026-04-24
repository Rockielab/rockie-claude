"""providers/ — multi-provider GPU adapter package.

See base.py for the Protocol every adapter implements. Concrete adapters:
runpod.py, vast.py, primeintellect.py, shadeform.py. The router in
scripts/gpu.py iterates them; scripts/runpod.py is a thin per-provider CLI.
"""
