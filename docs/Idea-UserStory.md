Idee
Titel: Erdbeben Monitoring

Kurzbeschreibung: Visualisierung von Echtzeitdaten für Erdbeben auf einer Weltkarte

Beschreibung: 
Eine End-to-End-Pipeline bezieht Erdbebenereignisse über die USGS-API (https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson) in (fast) Echtzeit, verarbeitet sie per Spark/Kafka als Data Stream und speichert sie in einer Datenbank als Roh- und Auswertungsdaten. Die Ergebnisse werden in einem Streamlit-Dashboard visualisiert. Das Dashboard bietet mehrere Funktionen wie eine Karte, Zeitreihen, Magnituden-Verteilungen, Heatmap-Overlay, Tsunami-Warnung und verschiedene Terrain-Ansichten. Alle Schritte – Datenerfassung, Transformation, Speicherung, Auswertung und Darstellung – werden in einem Jupyter-Notebook dokumentiert.

User Stories
https://en.wikipedia.org/wiki/User_story

(Connextra template) As a <role> I can <capability>, so that <receive benefit>


As a user I can see when the last earthquake was within xxx km of the place yyy, so that I am up-to-date about the latest earthquake.
As a user I can see a heatmap of earthquake frequencies across the world in the last 24 hours / 365 days, so that I can easily recognize heavily impacted regions.
As a user I can filter earthquakes by magnitude, so that I only see events that feel relevant to me.
As a person who lives near the beach, I would like to know if there was tsunami near my place in the last few weeks/months or alerted when there is one
As a non technical user, I can ask the system any earthquakes data using just a natural language, such as “show me any earthquakes event with magnitude higher than 3.0 in Austria in the last 30 days and sorted by date” 
As a user I can sort earthquakes by most recent, strongest or nearest to my location so I can scan for events that matter to me.
As a user I can toggle between different map views like satellite or terrain, so that I can view the impact location from different angles. 
As a user I can use speed through a certain time period, so that I can check how many earthquakes occurred in that time period. 

Requirements (functional)
Terrain toggle function
Heatmap overlay
Timelapse function
Filter/Sort function
Magnitude display
Tsunami data display
Requirements (must have criteria)
Store data
Spark or Kafka
Streamlit app
Jupyter notebook with data flow
(optional: Docker) 

Tech stack (~)
Spark
Streamlit
Docker
Database (sqlite vs postgresql)
venv/pip oder uv?
github
Jupyter

Architecture (mehr Recherche notwendig!)
 Source API -> Parse/wrangle data -> Spark -> Database -> SQL? -> Streamlit



