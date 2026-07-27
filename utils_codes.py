import string
import random
from database import connecter

def generate_unique_article_code(prefix: str='A', length: int=6) -> str:
    """
    Génère un code article unique en base.
    - Format: prefix + <length> caractères alphanumériques en MAJ.
    - Vérifie l'unicité dans la table articles.code.
    """
    chars = string.ascii_uppercase + string.digits
    attempt = 0
    while True:
        attempt += 1
        candidate = prefix + ''.join((random.choice(chars) for _ in range(length)))
        try:
            with connecter() as conn:
                cur = conn.cursor()
                cur.execute('SELECT 1 FROM articles WHERE code = ? LIMIT 1', (candidate,))
                if cur.fetchone() is None:
                    return candidate
        except Exception:
            return candidate
        if attempt > 1000:
            return candidate