"""SSH client pour se connecter à la VM et exécuter des commandes."""

import paramiko
import time
from pathlib import Path
from typing import Optional


class SSHClient:
    """Client SSH avec upload/exec."""

    def __init__(self, host: str, user: str, password: Optional[str] = None,
                 key_filename: Optional[str] = None, port: int = 22, timeout: int = 30):
        """Initialiser le client SSH."""
        self.host = host
        self.user = user
        self.password = password
        self.key_filename = key_filename
        self.port = port
        self.timeout = timeout
        self.client = None

    def connect(self, retries: int = 5, delay: int = 2) -> None:
        """Se connecter au serveur SSH avec retry."""
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        for attempt in range(retries):
            try:
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
                return
            except (paramiko.SSHException, OSError) as e:
                if attempt < retries - 1:
                    time.sleep(delay)
                else:
                    raise

    def disconnect(self) -> None:
        """Se déconnecter."""
        if self.client:
            self.client.close()

    def exec_command(self, command: str, timeout: int = None) -> tuple[str, str, int]:
        """Exécuter une commande et retourner stdout, stderr, return code."""
        if not self.client:
            raise RuntimeError("Not connected")

        if timeout is None:
            timeout = self.timeout

        stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        return stdout.read().decode(), stderr.read().decode(), exit_code

    def exec_command_live(self, command: str) -> int:
        """Exécuter une commande et afficher output en temps réel."""
        if not self.client:
            raise RuntimeError("Not connected")

        stdin, stdout, stderr = self.client.exec_command(command)
        
        for line in stdout:
            print(line.rstrip())
        
        exit_code = stdout.channel.recv_exit_status()
        
        if exit_code != 0:
            for line in stderr:
                print(f"[err] {line.rstrip()}")
        
        return exit_code

    def put_file(self, local_path: str, remote_path: str) -> None:
        """Uploader un fichier."""
        if not self.client:
            raise RuntimeError("Not connected")
        
        sftp = self.client.open_sftp()
        try:
            sftp.put(local_path, remote_path)
        finally:
            sftp.close()

    def put_file_content(self, content: str, remote_path: str) -> None:
        """Créer un fichier avec du contenu."""
        if not self.client:
            raise RuntimeError("Not connected")
        
        sftp = self.client.open_sftp()
        try:
            with sftp.file(remote_path, "w") as f:
                f.write(content)
        finally:
            sftp.close()

    def get_file(self, remote_path: str, local_path: str) -> None:
        """Downloader un fichier."""
        if not self.client:
            raise RuntimeError("Not connected")
        
        sftp = self.client.open_sftp()
        try:
            sftp.get(remote_path, local_path)
        finally:
            sftp.close()

    def mkdir(self, remote_path: str) -> None:
        """Créer un répertoire."""
        if not self.client:
            raise RuntimeError("Not connected")
        
        sftp = self.client.open_sftp()
        try:
            try:
                sftp.stat(remote_path)
            except FileNotFoundError:
                sftp.mkdir(remote_path)
        finally:
            sftp.close()
