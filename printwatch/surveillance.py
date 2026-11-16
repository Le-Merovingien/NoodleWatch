import logging
import time

from . import alerte, menage
from .filtre import Filtre
from .prusalink import ErreurImprimante

log = logging.getLogger("printwatch")


def surveille(c, imprimante, source, detecteur, connect=None, dormir=time.sleep, horloge=time.monotonic):
    """Tourne jusqu'a la fin de la source (dossier ou video d'essai) ; une camera ne finit jamais."""
    filtre = Filtre(c.n, c.m)
    precedent = None
    derniere_photo = None
    dernier_menage = None
    while True:
        try:
            etat, travail = imprimante.etat()
        except ErreurImprimante as e:
            log.warning("%s", e)
            filtre.vide()
            dormir(c.intervalle_repos)
            continue
        if etat != precedent:
            log.info("imprimante : %s", etat)
            if precedent == "PRINTING" and etat == "FINISHED":
                photo_de_fin(c, source, connect)
            if etat == "PRINTING" and precedent is not None and hasattr(source, "regle"):
                try:
                    source.regle()
                except Exception as e:                      # un reglage rate ne doit pas arreter la surveillance
                    log.warning("reglage du capteur impossible : %s", e)
            precedent = etat
        if etat != "PRINTING":
            filtre.vide()
            derniere_photo = None
            if dernier_menage is None or horloge() - dernier_menage >= 3600:
                dernier_menage = horloge()
                try:
                    menage.purge(c.dossier, c.jours)
                except Exception as e:                  # le menage ne doit jamais arreter la surveillance
                    log.warning("menage impossible : %s", e)
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
        if connect is not None and (derniere_photo is None or horloge() - derniere_photo >= c.intervalle_connect):
            connect.envoie(image)
            derniere_photo = horloge()
        detections = detecteur.detecte(image)
        confirme = filtre.ajoute(bool(detections))
        log.info("spaghetti %s (%s), %d/%d", "oui" if detections else "non",
                 ", ".join("%s %.2f" % (d.nom, d.score) for d in detections) or "-", filtre.compte, c.n)
        if confirme:
            annotee = alerte.annote(image, detections)
            log.warning("ALERTE : spaghetti confirme, image %s", alerte.enregistre(annotee, c.dossier, "alerte"))
            if c.pause and travail is not None:
                try:
                    log.warning("pause du travail %d : %s", travail,
                                "faite" if imprimante.pause(travail) else "deja arrete")
                except ErreurImprimante as e:
                    log.error("pause impossible : %s", e)
            if connect is not None:
                connect.envoie(annotee)
            alerte.sonne(c.commande)
            filtre.vide()
        dormir(c.intervalle)


def photo_de_fin(c, source, connect):
    """Photo de l'impression terminee : gardee en local et envoyee a Prusa Connect (pour poster le make)."""
    image = source.lit()
    if image is None:
        return
    log.info("photo de fin : %s", alerte.enregistre(image, c.dossier, "fin"))
    if connect is not None:
        connect.envoie(image)
