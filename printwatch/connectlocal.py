import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from .prusaconnect import jpeg
from .prusalink import ErreurImprimante

log = logging.getLogger("printwatch")
REFUS_ETAT = ("/VERB_NOT_ALLOWED_IN_STATE", "/COMMAND_REJECTED")   # l'impression n'est plus en cours


def requete(base, jeton, methode, chemin, corps=None, type_corps="application/json", delai=5.0):
    """(code HTTP, reponse JSON ou None) ; ErreurImprimante si le serveur ne repond pas."""
    entetes = {"Authorization": "Bearer " + jeton, "Accept": "application/json"}
    if corps is not None:
        entetes["Content-Type"] = type_corps
        if type_corps == "application/json":
            corps = json.dumps(corps).encode()
    req = urllib.request.Request(base + chemin, data=corps, method=methode, headers=entetes)
    try:
        with urllib.request.urlopen(req, timeout=delai) as r:
            code, brut = r.status, r.read()
    except urllib.error.HTTPError as e:
        code, brut = e.code, e.read()
    except (urllib.error.URLError, OSError) as e:
        raise ErreurImprimante("Prusa Connect %s injoignable : %s" % (base, e)) from e
    try:
        return code, json.loads(brut) if brut else None
    except ValueError:
        return code, None


def base_url(url):
    base = url if url.startswith("http") else "http://" + url
    return base.rstrip("/")


class ConnectLocal:
    def __init__(self, url, jeton, imprimante="", delai=5.0):
        self.base = base_url(url)
        self.jeton = jeton
        self.imprimante = imprimante                 # id de l'imprimante sur le serveur ; vide : la seule connue
        self.delai = delai

    def _requete(self, methode, chemin, corps=None):
        code, d = requete(self.base, self.jeton, methode, chemin, corps, delai=self.delai)
        if code == 401:
            raise ErreurImprimante("jeton Prusa Connect refuse")
        if code == 403:
            raise ErreurImprimante("jeton Prusa Connect sans le droit necessaire (portee operate)")
        return code, d

    def _trouve_imprimante(self):
        code, d = self._requete("GET", "/api/v1/devices")
        if code != 200 or d is None:
            raise ErreurImprimante("liste des imprimantes : HTTP %d" % code)
        imprimantes = [i for i in d.get("items") or [] if i.get("kind", "printer") == "printer"]
        if len(imprimantes) != 1:
            noms = ", ".join("%s (%s)" % (i.get("name"), i.get("id")) for i in imprimantes) or "aucune"
            raise ErreurImprimante("[connect_local] imprimante a remplir, imprimantes connues : " + noms)
        self.imprimante = imprimantes[0]["id"]
        log.info("Prusa Connect : imprimante %s (%s)", imprimantes[0].get("name"), self.imprimante)

    def _chemin(self):
        if not self.imprimante:
            self._trouve_imprimante()
        return "/api/v1/devices/" + urllib.parse.quote(self.imprimante, safe="")

    def etat(self):
        """(etat, numero du travail ou None), avec les memes mots que PrusaLink (ceux du micrologiciel)."""
        code, d = self._requete("GET", self._chemin())
        if code == 404:
            raise ErreurImprimante("imprimante %s inconnue de Prusa Connect" % self.imprimante)
        if code != 200 or d is None:
            raise ErreurImprimante("etat : HTTP %d" % code)
        if d.get("departed"):
            raise ErreurImprimante("imprimante deconnectee de Prusa Connect")
        st = d.get("state") or {}
        etat, travail = st.get("/state"), st.get("/job/id")
        if etat is None:
            raise ErreurImprimante("etat de l'imprimante pas encore recu par Prusa Connect")
        if travail is None and etat in ("PRINTING", "PAUSED"):
            travail = 0                              # la pause de Connect ne prend pas de numero de travail
        return etat, travail

    def pause(self, travail):
        """Met l'impression en pause ; False si elle n'etait plus en cours."""
        code, d = self._requete("POST", self._chemin() + "/commands", {"verb": "core.command.pause_print"})
        if code == 200 and d is not None:
            if not d.get("ok"):
                log.warning("pause refusee par l'imprimante : %s", d.get("machine_reason") or "sans raison")
            return bool(d.get("ok"))
        if code == 409 and d is not None and str(d.get("code", "")).endswith(REFUS_ETAT):
            return False
        raise ErreurImprimante("pause : HTTP %d %s" % (code, (d or {}).get("code", "")))


class CameraConnectLocal:
    """Camera de type push declaree sur le serveur (page de l'imprimante > Cameras) : on lui envoie les photos."""

    def __init__(self, url, jeton, camera, delai=15.0, largeur_max=1920):
        self.base = base_url(url)
        self.jeton = jeton
        self.camera = camera
        self.delai = delai
        self.largeur_max = largeur_max

    def envoie(self, image_bgr):
        """Envoie une photo ; False (et un avertissement) si le serveur ne l'accepte pas."""
        donnees = jpeg(image_bgr, self.largeur_max)
        if donnees is None:
            return False
        chemin = "/api/v1/cameras/%s/snapshot" % urllib.parse.quote(self.camera, safe="")
        try:
            code, d = requete(self.base, self.jeton, "PUT", chemin, donnees, "image/jpeg", self.delai)
        except ErreurImprimante as e:
            log.warning("%s", e)
            return False
        if 200 <= code < 300:
            return True
        log.warning("Prusa Connect refuse la photo : HTTP %d %s", code, (d or {}).get("code", ""))
        return False
