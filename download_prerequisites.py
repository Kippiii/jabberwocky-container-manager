import shutil
from pathlib import Path
from urllib.request import urlretrieve
from sys import platform
from os import listdir, rmdir, remove

CONTRIB_PATH = Path(__file__).parent

if not (CONTRIB_PATH / "filezilla/").exists():
    print("Downaloding Filezilla...")

    if platform == "win32":
        url = "https://dl3.cdn.filezilla-project.org/client/FileZilla_3.63.1_win64.zip?h=ANIvQYbsJsgefHI_ff-mXA&x=1674844216"
        downlaod_dest = CONTRIB_PATH / "download.zip"
        extract_dest = CONTRIB_PATH / "tmp/"
        final_dest = CONTRIB_PATH / "filezilla/"
        urlretrieve(url, downlaod_dest)
        shutil.unpack_archive(downlaod_dest, extract_dest)
        shutil.move(extract_dest / listdir(extract_dest)[0], final_dest)
        rmdir(extract_dest)
        remove(downlaod_dest)
    elif platform == "linux":
        url = "https://dl3.cdn.filezilla-project.org/client/FileZilla_3.63.1_x86_64-linux-gnu.tar.bz2?h=S3DdlU_RmKhMSSW2MH14bA&x=1674844216"
        downlaod_dest = CONTRIB_PATH / "download.tar.bz2"
        extract_dest = CONTRIB_PATH / "tmp/"
        final_dest = CONTRIB_PATH / "filezilla/"
        urlretrieve(url, downlaod_dest)
        shutil.unpack_archive(downlaod_dest, extract_dest)
        shutil.move(extract_dest / listdir(extract_dest)[0], final_dest)
        rmdir(extract_dest)
        remove(downlaod_dest)

else:
    print("Skipping Filezilla.")
