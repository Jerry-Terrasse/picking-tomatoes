import glob
import json
import sys

files = glob.glob(f'{sys.argv[1]}/*.json')
print(f"{len(files)} files")
cnt = 0
for fname in files:
    with open(fname) as f:
        data = json.load(f)
    cnt += len(data)
print(f"{cnt} records")