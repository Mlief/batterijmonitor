# Batterijmonitor

Dagelijkse signalering van openbare berichten over zakelijke batterijprojecten in de Nederlandse agrarische sector en glastuinbouw.

## Wat de monitor doet
- Haalt dagelijks openbare Google News RSS-resultaten op voor zoektermen rond batterijen, energieopslag, kwekerijen en agrarische bedrijven.
- Neemt concrete projecten, aankondigingen, projecten in ontwikkeling en uitbreidingen mee.
- Laat vermogen en opslagcapaciteit als onbekend staan als de bron die niet noemt. Een onbekend vermogen wordt dus niet automatisch uitgesloten.
- Probeert bedrijfsnaam, locatie, vermogen, capaciteit, status en betrokken partijen uit titel en samenvatting te herkennen.
- Voorkomt herhaling met een lokale lijst van eerder gemelde links.
- Maakt een dagelijks HTML-overzicht en bewaart dit als GitHub Actions-artifact.

## Belangrijke beperking
Dit is een monitor van openbare, indexeerbare bronnen. Google News/RSS en zoekmachines tonen niet alle LinkedIn-berichten. De monitor scrapt LinkedIn niet en kan daarom geen volledige LinkedIn-dekking garanderen. De Google Alerts die je al hebt ingesteld blijven een aanvullende bron in Outlook.

## Dagelijkse uitvoering
De workflow draait dagelijks om 05:00 UTC (06:00 Nederlandse wintertijd; 07:00 zomertijd). Je kunt hem ook handmatig starten via Actions.

## E-mail naar Outlook
De workflow kan het rapport per e-mail versturen via SMTP. Daarvoor moeten repository secrets worden ingesteld. Gebruik alleen een door je organisatie toegestane SMTP-configuratie:

- `SMTP_HOST`: SMTP-server
- `SMTP_PORT`: meestal 587
- `SMTP_USERNAME`: accountnaam
- `SMTP_PASSWORD`: SMTP-wachtwoord of app-wachtwoord dat door IT is toegestaan
- `MAIL_FROM`: afzenderadres
- `MAIL_TO`: `edwin.melief@enova.nl`

Zonder deze secrets wordt het rapport wel gemaakt en als artifact opgeslagen, maar niet gemaild. Bij Microsoft 365 kan SMTP AUTH door de organisatie zijn uitgeschakeld; vraag IT dan om de goedgekeurde verzendmethode. Plaats nooit wachtwoorden in code of in dit repository.

## Beoordeling
- **Hoog**: concreet project met vermogen boven 500 kW, of duidelijke grote investering.
- **Middel**: concreet project, maar vermogen ontbreekt of is niet eenduidig.
- **Laag**: algemene marktinformatie, productnieuws of een mogelijk kleine installatie.

De classificatie is een eerste automatische indicatie. Controleer de bron voordat je een commerciële opvolging doet.
