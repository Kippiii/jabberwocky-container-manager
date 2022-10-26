import paramiko
import subprocess
from typing import Optional


class SSHInterface:
    host: str
    user: str
    port: int
    passwd: str
    ssh_client: Optional[paramiko.SSHClient] = None
    ftp_client: Optional[paramiko.SFTPClient] = None

    def __init__(self, host: str, user: str, port: int, passwd: str):
        self.host = host
        self.user = user
        self.port = port
        self.passwd = passwd

    def open_all(self):
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(
            paramiko.MissingHostKeyPolicy())
        self.ssh_client.connect(hostname=self.host, username=self.user,
                                port=self.port, password=self.passwd)
        self.ftp_client = self.ssh_client.open_sftp()

    def put(self, local_file_path: str, remote_file_path: str):
        self.ftp_client.put(local_file_path, remote_file_path)

    def get(self, remote_file_path: str, local_file_path: str):
        self.ftp_client.get(remote_file_path, local_file_path)

    def exec_ssh_command(self, cli: list):
        _CMD = [
            'ssh',
            '-oStrictHostKeyChecking=no',
            '-oLogLevel=ERROR',
            '-oPasswordAuthentication=no',
            '-p',
            str(self.port),
            f'{self.user}@{self.host}',
            *cli
        ]

        print(f'Executing {" ".join(_CMD)}')

        completed_process = subprocess.run(_CMD)

        if completed_process.returncode:
            raise RuntimeError(
                f'{_CMD[0]} exited with non-zero exit code {completed_process.returncode}. '
                'You may need to run [__update_hostkey__].')

    def exec_ssh_shell(self):
        self.exec_ssh_command([])

    def close_all(self):
        self.ftp_client.close()
        self.ssh_client.close()
        self.ssh_client = None
        self.ftp_client = None

    def __update_hostkey__(self):
        raise NotImplementedError('__update_hostkey__')
