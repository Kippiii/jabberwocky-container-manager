import shutil
from pathlib import Path
from urllib.request import urlretrieve
from sys import platform
from os import listdir, rmdir, remove, makedirs

CONTRIB_PATH = Path(__file__).parent / "contrib"

if not CONTRIB_PATH.exists():
    makedirs(CONTRIB_PATH)

if not (CONTRIB_PATH / "filezilla").exists():
    print("Downaloding Filezilla...")

    if platform == "win32":
        url = "https://github.com/dmcdo/jabberwocky-contrib/blob/master/win32filezilla.zip?raw=true"
        downlaod_dest = CONTRIB_PATH / "download.zip"
        extract_dest = CONTRIB_PATH / "tmp/"
        final_dest = CONTRIB_PATH / "filezilla"
        urlretrieve(url, downlaod_dest)
        shutil.unpack_archive(downlaod_dest, extract_dest)
        shutil.move(extract_dest / listdir(extract_dest)[0], final_dest)
        rmdir(extract_dest)
        remove(downlaod_dest)
    elif platform == "linux":
        url = "https://github.com/dmcdo/jabberwocky-contrib/blob/master/linuxfilezilla.tar.bz2?raw=true"
        downlaod_dest = CONTRIB_PATH / "download.tar.bz2"
        extract_dest = CONTRIB_PATH / "tmp/"
        final_dest = CONTRIB_PATH / "filezilla"
        urlretrieve(url, downlaod_dest)
        shutil.unpack_archive(downlaod_dest, extract_dest)
        shutil.move(extract_dest / listdir(extract_dest)[0], final_dest)
        rmdir(extract_dest)
        remove(downlaod_dest)
    elif platform == "darwin":
        url = "https://github.com/dmcdo/jabberwocky-contrib/blob/master/FileZilla_3.63.1_macosx-x86.app.tar.bz2?raw=true"
        downlaod_dest = CONTRIB_PATH / "download.tar.bz2"
        extract_dest = CONTRIB_PATH / "filezilla"
        urlretrieve(url, downlaod_dest)
        shutil.unpack_archive(downlaod_dest, extract_dest)
        remove(downlaod_dest)

else:
    print("Skipping Filezilla.")
