import logging
import subprocess
import time
from pathlib import Path

import cv2

log = logging.getLogger("printwatch")


def annote(image, detections):
    annotee = image.copy()
    for det in detections:
        cv2.rectangle(annotee, (int(det.x1), int(det.y1)), (int(det.x2), int(det.y2)), (0, 110, 250), 2)
        cv2.putText(annotee, "%s %.2f" % (det.nom, det.score), (int(det.x1), max(int(det.y1) - 6, 12)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 110, 250), 1)
    return annotee


def enregistre(image, dossier, prefixe):
    """Ecrit l'image dans dossier/prefixe_AAAAMMJJ_HHMMSS.jpg et renvoie le chemin."""
    d = Path(dossier)
    d.mkdir(parents=True, exist_ok=True)
    chemin = d / time.strftime(prefixe + "_%Y%m%d_%H%M%S.jpg")
    cv2.imwrite(str(chemin), image)
    return chemin


def sonne(commande):
    if not commande:
        return
    try:
        subprocess.run(commande, shell=True, timeout=30, check=True)
    except (subprocess.SubprocessError, OSError) as e:
        log.warning("commande d'alerte en echec : %s", e)
