import numpy as np
from Bolt_Utils import utils

# create an array
array1 = np.array([[0, 1], 
                    [2, 3], 
                    [4, 5], 
                    [6, 7]])

print(utils.normalize(array1[1]))

# find the average of entire array
average1 = np.average(array1, 1)

# find the average across axis 0
average2 = np.average(array1, 0)

#print('\naverage across axis 1:\n', average1)
#print('\naverage across axis 0:\n', average2)

a = np.array([0, 1, 2])
b = np.array([3, 1, 2])
c = np.array([4, 1, 2])
d = np.array([4, 1, 2])

print( utils.MatrixFromVectors((a, b, c, d)) )