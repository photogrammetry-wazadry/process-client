import os
import shutil
from glob import glob
import requests
import subprocess
import zipfile
import time

from config import CLIENT_NAME, SERVER_URL, CAN_DO_IMAGES, CAN_DO_MODELS, BLENDER_CALL_PATH, METASHAPE_CALL_PATH


env = os.environ.copy()
env["DISPLAY"] = ":0"

def execute(cmd):
    popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, env=env, universal_newlines=True)

    try:
        for stdout_line in iter(popen.stdout.readline, ""):
            yield stdout_line
    except:
        pass

    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)


needed_dirs = ["input/", "render/", "temp/"]
for needed_dir in needed_dirs:
    if not os.path.exists(needed_dir):
        os.mkdir(needed_dir)

while True:
    print("\nServer free, sending request for new work")

    r = requests.get(f"{SERVER_URL}/get_task/{CLIENT_NAME}/{CAN_DO_IMAGES}/{CAN_DO_MODELS}", allow_redirects=True)

    # Headers
    print(r)
    task_type = r.headers['task_type']

    if task_type == "render":
        open('project.blend', 'wb').write(r.content)

        # Clear render directory
        for file in glob("render/*"):
            os.remove(file)

        for line in execute([str(BLENDER_CALL_PATH), "-b", "-E", "BLENDER_EEVEE", "project.blend", "-o",
                             f"{os.path.join(os.getcwd(), 'render')}/###",
                             "-s", str(1), "-a"]):
            try:
                print(line, end='')
            except:
                print("Encoding error :\\")

        print("Rendering finished, archiving images")
        shutil.make_archive("render", 'zip', "./render")

        print("Sending results to main server now")
        files = {'file': open("render.zip", 'rb')}
        values = {'client_name': CLIENT_NAME}
        r = requests.post(f"{SERVER_URL}/submit_task/{CLIENT_NAME}/{task_type}", files=files, data=values)
        os.remove("render.zip")

    else:
        if os.path.exists("model.zip"):
            os.remove("model.zip")

        open('photos.zip', 'wb').write(r.content)
        
        output_dir = "metashape_api/render"
        for file_name in glob(os.path.join(output_dir, "*.png")):
            os.remove(file_name)

        # Extract
        with zipfile.ZipFile("photos.zip", 'r') as zip_ref:
            zip_ref.extractall(output_dir)

        print("Starting calc")
        for line in execute([METASHAPE_CALL_PATH, "-r", "metashape_api/load.py"]):
            try:
                print(line, end='')
            except:
                print("Encoding error :\\")

        shutil.make_archive("model", 'zip', "./output")
        files = {'file': open("model.zip", 'rb')}
        values = {'client_name': CLIENT_NAME}
        r = requests.post(f"{SERVER_URL}/submit_task/{CLIENT_NAME}/{task_type}", files=files, data=values)
        
        time.sleep(60)
