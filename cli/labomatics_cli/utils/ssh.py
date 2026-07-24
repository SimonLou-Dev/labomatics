"""SSH client pour se connecter à la VM et exécuter des commandes."""

import paramiko
from pathlib import Path
from typing import Optional


class SSHClient:
    """Client SSH simple."""

    def __init__(self, host: str, user: str, password: Optional[str] = None, 
                 key_filename: Optional[str] = None, port: int = 22, timeout: int = 10):
        """Initialiser le client SSH."""
        self.host = host
        self.user = user
        self.password = password
        self.key_filename = key_filename
        self.port = port
        self.timeout = timeout
        self.client = None

    def connect(self) -> None:
        """Se connecter au serveur SSH."""
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        self.client.connect(
            self.host,
            port=self.port,
            username=self.user,
            password=self.password,
            key_filename=self.key_filename,
            timeout=self.timeout,
            look_for_keys=False,
            allow_agent=False,
        )

    def disconnect(self) -> None:
        """Se déconnecter."""
        if self.client:
            self.client.close()

    def exec_command(self, command: str) -> tuple[str, str, int]:
        """Exécuter une commande et retourner stdout, stderr, return code."""
        if not self.client:
            raise RuntimeError("Not connected")
        
        stdin, stdout, stderr = self.client.exec_command(command, timeout=self.timeout)
        exit_code = stdout.channel.recv_exit_status()
        return stdout.read().decode(), stderr.read().decode(), exit_code

    def put_file(self, local_path: str, remote_path: str) -> None:
        """Uploader un fichier."""
        if not self.client:
            raise RuntimeError("Not connected")
        sftp = self.client.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()

    def get_file(self, remote_path: str, local_path: str) -> None:
        """Downloader un fichier."""
        if not self.client:
            raise RuntimeError("Not connected")
        sftp = self.client.open_sftp()
        sftp.get(remote_path, local_path)
        sftp.close()
