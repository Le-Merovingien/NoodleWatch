import logging
import logging.handlers
import time
from pathlib import Path

log = logging.getLogger("printwatch")
FORMAT = "%(asctime)s %(levelname)s %(message)s"
PREFIXES = ("alerte_", "fin_")                       # images ecrites par alerte.enregistre


def journal(fichier, jours):
    """Ajoute un journal fichier, tourne a minuit (heure locale) ; garde les jours derniers fichiers (0 : tous)."""
    Path(fichier).parent.mkdir(parents=True, exist_ok=True)
    h = logging.handlers.TimedRotatingFileHandler(fichier, when="midnight", backupCount=jours, encoding="utf-8")
    h.setFormatter(logging.Formatter(FORMAT))
    logging.getLogger().addHandler(h)
    return h


def purge(dossier, jours, maintenant=None):
    """Supprime de dossier les images d'alerte et de fin plus vieilles que jours (0 : jamais) ; renvoie leur nombre."""
    if jours <= 0:
        return 0
    limite = (time.time() if maintenant is None else maintenant) - jours * 86400
    n = 0
    for f in sorted(Path(dossier).glob("*.jpg")):
        if not f.name.startswith(PREFIXES):
            continue
        try:
            if f.stat().st_mtime < limite:
                f.unlink()
                n += 1
        except OSError as e:
            log.warning("menage : %s non supprime (%s)", f.name, e)
    if n:
        log.info("menage : %d image(s) de plus de %d jours supprimee(s)", n, jours)
    return n
