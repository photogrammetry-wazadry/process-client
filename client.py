import sys
# caution: path[0] is reserved for script path (or '' in REPL)
sys.path.insert(1, 'blender-sphere-renderer')

import os
import shutil
from glob import glob
import requests
from main import orbit_render, execute


CLIENT_NAME = "dev"
SERVER_URL = "http://127.0.0.1:1303"
CAN_DO_IMAGES = "true"
CAN_DO_MODELS = "false"


while True:
    print("Server free, sending request for new work")

    r = requests.get(f"{SERVER_URL}/get_task/{CLIENT_NAME}/{CAN_DO_IMAGES}/{CAN_DO_MODELS}", allow_redirects=True)

    # Headers
    start_index = r.headers['start_index']
    task_type = r.headers['task_type']

    open('input/model.zip', 'wb').write(r.content)

    if task_type == "render":
        # Clear render directory
        for file in glob("render/*"):
            os.remove(file)

        orbit_render("model.zip")  # Import and normalise size of the model

        for line in execute(["blender", "-b", "project.blend", "-o", f"{os.path.join(os.getcwd(), 'render')}/###",
                                        "-s", str(start_index), "-a"]):
            print(line, end='')

        shutil.make_archive("render", 'zip', "./render")

        files = {'file': open("render.zip", 'rb')}
        values = {'client_name': CLIENT_NAME}
        r = requests.post(f"{SERVER_URL}/submit_task/{CLIENT_NAME}/{task_type}", files=files, data=values)
        os.remove("render.zip")

    else:
        raise NotImplementedError
