import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class Detection:
    score: float
    x1: float          # pixels de l'image d'origine
    y1: float
    x2: float
    y2: float
    classe: int = 0    # indice dans modele.json -> classes
    nom: str = "spaghetti"


def letterbox(image_bgr, taille):
    """Image RGB float [0, 1], taille x taille, bandes grises (114) ; renvoie aussi (echelle, gauche, haut)."""
    image = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    h, w = image.shape[:2]
    echelle = min(taille / w, taille / h)
    reduite = cv2.resize(image, (int(w * echelle), int(h * echelle)))
    fond = np.full((taille, taille, 3), 114, dtype=np.uint8)
    haut, gauche = (taille - reduite.shape[0]) // 2, (taille - reduite.shape[1]) // 2
    fond[haut:haut + reduite.shape[0], gauche:gauche + reduite.shape[1]] = reduite
    return fond.astype(np.float32) / 255.0, (echelle, gauche, haut)


def decode(sortie, seuil, iou=0.45):
    """sortie [4 + classes, ancres], boites (cx, cy, w, h) normalisees. Renvoie [(score, classe, cx, cy, w, h)] apres
    NMS (toutes classes confondues : chaque classe declenche l'alerte)."""
    boites, conf, classe = sortie[:4].T, sortie[4:].max(0), sortie[4:].argmax(0)
    garde = conf >= seuil
    boites, conf, classe = boites[garde], conf[garde], classe[garde]
    x1, y1 = boites[:, 0] - boites[:, 2] / 2, boites[:, 1] - boites[:, 3] / 2
    x2, y2 = boites[:, 0] + boites[:, 2] / 2, boites[:, 1] + boites[:, 3] / 2
    aire = boites[:, 2] * boites[:, 3]
    ordre = conf.argsort()[::-1]
    res = []
    while len(ordre):
        i, reste = ordre[0], ordre[1:]
        res.append((float(conf[i]), int(classe[i]), *map(float, boites[i])))
        inter = (np.clip(np.minimum(x2[i], x2[reste]) - np.maximum(x1[i], x1[reste]), 0, None) *
                 np.clip(np.minimum(y2[i], y2[reste]) - np.maximum(y1[i], y1[reste]), 0, None))
        ordre = reste[inter / np.maximum(aire[i] + aire[reste] - inter, 1e-9) <= iou]
    return res


class Detecteur:
    def __init__(self, dossier, materiel="npu", seuil=0.18):
        d = Path(dossier)
        self.meta = json.loads((d / "modele.json").read_text())
        self.taille = self.meta["taille"]
        self.seuil = seuil
        self.duree_ms = 0.0
        if materiel == "tflite":
            from ai_edge_litert.interpreter import Interpreter
            self._interp = Interpreter(model_path=str(d / self.meta["tflite"]))
            self._interp.allocate_tensors()
            self._entree = self._interp.get_input_details()[0]["index"]
            self._sortie = self._interp.get_output_details()[0]["index"]
            self._infere = self._infere_tflite
        else:
            from torq.runtime import VMFBInferenceRunner
            self._runner = VMFBInferenceRunner(d / self.meta["vmfb"], device_uri="torq",
                                               torq_hw_type="astra_machina" if materiel == "npu" else "sim")
            self._infere = self._infere_vmfb

    def _infere_tflite(self, q):
        self._interp.set_tensor(self._entree, q)
        self._interp.invoke()
        return self._interp.get_tensor(self._sortie)

    def _infere_vmfb(self, q):
        sortie = self._runner.infer([q])[0]
        self.duree_ms = self._runner.infer_time_ms
        return np.asarray(sortie)

    def detecte(self, image_bgr):
        x, (echelle, gauche, haut) = letterbox(image_bgr, self.taille)
        se, ze = self.meta["entree"]
        q = np.clip(np.round(x / se + ze), -128, 127).astype(np.int8)[None]
        brut = self._infere(q).reshape(self.meta["forme_sortie"])
        ss, zs = self.meta["sortie"]
        sortie = (brut.astype(np.float32) - zs) * ss
        if self.meta["transposee"]:                     # onnx2tf peut sortir [1, ancres, canaux]
            sortie = sortie.transpose(0, 2, 1)
        res = []
        noms = self.meta["classes"]
        for score, classe, cx, cy, w, h in decode(sortie[0], self.seuil):
            px = lambda u, decal: (u * self.taille - decal) / echelle   # noqa: E731
            res.append(Detection(score, px(cx - w / 2, gauche), px(cy - h / 2, haut),
                                 px(cx + w / 2, gauche), px(cy + h / 2, haut),
                                 classe, noms[classe] if classe < len(noms) else str(classe)))
        return res
