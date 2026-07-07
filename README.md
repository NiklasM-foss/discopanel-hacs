# DiscoPanel für Home Assistant

*Deutsch · [English](README.en.md)*

Eine benutzerdefinierte Home Assistant Integration (HACS-kompatibel) für
[DiscoPanel](https://github.com/nickheyer/discopanel), ein Verwaltungspanel für
modifizierte Minecraft-Server (Fabric, Forge, NeoForge, Paper, Vanilla und
mehr).

Die Integration bindet jeden von DiscoPanel verwalteten Minecraft-Server als
eigenes Gerät in Home Assistant ein. So kannst du deine Server direkt aus Home
Assistant heraus starten, stoppen und neu starten, Konsolenbefehle senden und
alle wichtigen Laufzeitwerte (Spielerzahl, TPS, CPU, RAM, Festplatte,
Weltgröße, Status, Latenz, MOTD) als Sensoren überwachen und in Automationen
verwenden.

## Was die Integration macht

DiscoPanel ist ein Manager für modifizierte Minecraft-Server. Diese Integration
spricht die lokale ConnectRPC-API von DiscoPanel an und legt für jeden Server
ein eigenes Home Assistant Gerät an. Die Daten werden lokal per Polling
abgefragt (iot_class `local_polling`), es findet keine Cloud-Kommunikation
statt.

## Funktionen

Pro Minecraft-Server werden folgende Entitäten angelegt:

- **Switch** (Ein/Aus): Server-Power-Schalter. Ein = Server läuft. Einschalten
  startet den Server, Ausschalten stoppt ihn.
- **Button** (Neustart): Startet den Server neu.
- **Sensoren:**
  - Status (Textwert, z. B. Running, Stopped, Starting; der rohe Enum-Wert
    liegt als Attribut bei)
  - Spieler online (mit Attributen für maximale Spielerzahl und Spielerliste)
  - TPS (Ticks pro Sekunde)
  - CPU-Auslastung (in Prozent)
  - RAM-Nutzung (in Bytes, Anzeige wahlweise in MB)
  - Festplattennutzung (in Bytes)
  - Weltgröße (in Bytes)
  - Latenz (Server List Ping, in Millisekunden, Diagnose)
  - Minecraft-Version (Diagnose)
  - MOTD (Diagnose)
- **Binary Sensoren:**
  - Läuft (device_class RUNNING, an wenn der Server läuft)
  - Erreichbar (device_class CONNECTIVITY, an wenn der Server per Server List
    Ping antwortet)

## Installation

### Über HACS (benutzerdefiniertes Repository)

1. In Home Assistant HACS öffnen.
2. Oben rechts auf das Drei-Punkte-Menü klicken und **Benutzerdefinierte
   Repositories** wählen.
3. Als Repository-URL folgendes eintragen:
   `https://github.com/niklasm-foss/discopanel-hacs`
4. Als Kategorie **Integration** wählen und auf **Hinzufügen** klicken.
5. Anschließend im HACS-Store nach **DiscoPanel** suchen und installieren.
6. Home Assistant neu starten.

### Manuelle Installation

1. Den Ordner `custom_components/discopanel` aus diesem Repository in dein Home
   Assistant Konfigurationsverzeichnis kopieren, sodass der Pfad
   `config/custom_components/discopanel/` entsteht.
2. Home Assistant neu starten.

## Einrichtung / Konfiguration

Nach der Installation die Integration über
**Einstellungen -> Geräte & Dienste -> Integration hinzufügen** einrichten und
nach **DiscoPanel** suchen. Im Dialog werden folgende Angaben abgefragt:

- **Host:** IP-Adresse oder Hostname deiner DiscoPanel-Instanz.
- **Port:** Standard `8080`.
- **SSL:** Aktivieren, wenn DiscoPanel über HTTPS erreichbar ist.
- **SSL-Zertifikat prüfen:** Nur relevant bei aktivem SSL. Bei
  selbstsignierten Zertifikaten kann die Prüfung deaktiviert werden.
- **API-Token:** Ein DiscoPanel API-Token (siehe unten).

### API-Token erstellen

Die Integration authentifiziert sich mit einem API-Token, das mit dem Präfix
`dp_` beginnt. So erstellst du eines:

1. Die DiscoPanel-Weboberfläche im Browser öffnen.
2. In den Bereich **API Tokens** (API-Tokens) navigieren.
3. Ein neues Token erstellen und den vollständigen Wert (beginnt mit `dp_`)
   kopieren.
4. Diesen Wert im Einrichtungsdialog der Integration in das Feld **API-Token**
   einfügen.

Das Token wird von der Integration unverändert als Bearer-Token verwendet.

### Optionen

Über **Konfigurieren** bei der eingerichteten Integration lässt sich das
Abfrageintervall (**scan_interval**) einstellen. Standard sind 30 Sekunden,
Minimum 10 Sekunden.

## Dienst: send_command

Die Integration registriert den Dienst `discopanel.send_command`, mit dem du
einen Konsolenbefehl an einen Server sendest.

Felder:

- `server_id` (erforderlich): Die ID des Ziel-Servers (wie von DiscoPanel
  vergeben).
- `command` (erforderlich): Der zu sendende Konsolenbefehl.
- `silent` (optional, Standard `true`): Wenn `true`, wird der Befehl still
  ausgeführt.

Beispiel:

```yaml
service: discopanel.send_command
data:
  server_id: "abc123"
  command: "say Hallo aus Home Assistant"
  silent: true
```

## Hinweise

- Die Integration fragt die DiscoPanel-API lokal per Polling ab
  (`local_polling`). Es gibt keine Cloud-Abhängigkeit.
- Laufzeitwerte wie CPU, RAM oder Spielerzahl sind meist nur verfügbar, wenn
  der Server läuft. Bei gestopptem Server können diese Sensoren leer bzw.
  unbekannt sein.
- Jeder Minecraft-Server erscheint als eigenes Gerät, alle Server hängen an
  einem gemeinsamen DiscoPanel-Hub-Gerät.

## Links

- Repository und Fehlermeldungen:
  https://github.com/niklasm-foss/discopanel-hacs
