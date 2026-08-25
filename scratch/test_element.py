from ortools.sat.python import cp_model
import numpy as np

def test():
    model = cp_model.CpModel()
    x = model.NewIntVar(0, 10, "x")
    y = model.NewIntVar(0, 100, "y")
    
    # Try passing list of native ints
    arr1 = [10, 20, 30, 40, 50]
    print("Testing AddElement with native ints...")
    model.AddElement(x, arr1, y)
    
    # Try passing numpy int64 list (direct cast)
    arr2 = list(np.array([10, 20, 30, 40, 50], dtype=np.int64))
    print("Testing AddElement with list of numpy int64...")
    try:
        model.AddElement(x, arr2, y)
        print("Success!")
    except Exception as e:
        print("Failed:", e)
        
if __name__ == "__main__":
    test()
