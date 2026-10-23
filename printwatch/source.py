from pathlib import Path

import cv2


class Source:
    def __init__(self, source):
        self.fini = False
        p = Path(source)
        self._images = None
        self._cap = None
        if p.is_dir():
            self._images = sorted(x for x in p.iterdir() if x.suffix.lower() in (".jpg", ".jpeg", ".png"))
            self._camera = False
        else:
            self._cap = cv2.VideoCapture(source, cv2.CAP_GSTREAMER if "!" in source else cv2.CAP_ANY)
            if not self._cap.isOpened():
                raise RuntimeError("impossible d'ouvrir la source d'images %s" % source)
            self._camera = not p.is_file()

    def lit(self):
        """Image BGR, ou None (fin d'un dossier ou d'une video : fini passe a True ; camera : image ratee)."""
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
        if self._cap is not None:
            self._cap.release()
