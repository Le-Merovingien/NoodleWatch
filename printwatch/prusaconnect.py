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


class PrusaConnect:
    def __init__(self, jeton, empreinte="", url=URL, delai=15.0, largeur_max=1920):
        self.jeton = jeton
        self.empreinte = empreinte or empreinte_machine()
        self.url = url
        self.delai = delai
        self.largeur_max = largeur_max

    def envoie(self, image_bgr):
        """Envoie une photo ; False (et un avertissement) si Prusa Connect ne l'accepte pas."""
        h, w = image_bgr.shape[:2]
        if w > self.largeur_max:
            image_bgr = cv2.resize(image_bgr, (self.largeur_max, int(h * self.largeur_max / w)))
        ok, jpg = cv2.imencode(".jpg", image_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ok:
            return False
        req = urllib.request.Request(self.url, data=jpg.tobytes(), method="PUT", headers={
            "Content-Type": "image/jpg", "token": self.jeton, "fingerprint": self.empreinte})
        try:
            with urllib.request.urlopen(req, timeout=self.delai) as r:
                return 200 <= r.status < 300
        except urllib.error.HTTPError as e:
            log.warning("Prusa Connect refuse la photo : HTTP %d", e.code)
        except (urllib.error.URLError, OSError) as e:
            log.warning("Prusa Connect injoignable : %s", e)
        return False
