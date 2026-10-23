import json
import urllib.error
import urllib.request


class ErreurImprimante(Exception):
    pass


class PrusaLink:
    def __init__(self, hote, utilisateur, mot_de_passe, delai=5.0):
        base = hote if hote.startswith("http") else "http://" + hote
        self.base = base.rstrip("/")
        mdp = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        mdp.add_password(None, self.base, utilisateur, mot_de_passe)
        self._ouvreur = urllib.request.build_opener(urllib.request.HTTPDigestAuthHandler(mdp))
        self.delai = delai

    def _requete(self, methode, chemin):
        req = urllib.request.Request(self.base + chemin, method=methode, data=b"" if methode == "PUT" else None)
        try:
            with self._ouvreur.open(req, timeout=self.delai) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, b""
        except (urllib.error.URLError, OSError) as e:
            raise ErreurImprimante("%s injoignable : %s" % (self.base, e)) from e

    def etat(self):
        """(etat, id du travail ou None). Etats PrusaLink : IDLE, BUSY, PRINTING, PAUSED, FINISHED, STOPPED, ERROR,
        ATTENTION, READY."""
        code, corps = self._requete("GET", "/api/v1/status")
        if code == 401:
            raise ErreurImprimante("mot de passe PrusaLink refuse")
        if code != 200:
            raise ErreurImprimante("statut : HTTP %d" % code)
        d = json.loads(corps)
        return d["printer"]["state"], (d.get("job") or {}).get("id")

    def pause(self, travail):
        """Met le travail en pause ; False s'il n'etait plus en cours (HTTP 409)."""
        code, _ = self._requete("PUT", "/api/v1/job/%d/pause" % travail)
        if code == 409:
            return False
        if code != 204:
            raise ErreurImprimante("pause : HTTP %d" % code)
        return True
