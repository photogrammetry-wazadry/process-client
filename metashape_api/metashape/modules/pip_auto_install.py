import hashlib
import importlib
import json
import os
import platform
import PySide2
import sys
import time
import inspect

from pathlib import Path
from PySide2 import QtCore, QtWidgets, QtGui

_app = QtWidgets.QApplication.instance()
_parent_window = None
for _widget in _app.topLevelWidgets():
    if(type(_widget) is QtWidgets.QMainWindow):
        _parent_window = _widget

_app_data_location = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DataLocation)
if os.name == 'nt': # if windows
    _app_data_location = _app_data_location.replace('/', '\\')

_user_packages_location = os.path.join(_app_data_location, "user-packages")

_installed_requirements_path = os.path.join(_user_packages_location, "installed_requirements.txt")

def _mkdirs():
    Path(_app_data_location).mkdir(parents=True, exist_ok=True)
    Path(_user_packages_location).mkdir(parents=True, exist_ok=True)

class _ProgressDialog(QtWidgets.QDialog):
    def __init__(self, _parent_window):
        QtWidgets.QDialog.__init__(self, _parent_window)

        self.resize(357, 274)

        self.setWindowTitle("Processing in progress...")
        self.labelStatus = QtWidgets.QLabel()
        self.labelStatus.setText("Installing script requirements:")

        self.progressPartial = QtWidgets.QProgressBar()
        self.progressPartial.setTextVisible(False)
        self.progressPartial.setValue(24)

        self.labelTime = QtWidgets.QLabel()
        self.labelTime.setText("<time>")

        self.labelOverall = QtWidgets.QLabel()
        self.labelOverall.setText("Overall progress:")

        self.progressOverall = QtWidgets.QProgressBar()
        self.progressOverall.setTextVisible(False)
        self.progressOverall.setValue(24)

        self.groupAdvanced = QtWidgets.QGroupBox()
        self.groupAdvanced.setTitle("Details")

        self.textLog = QtWidgets.QPlainTextEdit()
        self.textLog.setReadOnly(True)

        self.buttonBox = QtWidgets.QDialogButtonBox()
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel)

        # creating layout
        layoutAdvanced = QtWidgets.QGridLayout()
        layoutAdvanced.setMargin(6)
        layoutAdvanced.addWidget(self.textLog, 0, 0)

        self.groupAdvanced.setLayout(layoutAdvanced)

        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(10)
        layout.addWidget(self.labelStatus)
        layout.addWidget(self.progressPartial)
        #layout.addWidget(self.labelTime)
        #layout.addWidget(self.labelOverall)
        #layout.addWidget(self.progressOverall)
        layout.addWidget(self.groupAdvanced)
        layout.addWidget(self.buttonBox)

        self.setLayout(layout)

        QtCore.QObject.connect(self.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel), QtCore.SIGNAL("clicked()"), self.reject)

class _InstallProgressDialog(_ProgressDialog):
    def __init__ (self, _parent_window):
        _ProgressDialog.__init__(self, _parent_window)
        self.progressPartial.setRange(0, 0)

class _InstallDialog(QtWidgets.QDialog):
    def __init__(self, _parent_window):
        QtWidgets.QDialog.__init__(self, _parent_window)

        self.resize(357, 174)

        self.labelText = QtWidgets.QLabel()
        self.labelText.setWordWrap(True)

        self.groupRequirements = QtWidgets.QGroupBox()
        self.groupRequirements.setTitle("requirements")

        self.textRequirements = QtWidgets.QPlainTextEdit()
        self.textRequirements.setReadOnly(True)

        self.buttonBox = QtWidgets.QDialogButtonBox()
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok)

        # creating layout
        layoutRequirements = QtWidgets.QGridLayout()
        layoutRequirements.setMargin(6)
        layoutRequirements.addWidget(self.textRequirements, 0, 0)

        self.groupRequirements.setLayout(layoutRequirements)

        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(10)
        layout.addWidget(self.labelText)
        layout.addWidget(self.groupRequirements)
        layout.addWidget(self.buttonBox)

        self.setLayout(layout)

        QtCore.QObject.connect(self.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel), QtCore.SIGNAL("clicked()"), self.reject)
        QtCore.QObject.connect(self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok), QtCore.SIGNAL("clicked()"), self.accept)

