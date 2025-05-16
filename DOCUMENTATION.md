# ![Projektlogo](./logo.png)

# LF11: Rechnungsverwaltungssoftware

## Anwenderdokumentation & Entwicklungsdokumentation

---

## Inhaltsverzeichnis

1. [Deckblatt](#deckblatt)
2. [Projektübersicht](#projektübersicht)
3. [Inhaltsverzeichnis](#inhaltsverzeichnis)
4. [Anwenderdokumentation](#anwenderdokumentation)
    - [Einleitung](#einleitung)
    - [Funktionen](#funktionen)
    - [Installation](#installation)
    - [Konfiguration](#konfiguration)
    - [Benutzung](#benutzung)
    - [Screenshots](#screenshots)
    - [Fehlerbehebung](#fehlerbehebung)
    - [FAQ](#faq)
    - [Kontakt & Support](#kontakt--support)
5. [Entwicklungsdokumentation](#entwicklungsdokumentation)
    - [Architekturüberblick](#architekturüberblick)
    - [Projektstruktur](#projektstruktur)
    - [Entwicklungsumgebung einrichten](#entwicklungsumgebung-einrichten)
    - [Coding Guidelines](#coding-guidelines)
    - [Wichtige Module & Komponenten](#wichtige-module--komponenten)
    - [Datenbankschema](#datenbankschema)
    - [API-Endpunkte](#api-endpunkte)
    - [Tests](#tests)
    - [Deployment](#deployment)
    - [Changelog](#changelog)
    - [Beitragende & Beiträge](#beitragende--beiträge)
    - [Lizenz](#lizenz)

---

## Deckblatt

|                  |                               |
|------------------|-------------------------------|
| **Projekt:**     | Rechnungsverwaltungsssoftware |
| **Version:**     | A 1.1.1                       |
| **Datum:**       | 20205-05-16                   |
| **Autor:innen:** | Sebastian Große               |
| **Kontakt:**     | sebastian.grosse@grossese.de  |

---

## Projektübersicht

Der Auftrag des Kundens im Rahmen des Projektes ist es, eine Software zur Erstellung, Verwaltung und Archivierung von Rechnungen zu entwickeln. Ziel ist es dabei, eine benutzerfreundliche Anwendung mit grafischer Oberfläche zu realisieren, die zur Rechnungserstellung dient. Hierbei werden die Daten in einer Datenbank gespeichert und bereitgestellt. Diese bildet somit die Grundlage für das Erfassen, Anzeigen und Bearbeiten von Informationen innerhalb des Programms.
Eine charakteristische Funktion der Anwendung besteht in der Möglichkeit, Rechnungen direkt über die Software zu drucken. Dafür soll eine integrierte Druckvorschau realisiert werden, die dem Benutzer einen optischen Kontrollgang über die Rechnung vor dem eigentlichen Ausdruck ermöglicht. Zusätzlich soll eine automatisierte Archivierung der Rechnungen im PDF- und XML-Dateiformat erfolgen. Diese sollen in einem Ordner komprimiert (.zip) und verschlüsselt im Speichersystem abgelegt werden.
Technologisch basiert das System auf einer SQL-Datenbank zur strukturierten Speicherung der Daten. Darüber hinaus kommt für die Umsetzung der Benutzeroberfläche und der Anwendungslogik die Programmiersprache Python zum Einsatz.


---

## Anwenderdokumentation

### Einleitung

Die Anwendung soll der Rechnungsverwaltung dienen.

---

### Funktionen

- Rechnungen erstellen und löschen
- Dienstleister hinzufügen und löschen
- Kunden hinzufügen und löschen
- Rechnungen exportieren
- Rechnungen als Vorschau anzeigen

---

### Installation

```bash
# Schritt-für-Schritt Installationsanleitung
git clone https://github.com/deinuser/deinrepo.git
cd deinrepo
pip install -r requirements.txt
```

---

### Konfiguration

Erkläre Konfigurationsmöglichkeiten, Umgebungsvariablen oder Dateien.

---

### Benutzung

Beschreibe die Benutzung mit Beispielen, Kommandozeilenargumenten oder Navigationsanweisungen in der Oberfläche.

---

### Screenshots

Füge relevante Screenshots oder GIFs ein.

![Screenshot](./screenshots/screen1.png)

---

### Fehlerbehebung

| Problem           | Lösung                    |
|-------------------|--------------------------|
| Häufiges Problem  | So wird es behoben        |
| Weiteres Problem  | So wird es behoben        |

---

### FAQ

**F:** Häufig gestellte Frage?  
**A:** Antwort.

---

### Kontakt & Support

- E-Mail: [deine.email@example.com]
- GitHub Issues: [Repo-Issues-Link]

---

## Entwicklungsdokumentation

### Architekturüberblick

Beschreibe die Software-Architektur (gerne mit Diagrammen).

---

### Projektstruktur

```text
root/
├── src/
├── tests/
├── docs/
├── ...
```

---

### Entwicklungsumgebung einrichten

Anleitung zum Einrichten der Entwicklungsumgebung.

---

### Coding Guidelines

- Namenskonventionen
- Codestyle
- Linting/Formatierung

---

### Wichtige Module & Komponenten

| Modul         | Beschreibung                |
|---------------|----------------------------|
| modul1.py     | Verantwortlich für X       |
| modul2.py     | Zuständig für Y            |

---

### Datenbankschema

Füge Diagramme oder Tabellenübersichten ein.

---

### API-Endpunkte

| Methode | Endpunkt     | Beschreibung        |
|---------|--------------|--------------------|
| GET     | /api/item    | Alle Items abrufen |
| POST    | /api/item    | Item erstellen     |

---

### Tests

Beschreibe die Teststrategie, Frameworks und wie Tests ausgeführt werden.

---

### Deployment

Anleitung zum Deployment der Anwendung.

---

### Changelog

| Version | Datum      | Änderungen              |
|---------|------------|-------------------------|
| 1.0.0   | JJJJ-MM-TT | Erste Veröffentlichung  |

---

### Beitragende & Beiträge

Richtlinien für Beitragende.

---

### Lizenz

Gib die Projektlizenz an.

---

> _„Dokumentation ist ein Liebesbrief an das eigene zukünftige Ich.“_  
> — Damian Conway
