import shutil
from os import listdir, makedirs, remove, rmdir
from pathlib import Path
from sys import platform
from urllib.request import urlretrieve

CONTRIB_PATH = Path(__file__).parent / "contrib"

if not CONTRIB_PATH.exists():
    makedirs(CONTRIB_PATH)

if not (CONTRIB_PATH / "filezilla").exists():
    print("Downloading Filezilla...")

    if platform == "win32":
        url = "https://github.com/dmcdo/jabberwocky-contrib/blob/master/win32filezilla.zip?raw=true"
        download_dest = CONTRIB_PATH / "download.zip"
        extract_dest = CONTRIB_PATH / "tmp/"
        final_dest = CONTRIB_PATH / "filezilla"
        urlretrieve(url, download_dest)
        shutil.unpack_archive(download_dest, extract_dest)
        shutil.move(extract_dest / listdir(extract_dest)[0], final_dest)
        rmdir(extract_dest)
        remove(download_dest)
    elif platform == "linux":
        url = "https://github.com/dmcdo/jabberwocky-contrib/blob/master/linuxfilezilla.tar.bz2?raw=true"
        download_dest = CONTRIB_PATH / "download.tar.bz2"
        extract_dest = CONTRIB_PATH / "tmp/"
        final_dest = CONTRIB_PATH / "filezilla"
        urlretrieve(url, download_dest)
        shutil.unpack_archive(download_dest, extract_dest)
        shutil.move(extract_dest / listdir(extract_dest)[0], final_dest)
        rmdir(extract_dest)
        remove(download_dest)
    elif platform == "darwin":
        url = "https://github.com/dmcdo/jabberwocky-contrib/blob/master/FileZilla_3.63.1_macosx-x86.app.tar.bz2?raw=true"
        download_dest = CONTRIB_PATH / "download.tar.bz2"
        extract_dest = CONTRIB_PATH / "filezilla"
        urlretrieve(url, download_dest)
        shutil.unpack_archive(download_dest, extract_dest)
        remove(download_dest)

else:
    print("Skipping Filezilla.")
