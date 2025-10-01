import sys #importerar språkets standarsmodul för systemrelaterade saker. Qt appen behöver sys.argv (kommandoradsargument) när vi startar appen.
from dataclasses import asdict #tar in asdict från dataklassen, asdict konverterar en dataklass ex event till en vanlig python dict, bra innan vi sparar till json.
from PySide6.QtWidgets import QApplication, QWidget, QTabWidget, QVBoxLayout, QMessageBox #tar in centrala Qt widgetar. QApplication: applikationsobjektet, QWidget: basen för fönster/komponenter, QTabWidget: flikar(tabs), QVBoxLayout: placerar saker i kolumn, QmessageBox: dialogruta för ex felmeddelanden.

from .models import Character, Place, Event #hämtar datamodeller från lokala paketet, vi konverterar till json
from .storage import load_state, save_state #två funtioner för att läsa eller skriva state.
from .ui.tabs import ListTab, EventsTab #listTab: flik för att lista och redigera namn ex characters, places. EventsTab: flik som hanterat en lista av event objekt.
from .ui.timeline import TimelineTab # flik som visualiserar händelser i tidsordning

class MainWindow(QWidget): #innehåller våra flikar och layout.
    def __init__(self): # konstruktor
        super().__init__()
        self.setWindowTitle("timeline – MVP with Timeline")# sätter fönstrets titel och startstorlek
        self.resize(900, 600)#igenkänning, lagom storkek för fyra flikar

        state = load_state()#läser inte det senaste sprade, för vi vill starta med användarens tidigare data i minnet.
        char_names = [c["name"] for c in state.get("characters", [])]# tar ut namn, om namn inte finns används tom lista som standard.
        place_names = [p["name"] for p in state.get("places", [])]#samma
        events = [Event(**e) for e in state.get("events", [])] #man gör en vanlig grej till ett riktigt objekt genom packa upp med **. nycklarna måste ha samma namn (e) om fel blir typeError.

        self.tabs = QTabWidget() #skapar flikbehållaren. för vi vill separata vyer.
        self.chars_tab = ListTab("Character", char_names)#två tabs, ena visar character och andra places. använfa samma listkomponent för båda, för mindre dubbla listor i koden.
        self.places_tab = ListTab("Place", place_names)
        self.events_tab = EventsTab(events) # visar/redigerar event objekt.
        self.timeline_tab = TimelineTab(self.events_tab.values) #skapar tidslinjefliken och ger den händelser den ska visa, utan parantes, receptet inte kakan, detalj

        self.tabs.addTab(self.chars_tab, "Characters") #flikar i bestämd ordning.
        self.tabs.addTab(self.places_tab, "Places")
        self.tabs.addTab(self.events_tab, "Events")
        self.tabs.addTab(self.timeline_tab, "Timeline")

        layout = QVBoxLayout(self) # huvudfönstret ska använda vertikal layout(låda där innehållet staplas upp till ner.)
        layout.addWidget(self.tabs)#Qt kräver en layout för automantisk storlek/placering, en tabs räcker

    def closeEvent(self, event): # sparar när fönstret stängs.autospara
        state = { # man bygger en ny ren ordbok med allt som ska sparas
            "characters": [asdict(Character(name=n)) for n in self.chars_tab.values], #för varje namn från chars_tab skapas en Character(name=n) och man kör asdict(...) blir "name"...
            "places": [asdict(Place(name=n)) for n in self.places_tab.values], #samma
            "events": [asdict(e) for e in self.events_tab.values], #för varje event kör man asdict(e) en dict med alla fält i eventet.
        }
        try: # försöker spara, vid fel proppar en röd felruta upp.
            save_state(state)
        except Exception as e:
            QMessageBox.critical(self, "Save failed", f"Could not save data: {e}")
        event.accept()

def main(): #start
    app = QApplication(sys.argv) # skapar appen och låter Qt läsa flaggor
    w = MainWindow() # skapar huvudfösnter och visar
    w.show()
    sys.exit(app.exec()) # startar Qt eventloop, exit returnerar rätt statuskod till operativsystemet.

if __name__ == "__main__": # endas om filen körs direkt, 
    main()
