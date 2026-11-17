import argparse
import logging

from . import config, menage
from .connectlocal import CameraConnectLocal, ConnectLocal
from .detecteur import Detecteur
from .prusaconnect import PrusaConnect
from .prusalink import PrusaLink
from .source import Source
from .surveillance import surveille


def main():
    p = argparse.ArgumentParser(prog="printwatch",
                                description="Detection des spaghettis et pause par PrusaLink ou Prusa Connect local")
    p.add_argument("config", help="fichier INI (voir printwatch.ini.exemple)")
    p.add_argument("--verbeux", action="store_true")
    a = p.parse_args()
    logging.basicConfig(level=logging.DEBUG if a.verbeux else logging.INFO,
                        format=menage.FORMAT)
    c = config.lit(a.config)
    log = logging.getLogger("printwatch")
    if c.fichier:
        try:
            menage.journal(c.fichier, c.jours)
        except OSError as e:                         # pas de fichier : la surveillance continue sur la sortie standard
            log.warning("journal %s impossible : %s", c.fichier, e)
    detecteur = Detecteur(c.modele, c.materiel, c.seuil)
    log.info("modele %s sur %s, seuil %.2f, alerte a %d sur %d, pause %s", c.modele, c.materiel, c.seuil, c.n, c.m,
             "oui" if c.pause else "non (observation)")
    if c.api == "connect":
        imprimante = ConnectLocal(c.url_local, c.jeton_local, c.imprimante_local)
        log.info("imprimante : Prusa Connect local %s", imprimante.base)
    else:
        imprimante = PrusaLink(c.hote, c.utilisateur, c.mot_de_passe)
        log.info("imprimante : PrusaLink %s", imprimante.base)
    connect = None
    if c.camera_local:
        connect = CameraConnectLocal(c.url_local, c.jeton_local, c.camera_local)
        log.info("Prusa Connect local : une photo toutes les %d s, camera %s", c.intervalle_connect, c.camera_local)
    elif c.jeton:
        connect = PrusaConnect(c.jeton, c.empreinte, c.url_connect)
        log.info("Prusa Connect : une photo toutes les %d s, empreinte %s", c.intervalle_connect, connect.empreinte)
    source = Source(c.source)
    source.regle()                                   # exposition du capteur CSI de la boite
    try:
        surveille(c, imprimante, source, detecteur, connect)
    except KeyboardInterrupt:
        pass
    finally:
        source.ferme()


if __name__ == "__main__":
    main()
