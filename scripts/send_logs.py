import requests
import os

root = r'C:\Users\Colin\Desktop\logs'

for file in os.listdir(root):
    if not os.path.isfile(os.path.join(root, file)):
        continue
    print(file)
    status_code = 0
    is_corrupt = False
    with open(os.path.join(root, file), 'r') as f:
        try:
            r = requests.post('http://localhost:8000/rounds/', files={'log': f})
            status_code = r.status_code
        except UnicodeDecodeError:
            is_corrupt = True
    if is_corrupt:
        os.makedirs(os.path.join(root, 'corrupt'), exist_ok=True)
        os.rename(os.path.join(root, file), os.path.join(root, 'corrupt', file))
        continue
    os.makedirs(os.path.join(root, 'processed'), exist_ok=True)
    if r.status_code in [201, 409]:
        os.rename(os.path.join(root, file), os.path.join(root, 'processed', file))
