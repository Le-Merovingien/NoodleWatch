import logging
import time

from . import alerte
from .filtre import Filtre
from .prusalink import ErreurImprimante

log = logging.getLogger("printwatch")


def surveille(c, imprimante, source, detecteur, dormir=time.sleep):
    """Tourne jusqu'a la fin de la source (dossier ou video d'essai) ; une camera ne finit jamais."""
    filtre = Filtre(c.n, c.m)
    etat_precedent = None
    while True:
        try:
            etat, travail = imprimante.etat()
        except ErreurImprimante as e:
            log.warning("%s", e)
            filtre.vide()
            dormir(c.intervalle_repos)
            continue
        if etat != etat_precedent:
            log.info("imprimante : %s", etat)
            etat_precedent = etat
        if etat != "PRINTING":
            filtre.vide()
            dormir(c.intervalle_repos)
            continue
        image = source.lit()
        if image is None:
            if source.fini:
                log.info("fin des images")
                return
            log.warning("image ratee")
            dormir(c.intervalle)
            continue
        detections = detecteur.detecte(image)
        confirme = filtre.ajoute(bool(detections))
        log.info("spaghetti %s (%s), %d/%d" % (
            "oui" if detections else "non", ", ".join("%.2f" % d.score for d in detections) or "-",
            filtre.compte, c.n))
        if confirme:
            chemin = alerte.enregistre(image, detections, c.dossier)
            log.warning("ALERTE : spaghetti confirme, image %s", chemin)
            if c.pause and travail is not None:
                try:
                    log.warning("pause du travail %d : %s", travail,
                                "faite" if imprimante.pause(travail) else "deja arrete")
                except ErreurImprimante as e:
                    log.error("pause impossible : %s", e)
            alerte.sonne(c.commande)
            filtre.vide()
        dormir(c.intervalle)
