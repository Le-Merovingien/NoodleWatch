import logging
import subprocess
import time
from pathlib import Path

import cv2

log = logging.getLogger("printwatch")


def enregistre(image, detections, dossier):
    d = Path(dossier)
    d.mkdir(parents=True, exist_ok=True)
    annotee = image.copy()
    for det in detections:
        cv2.rectangle(annotee, (int(det.x1), int(det.y1)), (int(det.x2), int(det.y2)), (0, 110, 250), 2)
        cv2.putText(annotee, "spaghetti %.2f" % det.score, (int(det.x1), max(int(det.y1) - 6, 12)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 110, 250), 1)
    chemin = d / time.strftime("alerte_%Y%m%d_%H%M%S.jpg")
    cv2.imwrite(str(chemin), annotee)
    return chemin


def sonne(commande):
    if not commande:
        return
    try:
        subprocess.run(commande, shell=True, timeout=30, check=True)
    except (subprocess.SubprocessError, OSError) as e:
        log.warning("commande d'alerte en echec : %s", e)
