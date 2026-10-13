# Audit E007 (Train échoué) — verdict : REJECT (confirmé)
- Protocole et code commités en c0135f1 (« avant tout R ») ; train.json/status après. Aucun changement de critère depuis (git log protocol.md : 1 seul commit).
- Code relu (e007.py) : signal = clôture mid de la dernière minute < instant (mid_at), ATR H1 décalé de +1 h (disponible à la fin de la barre), variante B utilise shift(1) sur 20 signaux : pas de look-ahead. Sortie ≤ 21:00 UTC, DST via zoneinfo. Aucun bug pouvant fabriquer l'échec.
- Chiffres cohérents : n=371 (≥300 comptés avant), moyenne -0,012 R, t=-0,35, IC95 par jour [-0,296 ; +0,240], -1,13 pip net, 13 % de stops. Pas de signal, pas seulement un manque de puissance.
- validation.json et oos.json = {"skipped": "Train échoué"} : non lus, OOS vierge intact.
- Réserve mineure : comptage des placebos ±5..±8 h incomplet (0 trade pour +6..+8), sans effet puisque le critère 1 échoue.
Archiver. Pas de RETEST (ce serait du micro-réglage, règle 7).