class _ProcessHandler(QtCore.QObject):
    stream_type_stdout = 0
    stream_type_stderr = 1
    def __init__(self, q_processes):
        QtCore.QObject.__init__(self)
        self.pipeline_finished = False
        self.process_terminated = False
        self.current_process = 0

        self.q_processes = q_processes
        for q_process in q_processes:
            q_process.readyReadStandardOutput.connect(self.on_stdout_ready)
            q_process.readyReadStandardError.connect(self.on_stderr_ready)
            q_process.finished.connect(self.on_process_finished)

        self.start_current_process()

    def start_current_process(self):
        if (self.process_terminated):
            return
        self.q_process = self.q_processes[self.current_process]
        self.q_process.start()

    def terminate(self):
        self.process_terminated = True

    def on_process_finished(self, exit_code, exit_status):
        self.exit_code = exit_code

        if (self.current_process == len(self.q_processes) - 1 and exit_code == 0):
            self.on_pipeline_finished(exit_code, exit_status)
            return

        if (self.process_terminated):
            print('...terminated by the user', file = sys.stderr, flush = True)
            self.on_pipeline_finished(1, QtCore.QProcess.ExitStatus.NormalExit)
            return

        if (self.current_process == len(self.q_processes) - 1 and exit_code != 0):
            self.on_pipeline_finished(exit_code, exit_status)
            return

        self.current_process += 1
        self.start_current_process()

    def on_pipeline_finished(self, exit_code, exit_status):
        self.pipeline_finished = True
        self.exit_code = exit_code

    def write(self, log, stream_type):
        print(log, end = '', flush = True, file = sys.stderr if stream_type == self.stream_type_stderr else sys.stdout)

    def on_stdout_ready(self):
        log = str(self.q_process.readAllStandardOutput(), 'utf-8', errors='ignore')
        self.write(log, self.stream_type_stdout)

    def on_stderr_ready(self):
        log = str(self.q_process.readAllStandardError(), 'utf-8', errors='ignore')
        self.write(log, self.stream_type_stderr)

def _process_events():
    _app = QtWidgets.QApplication.instance()
    _app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 1000)

class _ProcessProgress(_ProcessHandler):
    def __init__(self, q_processes):
        _ProcessHandler.__init__(self, q_processes)
        self.progress_dialog = _InstallProgressDialog(_parent_window)
        self.progress_dialog.rejected.connect(self.terminate)

    def terminate(self):
        super().terminate()
        if (self.pipeline_finished):
            return
        if (os.name == 'nt'): # if windows
            self.q_process.kill()
        else:
            self.q_process.terminate()

    def on_pipeline_finished(self, exit_code, exit_status):
        super().on_pipeline_finished(exit_code, exit_status)
        if (self.process_terminated):
            return
        if (exit_code == 0):
            self.progress_dialog.accept()
        else:
            self.progress_dialog.reject()

    def exec(self):
        result = self.progress_dialog.exec()
        while(self.pipeline_finished != True):
           time.sleep(0.03)
           _process_events()
        return result

    def write(self, log, stream_type):
        super().write(log, stream_type)

        _app = QtWidgets.QApplication.instance()

        scroll_bar		= self.progress_dialog.textLog.verticalScrollBar()
        scroll_to_end	= (scroll_bar.value() == scroll_bar.maximum())

        cursor = QtGui.QTextCursor(self.progress_dialog.textLog.document())
        cursor.movePosition(QtGui.QTextCursor.End)

        format = self.progress_dialog.textLog.currentCharFormat()
        if (stream_type == self.stream_type_stderr):
            format.setForeground(QtGui.QColor(163, 21, 21))
        else:
            format.setForeground(_app.palette().color(QtGui.QPalette.Text))
        cursor.setCharFormat(format)

        cursor.insertText(log)

        if (scroll_to_end):
            scroll_bar.setValue(scroll_bar.maximum())
        _process_events()
        # scroll bar value may be updated after process_events
        if (scroll_to_end):
            scroll_bar.setValue(scroll_bar.maximum())

