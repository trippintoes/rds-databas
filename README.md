# Referensbeteckningsregister

En liten lokal webbapp för att registrera referensbeteckningar från ritningar, hantera versionshistorik och hålla koll på vad som gäller, vad som väntar godkännande och vad som är ur bruk.

Appen är nu upplagd efter hur ert Excel-blad faktiskt ser ut i dag:

- nivå 1 = driftområde
- nivå 2 = disciplin
- nivå 3 = funktions-ID för anläggning
- nivå 4 = funktionsklass
- nivå 5-7 = senare fördjupning när projekteringen kommit dit
- nivå 1-3 ses som toppnod och får återkomma
- det som inte ska krocka är huvudsystem på nivå 4 och löpnummer i nivå 5-7
- funktionsbeteckningen byggs som `=nivå1.nivå2.nivå3.nivå4...`

## Det här finns med

- unika objekt per full beteckning
- nivåerna visas med era riktiga namn i stället för generiska nivånummer
- enklare registrering med fokus på nivå 1-4 först
- nivå 5-7 ligger i en separat fördjupningsdel
- huvudpost på funktionsklass kan bära underposter för processenhet, utrustningsenhet och kontrollenhet
- varje underpost har eget populärnamn
- versionshistorik per objekt
- tydligt fält för `godkänd av` och `godkänd datum` i varje version
- status: `registrerad`, `skickad_for_godkannande`, `godkand`, `ur_bruk`
- `gäller från` och `gäller till`
- ritningsnummer och ritningsrevision
- audit-logg för skapade versioner
- krockkontroll för potentiella dubletter
- CSV-export

## Starta appen

1. Öppna PowerShell i projektmappen.
2. Starta appen:

```powershell
py app.py
```

3. Öppna sedan:

```text
http://127.0.0.1:8000
```

Om du vill använda en annan port kan du ange den:

```powershell
py app.py 8080
```

## Jira-koppling för beslutsfält

Appen kan lagra Jira-ärende och beslut per version. Om du vill synka beslutet direkt från Jira API sätter du dessa miljövariabler innan du startar appen:

```powershell
$env:JIRA_BASE_URL='https://dittbolag.atlassian.net'
$env:JIRA_EMAIL='din.adress@bolag.se'
$env:JIRA_API_TOKEN='din_api_token'
$env:JIRA_DECISION_FIELD='customfield_12345'
py app.py
```

Om du hellre använder Bearer-token kan du sätta:

```powershell
$env:JIRA_BASE_URL='https://dittbolag.atlassian.net'
$env:JIRA_BEARER_TOKEN='din_token'
$env:JIRA_DECISION_FIELD='customfield_12345'
py app.py
```

`JIRA_DECISION_FIELD` kan vara själva fält-id:t som `customfield_12345`. Du kan också ange fältnamnet, men id är säkrast.

## Hur den är tänkt att användas

- Skapa ett objekt per unik referensbeteckning.
- En funktionsklass som till exempel `F04` kan vara huvudpost.
- Under huvudposten kan du sedan lägga egna poster för processenhet, utrustningsenhet och kontrollenhet.
- När något ändras skapar du en ny version i stället för att skriva över gammal information.
- Om ett objekt ska upphöra kan du skapa en ny version med status `ur_bruk` och ange `gäller till`.
- Sidan **Krockkontroll** hjälper dig hitta dubletter på nivå 1-4 och exakta krockar på nivå 1-7.
- **Export CSV** ger dig data ut för vidare delning eller kontroll.

## Var sparas datan?

SQLite-databasen skapas automatiskt här:

```text
data/rds_registry.sqlite3
```

## Tips för ditt arbetssätt

- Sätt `status = registrerad` när du först matar in från ritning.
- Byt till `skickad_for_godkannande` när du skickar vidare underlaget.
- När godkännande finns registrerar du en ny version eller markerar aktuell version med `godkand` beroende på hur ni vill jobba.
- Ange alltid ritning och revision för spårbarhet.
