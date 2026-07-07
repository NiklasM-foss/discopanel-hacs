# DiscoPanel

Home Assistant Integration für [DiscoPanel](https://github.com/nickheyer/discopanel),
einen Verwaltungspanel für modifizierte Minecraft-Server (Fabric, Forge,
NeoForge, Paper, Vanilla und mehr).

Jeder Minecraft-Server wird als eigenes Gerät eingebunden. Die Abfrage läuft
lokal per Polling, ohne Cloud.

## Funktionen

- **Switch** zum Starten und Stoppen des Servers
- **Button** für Neustart
- **Sensoren:** Status, Spieler online, TPS, CPU, RAM, Festplatte, Weltgröße,
  Latenz, Minecraft-Version, MOTD
- **Binary Sensoren:** Läuft, Erreichbar
- **Dienst** `discopanel.send_command` zum Senden von Konsolenbefehlen

## Einrichtung

Über **Einstellungen -> Geräte & Dienste -> Integration hinzufügen** nach
**DiscoPanel** suchen. Benötigt werden Host, Port (Standard `8080`), optional
SSL sowie ein API-Token (Präfix `dp_`), das in der DiscoPanel-Weboberfläche
unter **API Tokens** erstellt wird.
