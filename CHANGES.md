# Änderungen gegenüber dem Original

Dieser Fork basiert auf einem Projekt von Stephan Joubert
(Apache-2.0, vom Autor archiviert am 2026-10-20).

Ziel: Quelle dauerhaft verfügbar halten, voll kompatibel (gleiche interne Domain,
gleiche Entity-IDs) für Hybrid-Wechselrichter.

## Geänderte Dateien
- `custom_components/solarman/manifest.json`: Name, Links, Codeowners; `pysolarmanv5` auf >=3.0.0,<3.1 begrenzt.
- `hacs.json`: Name, README-Anzeige.
- `README.md`: Hinweisblock zum Fork.
- `CHANGES.md`: diese Datei.
- `custom_components/solarman/inverter_definitions/deye_sg04lp3_vollstaendig.yaml`: neues, generiertes Profil
  (70 bisherige Sensoren unveraendert + 104 neue Werte inkl. Einstellungen, Arbeitsmodus, Time-of-Use, rein lesend, aus deye_p3.yaml, MIT, siehe NOTICE). Gegen echtes Geraet geprueft.
- `tools/build_profile.py`: Generator fuer dieses Profil.
- `NOTICE`: Attribution.

## Hinweis (Apache-2.0 §4b)
Alle oben genannten Dateien wurden gegenueber dem Original geaendert. Die Git-Historie wurde am 2026-11-12 neu begonnen (Bereinigung von Markennamen); Urheber-/Lizenzhinweise bleiben in LICENSE und NOTICE erhalten.
