"""Requête DNS minimale (type A) vers un serveur précis."""

from __future__ import annotations

import socket
import struct

TYPE_A = 1
CLASS_IN = 1
HEADER_SIZE = 12


class DnsProbe:
    """Interroge un serveur DNS en UDP, sans passer par le résolveur du poste."""

    def __init__(self, timeout: float = 3.0) -> None:
        """Initialise la sonde.

        Args:
            timeout: Délai de réponse en secondes.
        """
        self.timeout = timeout

    def resolve(self, server: str, name: str) -> list[str]:
        """Résout un nom en adresses IPv4 auprès d'un serveur donné.

        Args:
            server: IP du serveur DNS.
            name: Nom à résoudre.

        Returns:
            Les adresses trouvées (liste vide si le nom est inconnu).

        Raises:
            OSError: Si le serveur ne répond pas.
        """
        labels = b"".join(
            bytes([len(p)]) + p.encode() for p in name.rstrip(".").split(".")
        )
        query = struct.pack(">HHHHHH", 0x4C42, 0x0100, 1, 0, 0, 0)
        query += labels + b"\x00" + struct.pack(">HH", TYPE_A, CLASS_IN)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(self.timeout)
            sock.sendto(query, (server, 53))
            reply, _ = sock.recvfrom(512)
        return self._addresses(reply, len(query))

    @staticmethod
    def _addresses(reply: bytes, question_end: int) -> list[str]:
        """Extrait les enregistrements A d'une réponse.

        Args:
            reply: Réponse brute du serveur.
            question_end: Position de la fin de la section question.

        Returns:
            Les adresses IPv4 de la section réponse.
        """
        if len(reply) < HEADER_SIZE:
            return []
        answers = struct.unpack(">H", reply[6:8])[0]
        pos, found = question_end, []
        for _ in range(answers):
            while pos < len(reply) and reply[pos] != 0 and reply[pos] < 0xC0:
                pos += reply[pos] + 1
            pos += 2 if reply[pos] >= 0xC0 else 1
            kind, _, _, length = struct.unpack(">HHIH", reply[pos : pos + 10])
            pos += 10
            if kind == TYPE_A and length == 4:
                found.append(socket.inet_ntoa(reply[pos : pos + 4]))
            pos += length
        return found
