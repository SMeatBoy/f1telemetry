import matplotlib.pyplot as plt; plt.rcdefaults()
import numpy as np
import matplotlib.pyplot as plt

people = ('A','B','C','D','E','F','G','H')
y_pos = np.arange(len(people))
bottomdata = 3 + 10 * np.random.rand(len(people))
topdata = 3 + 10 * np.random.rand(len(people))
fig = plt.figure(figsize=(10,8))
ax = fig.add_subplot(111)
ax.barh(y_pos, bottomdata,color='r',align='center')
ax.barh(y_pos, topdata,color='g',align='center')
ax.set_yticks(y_pos)
ax.set_yticklabels(people)
ax.set_xlabel('Distance')

plt.show()