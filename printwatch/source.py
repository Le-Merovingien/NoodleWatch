import logging
import os
import re
import threading
import time
from pathlib import Path

import cv2

log = logging.getLogger("printwatch")


class Source:
    def __init__(self, source, ouvre=cv2.VideoCapture):
        self.fini = False
        p = Path(source)
        self._images = None
        self._cap = None
        self._flux = None
        if "!" in source:                           # pipeline GStreamer, meme avec rtspsrc location=rtsp://...
            self._flux = Flux(source, ouvre, api=cv2.CAP_GSTREAMER)
        elif "://" in source:                       # flux reseau : FFmpeg ou GStreamer, selon l'OpenCV installe
            self._flux = Flux(source, ouvre)
        elif p.is_dir():
            self._images = sorted(x for x in p.iterdir() if x.suffix.lower() in (".jpg", ".jpeg", ".png"))
            self._camera = False
        else:
            self._cap = ouvre(source, cv2.CAP_ANY)
            if not self._cap.isOpened():
                raise RuntimeError("impossible d'ouvrir la source d'images %s" % source)
            self._camera = not p.is_file()

    def lit(self):
        """Image BGR, ou None (fin d'un dossier ou d'une video : fini passe a True ; camera : image ratee)."""
        if self._flux is not None:
            return self._flux.lit()
        if self._images is not None:
            if not self._images:
                self.fini = True
                return None
            return cv2.imread(str(self._images.pop(0)))
        if self._camera:
            for _ in range(4):                      # vide le tampon : on veut l'image du moment, pas une ancienne
                self._cap.grab()
            ok, image = self._cap.retrieve()
        else:
            ok, image = self._cap.read()
            self.fini = not ok
        return image if ok else None

    def ferme(self):
        if self._flux is not None:
            self._flux.ferme()
        if self._cap is not None:
            self._cap.release()


class Flux:
    """Flux (reseau ou pipeline GStreamer) lu en continu dans un thread ; lit() rend l'image la plus recente, sans
    jamais bloquer. Entre deux analyses (5 s), un flux RTSP s'accumule dans les tampons du reseau et du decodeur : lu
    seulement au moment de l'analyse, il donnerait une image vieille de plusieurs secondes. Une camera qui ne livre
    plus rien donne None apres age_max secondes, au lieu de bloquer la surveillance. Reconnexion automatique si le
    flux coupe (camera redemarree, Wi-Fi). api : backend OpenCV (CAP_ANY : celui qui sait ouvrir l'URL)."""

    def __init__(self, url, ouvre=cv2.VideoCapture, api=cv2.CAP_ANY, age_max=10.0, attente=5.0):
        os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")    # TCP : pas d'image dechiree
        self.url = url
        self.api = api
        self.nom = re.sub(r"//[^/@]*@", "//", url)          # sans identifiants eventuels, pour le journal
        self.age_max = age_max                              # au-dela, l'image est perimee : lit() rend None
        self.attente = attente                              # pause avant de se reconnecter
        self._ouvre = ouvre
        self._image = None
        self._quand = 0.0
        self._verrou = threading.Lock()
        self._arret = threading.Event()
        self._thread = threading.Thread(target=self._boucle, name="flux", daemon=True)
        self._thread.start()

    def _boucle(self):
        while not self._arret.is_set():
            cap = self._ouvre(self.url, self.api)
            if cap.isOpened():
                log.info("flux %s ouvert", self.nom)
                while not self._arret.is_set():
                    ok, image = cap.read()
                    if not ok:
                        log.warning("flux %s coupe", self.nom)
                        break
                    with self._verrou:
                        self._image, self._quand = image, time.monotonic()
            else:
                log.warning("flux %s injoignable", self.nom)
            cap.release()
            self._arret.wait(self.attente)

    def lit(self):
        with self._verrou:
            if self._image is None or time.monotonic() - self._quand > self.age_max:
                return None
            return self._image.copy()

    def ferme(self):
        self._arret.set()
        self._thread.join(timeout=2.0)
