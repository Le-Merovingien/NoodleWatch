from collections import deque


class Filtre:
    def __init__(self, n, m):
        self.n = n
        self._fenetre = deque(maxlen=m)

    def ajoute(self, vu):
        """Ajoute le resultat d'une image ; True si l'alerte est confirmee."""
        self._fenetre.append(bool(vu))
        return sum(self._fenetre) >= self.n

    def vide(self):
        self._fenetre.clear()

    @property
    def compte(self):
        return sum(self._fenetre)
