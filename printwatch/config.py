import configparser
from dataclasses import dataclass
from pathlib import Path

ICI = Path(__file__).resolve().parent


@dataclass
class Config:
    # [imprimante] PrusaLink : utilisateur "maker", mot de passe affiche dans les reglages reseau de l'imprimante
    hote: str = ""
    utilisateur: str = "maker"
    mot_de_passe: str = ""
    pause: bool = True                 # False : mode observation, alerte sans mettre en pause
    # [camera]
    source: str = "/dev/video0"        # peripherique V4L2, pipeline GStreamer (avec "!"), fichier video ou dossier
    intervalle: float = 5.0            # secondes entre deux images pendant une impression
    intervalle_repos: float = 30.0     # secondes entre deux lectures d'etat hors impression
    # [detection]
    modele: str = str(ICI / "modele")  # dossier avec le .vmfb, le .tflite et modele.json
    materiel: str = "npu"              # npu (carte), sim (simulateur x86 du NPU), tflite (PC, rapide)
    seuil: float = 0.5                 # score minimal d'une detection
    n: int = 3                         # alerte quand n des m dernieres images contiennent un spaghetti
    m: int = 5
    # [alerte]
    commande: str = ""                 # commande shell lancee a l'alerte (buzzer, LED du HAT)
    dossier: str = "alertes"           # images annotees des alertes et photos de fin d'impression
    # [prusa_connect] option : photos envoyees a Prusa Connect, desactivee sans jeton
    jeton: str = ""
    empreinte: str = ""                # vide : derivee de l'identifiant de la machine
    url_connect: str = "https://webcam.connect.prusa3d.com/c/snapshot"
    intervalle_connect: float = 60.0


SECTIONS = {
    "imprimante": ("hote", "utilisateur", "mot_de_passe", "pause"),
    "camera": ("source", "intervalle", "intervalle_repos"),
    "detection": ("modele", "materiel", "seuil", "n", "m"),
    "alerte": ("commande", "dossier"),
    "prusa_connect": ("jeton", "empreinte", "url_connect", "intervalle_connect"),
}


def lit(chemin):
    p = configparser.ConfigParser(interpolation=None)
    if not p.read(chemin, encoding="utf-8"):
        raise FileNotFoundError(chemin)
    c = Config()
    for section, cles in SECTIONS.items():
        for cle in cles:
            if not p.has_option(section, cle):
                continue
            defaut = getattr(c, cle)
            if isinstance(defaut, bool):
                val = p.getboolean(section, cle)
            elif isinstance(defaut, int):
                val = p.getint(section, cle)
            elif isinstance(defaut, float):
                val = p.getfloat(section, cle)
            else:
                val = p.get(section, cle)
            setattr(c, cle, val)
    base = Path(chemin).resolve().parent             # chemins relatifs au fichier de configuration
    for cle in ("modele", "dossier"):
        v = Path(getattr(c, cle))
        if not v.is_absolute():
            setattr(c, cle, str(base / v))
    if not c.hote:
        raise ValueError("[imprimante] hote manquant")
    if c.materiel not in ("npu", "sim", "tflite"):
        raise ValueError("[detection] materiel : npu, sim ou tflite")
    if not 1 <= c.n <= c.m:
        raise ValueError("[detection] il faut 1 <= n <= m")
    return c
