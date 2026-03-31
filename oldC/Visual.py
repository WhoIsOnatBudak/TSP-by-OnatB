import numpy as np
import matplotlib.pyplot as plt

# dosyaları oku
xy = np.loadtxt("nodes.csv", delimiter=",")
order = np.loadtxt("tour.txt", dtype=int)

# düğümler
plt.scatter(xy[:,0], xy[:,1])
for i,(x,y) in enumerate(xy):
    plt.text(x, y, str(i), fontsize=9)

# tur çizgileri (kapat)
path = xy[order]
path = np.vstack([path, path[0]])
plt.plot(path[:,0], path[:,1])

plt.title("TSP Tour")
plt.xlabel("x"); plt.ylabel("y"); plt.grid(True)
plt.show()
