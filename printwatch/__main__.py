import argparse
import logging

from . import config
from .detecteur import Detecteur
from .prusaconnect import PrusaConnect
from .prusalink import PrusaLink
from .source import Source
from .surveillance import surveille


def main():
    p = argparse.ArgumentParser(prog="printwatch", description="Detection des spaghettis et pause PrusaLink")
    p.add_argument("config", help="fichier INI (voir printwatch.ini.exemple)")
    p.add_argument("--verbeux", action="store_true")
    a = p.parse_args()
    logging.basicConfig(level=logging.DEBUG if a.verbeux else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    c = config.lit(a.config)
    log = logging.getLogger("printwatch")
    detecteur = Detecteur(c.modele, c.materiel, c.seuil)
    log.info("modele %s sur %s, seuil %.2f, alerte a %d sur %d, pause %s", c.modele, c.materiel, c.seuil, c.n, c.m,
             "oui" if c.pause else "non (observation)")
    connect = PrusaConnect(c.jeton, c.empreinte, c.url_connect) if c.jeton else None
    if connect is not None:
        log.info("Prusa Connect : une photo toutes les %d s, empreinte %s", c.intervalle_connect, connect.empreinte)
    source = Source(c.source)
    try:
        surveille(c, PrusaLink(c.hote, c.utilisateur, c.mot_de_passe), source, detecteur, connect)
    except KeyboardInterrupt:
        pass
    finally:
        source.ferme()


if __name__ == "__main__":
    main()
