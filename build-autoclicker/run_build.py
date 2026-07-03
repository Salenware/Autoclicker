import os
import PyInstaller.__main__
PyInstaller.__main__.run([
"--noconfirm",
"--clean",
"--onefile",
"--windowed",
"--name",
os.environ["APP_NAME"],
"--distpath",
os.environ["BAT_DIR"],
"--workpath",
os.environ["WORK"],
"--specpath",
os.environ["BUILD_ROOT"],
os.environ["SCRIPT"],
])
