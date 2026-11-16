import glob
import logging
import subprocess
import time

log = logging.getLogger("printwatch")


def sous_peripherique(commande=subprocess.run, chemins=None):
    """Le /dev/v4l-subdevN du capteur (celui qui a analogue_gain), ou None."""
    for chemin in sorted(glob.glob("/dev/v4l-subdev*") if chemins is None else chemins):
        try:
            r = commande(["v4l2-ctl", "-d", chemin, "--list-ctrls"], capture_output=True, text=True, timeout=2,
                         check=False)
        except (OSError, subprocess.SubprocessError):
            continue
        if "analogue_gain" in (r.stdout or ""):
            return chemin
    return None


def regle(lit, sous_dev, commande=subprocess.run, dormir=time.sleep, cible=90, tolerance=20, essais=12):
    """Exposition manuelle, puis gain ajuste d'apres la luminosite moyenne (0-255) des images rendues par lit().
    Au mieux : un echec laisse le dernier gain. Renvoie la luminosite finale, ou None sans image."""
    def regle_ctrl(reglage):
        try:
            commande(["v4l2-ctl", "-d", sous_dev, "-c", reglage], capture_output=True, timeout=2, check=False)
        except (OSError, subprocess.SubprocessError) as e:
            log.warning("capteur : %s impossible (%s)", reglage, e)

    for reglage in ("white_balance_automatic=1", "auto_exposure=1", "gain_automatic=0", "exposure=500"):
        regle_ctrl(reglage)                               # auto_exposure=1 : mode manuel ; 500 : le maximum du capteur
    gain, gain_min, gain_max = 128, 16, 1023
    moyenne = None
    for _ in range(essais):
        regle_ctrl("analogue_gain=%d" % gain)
        dormir(0.5)                                       # un changement de gain met quelques images a arriver
        image = lit()
        if image is None:
            break
        moyenne = float(image.mean())
        if abs(moyenne - cible) <= tolerance or (moyenne < cible and gain >= gain_max) \
                or (moyenne > cible and gain <= gain_min):
            break
        gain = int(min(gain_max, max(gain_min, gain * min(4.0, max(0.5, cible / max(moyenne, 1.0))))))
    log.info("capteur %s : gain %d, luminosite moyenne %s", sous_dev, gain,
             "-" if moyenne is None else "%.0f" % moyenne)
    return moyenne
