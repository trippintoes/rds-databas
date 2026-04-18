# Referensbeteckningsregister

En liten lokal webbapp för att registrera referensbeteckningar från ritningar, hantera versionshistorik och hålla koll på vad som gäller, vad som väntar godkännande och vad som är ur bruk.

Appen är upplagd efter hur ert Excel-blad faktiskt ser ut i dag:

- nivå 1 = driftområde (kodlista)
- nivå 2 = disciplin (kodlista)
- nivå 3 = funktions-ID för anläggning (fritext, ansöks externt)
- nivå 4 = funktionsklass (kodlista bokstav A-Z, löpnummer auto)
- nivå 5-7 = processenhet, utrustningsenhet, kontrollenhet (bokstäver fritext, löpnummer auto per förälder)
- funktionsbeteckningen byggs som `=nivå1.nivå2.nivå3.nivå4...`

## Det här finns med

- unika objekt per full beteckning
- dropdown-kodlistor för nivå 1, 2 och 4 (utifrån er tabell)
- **automatiska löpnummer**: välj bara bokstav (t.ex. `F` eller `JQ`) så sätter systemet nästa lediga nummer (`F01`, `F02`, ...)
- nivå 4 scopas per anläggning (L1+L2+L3)
- nivå 5-7 scopas per förälder (så `JD01` kan återkomma under både `F01` och `F02`)
- huvudpost på funktionsklass kan bära underposter för processenhet, utrustningsenhet och kontrollenhet
- varje underpost har eget populärnamn
- versionshistorik per objekt
- **ändringshistorik per version** som visar fält-för-fält vad som ändrats (före → efter) och när
- tydligt fält för `godkänd av` och `godkänd datum` i varje version
- status: `registrerad`, `skickad_for_godkannande`, `godkand`, `ur_bruk`
- `gäller från` och `gäller till`
- ritningsnummer och ritningsrevision
- audit-logg för skapade versioner
- krockkontroll för potentiella dubletter på alla nivåer
- CSV-export

## Starta appen

Appen kräver bara Python 3 (standardbiblioteket) — inga externa beroenden.

### macOS / Linux

```bash
python3 app.py
```

### Windows

```powershell
py app.py
```

Öppna sedan:

```text
http://127.0.0.1:8000
```

Vill du använda en annan port anger du den som argument:

```bash
python3 app.py 8080
```

## Auto-numrering — så funkar det

När du skapar ett objekt:

- Välj **bokstav för funktionsklass** (nivå 4) i dropdown. Systemet hittar nästa lediga löpnummer i kombinationen driftområde + disciplin + anläggning och fyller i det automatiskt (t.ex. `F01`, nästa blir `F02`).
- För **nivå 5-7** skriver du två bokstäver (t.ex. `JQ`) i respektive fält. Systemet slår upp nästa lediga löpnummer under förälderposten och fyller på (`JQ01`, `JQ02`).
- Vill du låsa ett specifikt nummer kan du skriva hela koden själv (t.ex. `JQ05`). Då används den exakt som du skrev.

## Jira-koppling för beslutsfält

Appen kan lagra Jira-ärende och beslut per version. Sätt miljövariabler innan du startar appen för att synka beslutet direkt från Jira API.

### macOS / Linux (bash/zsh)

```bash
export JIRA_BASE_URL='https://dittbolag.atlassian.net'
export JIRA_EMAIL='din.adress@bolag.se'
export JIRA_API_TOKEN='din_api_token'
export JIRA_DECISION_FIELD='customfield_12345'
python3 app.py
```

### Windows (PowerShell)

```powershell
$env:JIRA_BASE_URL='https://dittbolag.atlassian.net'
$env:JIRA_EMAIL='din.adress@bolag.se'
$env:JIRA_API_TOKEN='din_api_token'
$env:JIRA_DECISION_FIELD='customfield_12345'
py app.py
```

Om du hellre använder Bearer-token sätter du `JIRA_BEARER_TOKEN` i stället för `JIRA_EMAIL` + `JIRA_API_TOKEN`.

`JIRA_DECISION_FIELD` kan vara själva fält-id:t som `customfield_12345`. Du kan också ange fältnamnet, men id är säkrast.

## Hur den är tänkt att användas

- Skapa ett objekt per unik referensbeteckning.
- En funktionsklass som till exempel `F01` kan vara huvudpost.
- Under huvudposten kan du sedan lägga egna poster för processenhet, utrustningsenhet och kontrollenhet.
- När något ändras skapar du en ny version i stället för att skriva över gammal information. Ändringarna syns i sektionen **Ändringshistorik per version** på objektets detaljsida.
- Om ett objekt ska upphöra kan du skapa en ny version med status `ur_bruk` och ange `gäller till`.
- Sidan **Krockkontroll** hjälper dig hitta dubletter per nivå och exakta krockar på hela beteckningen.
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
