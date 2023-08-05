import glob
import json
import sys
from collections import Counter
import matplotlib.pyplot as plt

files = glob.glob(f'{sys.argv[1]}/*.json')
print(f"{len(files)} files")
cnt = 0
results = []
for fname in files:
    with open(fname) as f:
        data = json.load(f)
    cnt += len(data)
    results.extend([r['rating'] for r in data.values()])
print(f"{cnt} records")
print(Counter(results))

def draw_hist(results, path="hist.png"):
    plt.hist(results, bins=10)
    plt.savefig(path)
    plt.show()

draw_hist(results)