# LF11-Projekt

Erstellung einer Rechungserstellungssoftware

##### Table of Contents  
- [Priorisierung](#priorisierung)
- [Todo](#todo)

## Priorisierung
| **Priorität** | **User Story (Als ... möchte ich ... damit ...)**                                                                                                | **Akzeptanzkriterien**                                    |
|---------------|--------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------|
| 🥇 Hoch        | Als Benutzer möchte ich Kunden anlegen, bearbeiten und löschen können, damit ich Stammdaten verwalten kann.                                      | CRUD-Funktionalität für Kunden, Eingabevalidierung        |
| 🥇 Hoch        | Als Benutzer möchte ich Dienstleister anlegen, bearbeiten und löschen können, damit ich diese in Rechnungen verwenden kann.                      | CRUD-Funktionalität für Dienstleister                     |
| 🥇 Hoch        | Als Benutzer möchte ich Rechnungen erstellen können, damit ich Dienstleistungen abrechnen kann.                                                  | Eingabe von Beträgen, Auswahl Kunde/Dienstleister         |
| 🥇 Hoch        | Als Benutzer möchte ich eine Druckvorschau sehen, bevor ich eine Rechnung drucke.                                                                | Vorschau sichtbar vor Druck, keine direkte Druckauslösung |
| 🥈 Mittel      | Als Benutzer möchte ich Rechnungen drucken können, damit ich sie in Papierform weitergeben kann.                                                 | Rechnungen werden korrekt gedruckt                        |
| 🥈 Mittel      | Als Benutzer möchte ich Rechnungen in PDF und/oder XML wandeln können, damit ich sie per PDF/XML weitergeben kann.                               | Rechnungen werden korrekt als PDF/XML umgewandelt         |
| 🥈 Mittel      | Als Benutzer möchte ich Rechnungen archivieren können, damit ich diese später wiederfinden kann. Diese sollen zur Sicherheit verschlüsselt sein. | Archiv als ZIP mit PDF + XML, verschlüsselt               |
| 🥈 Mittel      | Als Benutzer möchte ich in Registerkarten zwischen Kunden, Dienstleistern und Rechnungen wechseln können, damit ich den Überblick behalte.       | Funktionierende GUI-Tabs mit Navigation                   |
| 🥈 Mittel      | Als Benutzer möchte ich sehen, welcher Kunde zu welchem Dienstleister gehört, um die Beziehungen zu verstehen.                                   | Zuordnung sichtbar in GUI                                 |
| 🥉 Niedrig     | Als Product Owner möchte ich UML-Diagramme zur Softwarestruktur erhalten, damit ich die Architektur nachvollziehen kann.                         | Vorhandensein von folgenden Diagrammen:                   |
| 🥉 Niedrig     | Als Entwickler möchte ich während des Entwicklungsprozesses Testdaten in der Datenbank, um schneller testen zu können.                           | Automatisiertes Einfügen von Beispieldaten                |


## Todo



- [ ]    3.    autom. Width von Details Pages realisieren (zurückgestellt)
- [ ]    10.    Einträge durchsuchen
    - [x]    Label 'lbl_search_for' responisve machen (Text ändern je nach geöffnetem Tab) 18.05.2025
- [ ]    11.    Rechnungen erstellen
    - [ ]    Auswahl von Dienstleister + anlegen Button
    - [ ]    Auswahl von Kunden + anlegen Button
    - [x]    Auswahl von mehreren Positionen + Bulk anlegen Button 18.05.2025
- [ ]     12.    Form Validation Rules erfassen und umsetzen
- [ ]     13.    LOGO upload umsetzen
- [ ]     14.    Rechnungen als PDF exportieren mit Druckvorschau
- [ ]     15.    PDF-Vorschau für bestehende Rechnungen
- [ ] 16.    PDF-Vorschau für bestehende Rechnungen -> niedrige Prio 
- [ ] 18. Styling verbessern
    - [ ] Padding obere und linke Seite erhöhen (3-4px ?)
    - [ ] Bei Rechnungen -> Positionstabelle unten -> Eintragsnummer ganz links entfernen (ist sinnlos)
    - [ ] In den Tabellen -> wichtige Spalten weiter vorne anzeigen (optional wenn genug Zeit ist)
    - [ ] Warum ist neben der Suchleiste eine Anzeige für das Erstellungsdatum?
### DONE
- [x]    GUI erstellen
- [x]    Datenbanktyp auswählen und DB erstellen
- [x]    Datenmodell (folgend DM genannt) pflegen
- [x]    Dummy-Daten einfügen
- [x]    Views anlegen
- [x]    Rechnungen, Dienstleister, Kunden und Positionen anzeigen
- [x]    jeweiliges Form mit Daten des ausgewählten Eintrages füllen
- [x]    Erstellungsdatum des ausgewählten Eintrages anzeigen
- [x]    Detail-Pages für Rechnungen (Positionen) und Dienstleister (Geschäftsführer) realisieren 
- [x]    Aufteilung Code-Elemente 16.05.2025
- [x]    GUI auf full-width/height 16.05.2025
- [x]    GUI Responsive machen 16.05.2025
- [ ]    In Zahlenfeldern nur Zahlen bei Eingabe erlauben (zurückgestellt) 16.05.2025
- [x]    Automatisch PK-Felder mit nächsten kleinsten Value setzen + Logik PK Generierung 16.05.2025
- [x]    Alle QTableViews non editable machen 18.05.2025
- [x]    Positionen anlegen 18.05.2025
- [x]    Kunden anlegen 18.05.2025
- [x]    Rechnungen anlegen 18.05.2025
- [x]    Positionen löschen 20.05.2025
- [x]    Dienstleister anlegen 20.05.2025
  - [x]    Form um Bankverbindung ergänzen 18.05.2025
  - [x] Bankverbindungen  20.05.2025
- [x]    Diensteister löschen 20.05.2025
- [x]    Kunden löschen 20.05.2025
- [x] 17. Sprachmischung vermeinden - keine englischen Begriffe verwenden, alles auf Deutsch umstellen
