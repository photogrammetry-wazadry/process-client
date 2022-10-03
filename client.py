import os
import shutil
from glob import glob
import requests
import subprocess

from config import CLIENT_NAME, SERVER_URL, CAN_DO_IMAGES, CAN_DO_MODELS, BLENDER_CALL_PATH


def execute(cmd):
    popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True)
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)


needed_dirs = ["input/", "render/", "temp/"]
for needed_dir in needed_dirs:
    if not os.path.exists(needed_dir):
        os.mkdir(needed_dir)

while True:
    print("Server free, sending request for new work")

    r = requests.get(f"{SERVER_URL}/get_task/{CLIENT_NAME}/{CAN_DO_IMAGES}/{CAN_DO_MODELS}", allow_redirects=True)

    # Headers
    start_index = r.headers['start_index']
    task_type = r.headers['task_type']

    open('project.blend', 'wb').write(r.content)

    if task_type == "render":
        # Clear render directory
        for file in glob("render/*"):
            os.remove(file)

        for line in execute([str(BLENDER_CALL_PATH), "-b", "project.blend", "--python",
                             os.path.join(os.getcwd(), 'find_gpu.py'), "-o",
                             f"{os.path.join(os.getcwd(), 'render')}/###",
                             "-s", str(start_index), "-a"]):
            try:
                print(line, end='')
            except:
                print("Encoding error :\\")

        shutil.make_archive("render", 'zip', "./render")

        files = {'file': open("render.zip", 'rb')}
        values = {'client_name': CLIENT_NAME}
        r = requests.post(f"{SERVER_URL}/submit_task/{CLIENT_NAME}/{task_type}", files=files, data=values)
        os.remove("render.zip")

    else:
        raise NotImplementedError
