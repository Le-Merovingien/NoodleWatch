import hashlib
import logging
import socket
import urllib.error
import urllib.request
from pathlib import Path

import cv2

log = logging.getLogger("printwatch")
URL = "https://webcam.connect.prusa3d.com/c/snapshot"


def empreinte_machine():
    """Empreinte stable de la camera : 32 caracteres hexadecimaux derives de l'identifiant de la machine."""
    try:
        base = Path("/etc/machine-id").read_text().strip()
    except OSError:
        base = socket.gethostname()
    return hashlib.sha256(("printwatch-" + base).encode()).hexdigest()[:32]


def jpeg(image_bgr, largeur_max=1920):
    """Image en JPEG (qualite 85), reduite a largeur_max ; None si l'encodage echoue."""
    h, w = image_bgr.shape[:2]
    if w > largeur_max:
        image_bgr = cv2.resize(image_bgr, (largeur_max, int(h * largeur_max / w)))
    ok, jpg = cv2.imencode(".jpg", image_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return jpg.tobytes() if ok else None


class PrusaConnect:
    def __init__(self, jeton, empreinte="", url=URL, delai=15.0, largeur_max=1920):
        self.jeton = jeton
        self.empreinte = empreinte or empreinte_machine()
        self.url = url
        self.delai = delai
        self.largeur_max = largeur_max

    def envoie(self, image_bgr):
        """Envoie une photo ; False (et un avertissement) si Prusa Connect ne l'accepte pas."""
        donnees = jpeg(image_bgr, self.largeur_max)
        if donnees is None:
            return False
        req = urllib.request.Request(self.url, data=donnees, method="PUT", headers={
            "Content-Type": "image/jpg", "token": self.jeton, "fingerprint": self.empreinte})
        try:
            with urllib.request.urlopen(req, timeout=self.delai) as r:
                return 200 <= r.status < 300
        except urllib.error.HTTPError as e:
            log.warning("Prusa Connect refuse la photo : HTTP %d", e.code)
        except (urllib.error.URLError, OSError) as e:
            log.warning("Prusa Connect injoignable : %s", e)
        return False