def _is_already_installed(requirements_txt):
    installed_requirements = []

    try:
        installed_requirements_file = open(_installed_requirements_path, "r")
        installed_requirements = json.load(installed_requirements_file)
        installed_requirements_file.close()
    except:
        pass

    requirements_hash = hashlib.md5(requirements_txt.encode('utf-8')).hexdigest()
    if (requirements_hash in installed_requirements):
        return True
    return False

def _pip_ask_install(requirements_txt, script_name = ""):
    """Ask user to install python dependencies."""

    dialog = _InstallDialog(_parent_window)
    dialog.setWindowTitle("Install script dependencies")
    if script_name:
        dialog.labelText.setText('Following "' + script_name + '" script dependencies are going to be installed from the internet:')
    else:
        dialog.labelText.setText('Following script dependencies are going to be installed from the internet:')
    dialog.textRequirements.setPlainText(requirements_txt)

    if (not dialog.exec()):
        return False

    return True

def pip_install(requirements_txt, *, reinstall = False, ask = True):
    """
    Install python dependencies. Skip installation if called second time with the same requirements_txt
    :param requirements_txt: requirements passed to the pip install --requirement flag
    :param reinstall: force install (ignore previously installed requirements)
    :param ask: ask user before installing python dependencies.
    """

    _mkdirs()

    requirements_txt = requirements_txt.strip()

    already_installed = _is_already_installed(requirements_txt)
    if (not reinstall and already_installed):
        return True

    script_name = ""
    stack = inspect.stack()
    if (len(stack) >= 2):
        filename = stack[1][1]
        if (filename[-3:] == '.py'):
            script_name = Path(filename).stem

    if (ask):
        if (not _pip_ask_install(requirements_txt, script_name)):
            raise Exception("Failed to install requirements")

    if (script_name):
        print('Installing "' + script_name + '" requirements...', flush = True)
    else:
        print('Installing requirements...', flush = True)

    requirements_file_name = "requirements.txt"
    if (script_name):
        requirements_file_name = "requirements_" + script_name + ".txt"
    current_requirements_path = os.path.join(_user_packages_location, requirements_file_name)
    current_requirements_file = open(current_requirements_path, "w")
    current_requirements_file.write(requirements_txt)
    current_requirements_file.close()

    if platform.system() == 'Linux' or platform.system() == 'Darwin':
        python_executable = os.path.join(sys.exec_prefix, 'bin/python' + str(sys.version_info.major) + '.' + str(sys.version_info.minor))
    elif platform.system() == 'Windows':
        python_executable = os.path.join(sys.exec_prefix, 'python.exe')

    env = QtCore.QProcessEnvironment.systemEnvironment()
    env.insert("PYTHONUSERBASE", _user_packages_location)

    q_pip_process = QtCore.QProcess()
    q_pip_process.setProgram(python_executable)
    q_pip_process.setProcessEnvironment(env)
    q_pip_process.setArguments(['-m', 'pip', 'install', '--disable-pip-version-check', '--no-warn-script-location', '--user', '--upgrade', 'pip'])

    q_dep_process = QtCore.QProcess()
    q_dep_process.setProgram(python_executable)
    q_dep_process.setProcessEnvironment(env)
    q_dep_process.setArguments(['-m', 'pip', 'install', '--disable-pip-version-check', '--no-warn-script-location', '--user', '--requirement', current_requirements_path])

    process_progress = _ProcessProgress([q_pip_process, q_dep_process])
    if (not process_progress.exec()):
        notification = QtWidgets.QMessageBox(_parent_window)
        notification.setText("Failed to install script dependencies")
        notification.exec()
        raise Exception("Failed to install requirements")

    if (not already_installed):
        installed_requirements = []

        try:
            installed_requirements_file = open(_installed_requirements_path, "r")
            installed_requirements = json.load(installed_requirements_file)
            installed_requirements_file.close()
        except:
            pass

        requirements_hash = hashlib.md5(requirements_txt.encode('utf-8')).hexdigest()

        installed_requirements.append(requirements_hash)
        installed_requirements_file = open(_installed_requirements_path, "w")
        json.dump(installed_requirements, installed_requirements_file)
        installed_requirements_file.close()

    print('Successfully installed requirements', flush = True)

    importlib.invalidate_caches()

    return True