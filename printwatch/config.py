import configparser
from dataclasses import dataclass
from pathlib import Path

ICI = Path(__file__).resolve().parent


@dataclass
class Config:
    # [imprimante] api : prusalink (l'imprimante directement) ou connect (serveur Prusa Connect local, [connect_local])
    api: str = "prusalink"
    # PrusaLink : utilisateur "maker", mot de passe affiche dans les reglages reseau de l'imprimante
    hote: str = ""
    utilisateur: str = "maker"
    mot_de_passe: str = ""
    pause: bool = True                 # False : mode observation, alerte sans mettre en pause
    # [camera]
    # pipeline GStreamer de Synaptics pour la camera de la carte ; aussi : flux rtsp://, peripherique V4L2, video, dossier
    source: str = ("v4l2src device=/dev/video0 ! video/x-raw ! videoconvert ! video/x-raw,format=BGR ! "
                   "appsink drop=true max-buffers=1")
    intervalle: float = 5.0            # secondes entre deux images pendant une impression
    intervalle_repos: float = 30.0     # secondes entre deux lectures d'etat hors impression
    # [detection]
    modele: str = str(ICI / "modele")  # dossier avec le .vmfb, le .tflite et modele.json
    materiel: str = "npu"              # npu (carte), sim (simulateur x86 du NPU), tflite (PC, rapide)
    seuil: float = 0.18                # score minimal d'une detection
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
    # [connect_local] serveur Prusa Connect local (cles url, jeton, imprimante, camera dans le fichier INI)
    url_local: str = ""                # adresse du serveur, ex. http://192.168.1.10:8080
    jeton_local: str = ""              # jeton d'API, portee operate
    imprimante_local: str = ""         # id de l'imprimante sur le serveur ; vide : la seule connue du serveur
    camera_local: str = ""             # nom d'une camera de type push sur le serveur ; vide : pas de photos
    # [journal]
    fichier: str = ""                  # journal tourne chaque nuit ; vide : sortie standard (journal systemd) seulement
    jours: int = 14                    # journaux tournes et images d'alerte ou de fin plus vieux : supprimes (0 : jamais)


SECTIONS = {
    "imprimante": ("api", "hote", "utilisateur", "mot_de_passe", "pause"),
    "camera": ("source", "intervalle", "intervalle_repos"),
    "detection": ("modele", "materiel", "seuil", "n", "m"),
    "alerte": ("commande", "dossier"),
    "prusa_connect": ("jeton", "empreinte", "url_connect", "intervalle_connect"),
    "connect_local": (("url", "url_local"), ("jeton", "jeton_local"), ("imprimante", "imprimante_local"),
                      ("camera", "camera_local")),
    "journal": ("fichier", "jours"),
}


def lit(chemin):
    p = configparser.ConfigParser(interpolation=None)
    if not p.read(chemin, encoding="utf-8"):
        raise FileNotFoundError(chemin)
    c = Config()
    for section, cles in SECTIONS.items():
        for cle in cles:
            cle, attribut = cle if isinstance(cle, tuple) else (cle, cle)     # cle du fichier, champ de Config
            if not p.has_option(section, cle):
                continue
            defaut = getattr(c, attribut)
            if isinstance(defaut, bool):
                val = p.getboolean(section, cle)
            elif isinstance(defaut, int):
                val = p.getint(section, cle)
            elif isinstance(defaut, float):
                val = p.getfloat(section, cle)
            else:
                val = p.get(section, cle)
            setattr(c, attribut, val)
    base = Path(chemin).resolve().parent             # chemins relatifs au fichier de configuration
    for cle in ("modele", "dossier", "fichier"):
        v = Path(getattr(c, cle))
        if getattr(c, cle) and not v.is_absolute():
            setattr(c, cle, str(base / v))
    if c.api not in ("prusalink", "connect"):
        raise ValueError("[imprimante] api : prusalink ou connect")
    if c.api == "prusalink" and not c.hote:
        raise ValueError("[imprimante] hote manquant")
    if (c.api == "connect" or c.camera_local) and not (c.url_local and c.jeton_local):
        raise ValueError("[connect_local] url et jeton manquants")
    if c.camera_local and c.jeton:
        raise ValueError("photos : [prusa_connect] jeton ou [connect_local] camera, pas les deux")
    if c.materiel not in ("npu", "sim", "tflite"):
        raise ValueError("[detection] materiel : npu, sim ou tflite")
    if not 1 <= c.n <= c.m:
        raise ValueError("[detection] il faut 1 <= n <= m")
    if c.jours < 0:
        raise ValueError("[journal] jours : 0 ou plus")
    return c
