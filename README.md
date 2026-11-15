# Familje-IPTV – egna M3U-spellistor för IBO Player

En enkel, öppen IPTV-spellista som du styr själv. Sex kategorier, en gemensam
spellista, inga lösenord, ingen egen server och dagliga uppdateringar via GitHub Actions.
Kurdistan-kategorin har kompletterats med Kurdmax, Kurdmax Show/Music,
Kurdsat-alternativ, Speda, Gali Kurdistan, Nubar m.fl.

**Viktigt:** Detta ersätter **inte** ett betalt IPTV-abonnemang och låser inte upp
PIN-koden på en befintlig spellista. Det är en samling av publikt listade
ström-URL:er från [IPTV-org](https://github.com/iptv-org/iptv) och ett fåtal andra
öppna källor. Alla kanalers vidarepubliceringsrättigheter är inte verifierade. Strömmarna kan
ändras, vara geoblockerade eller sluta fungera. Kontrollera sändningsrättigheter
för din användning. Inget DRM eller abonnemang kringgås.

## Länkar till listorna efter publicering

Skapa ett **publikt** GitHub-repository som heter `familje-iptv` och lägg
filerna i repositoryts **rot** på grenen `main`. Avsett GitHub-konto är `yahyasystementor`:

| Spellista | Adress (kopiera till IBO Player) |
|---|---|
| Alla kanaler | `https://raw.githubusercontent.com/yahyasystementor/familje-iptv/main/playlists/all.m3u` |
| Kurdistan | `https://raw.githubusercontent.com/yahyasystementor/familje-iptv/main/playlists/kurdistan.m3u` |
| Irak | `https://raw.githubusercontent.com/yahyasystementor/familje-iptv/main/playlists/iraq.m3u` |
| Arabiska | `https://raw.githubusercontent.com/yahyasystementor/familje-iptv/main/playlists/arabic.m3u` |
| Sverige | `https://raw.githubusercontent.com/yahyasystementor/familje-iptv/main/playlists/sweden.m3u` |
| Turkiet | `https://raw.githubusercontent.com/yahyasystementor/familje-iptv/main/playlists/turkey.m3u` |
| Internationella | `https://raw.githubusercontent.com/yahyasystementor/familje-iptv/main/playlists/international.m3u` |

Kurdistan-filen levereras nu med en snapshot av IPTV-org:s 35 kurdiskspråkiga
ström-URL:er, Zagros TV samt separata kuraterade extraströmmar. Där ingår
Kurdmax Sorani, Kurdmax Show, Kurdmax Music, Kurdsat, Kurdsat News,
Kurdistan TV, Kurdistan 24, Speda och flera andra. Filerna är **URL-kandidater,
inte bekräftade fungerande TV-sändningar**.

- `sources/kurdish-extra.m3u`: kompletterande strömkandidater som automatiskt läggs till vid körning.
- `sources/kurdish-iptv-org-snapshot.m3u`: ögonblicksbild av IPTV-org:s 35 kurdiska kanaler (2026-11-15). Används endast för det levererade startpaketet; Actions hämtar aktuell källa.
- `sources/kurdish-archive-untested.m3u`: äldre, sannolikt mer opålitliga adresser **som inte läggs till automatiskt**.

**OBS:** Ingen nätverksbaserad verifiering av de individuella HLS-strömmarnas drift
eller sändningsrättigheter har gjorts. Länkar till tredjepartstjänster kan sluta
fungera eller sakna klar rättighetsinformation. Använd bara källor du har rätt att se.

## Publicera på ditt GitHub-konto (webbläsare)

1. Öppna https://github.com/new och skapa ett **Public** repo `familje-iptv`.
   Välj **inte** att skapa en README automatiskt.
2. Packa upp ZIP-paketet och behåll mapparna och filerna som de ligger.
3. Öppna repot på GitHub → **Add file → Upload files**. Dra in allt innehåll
   i den uppackade mappen, inklusive den dolda `.github`-mappen, och **Commit changes**.
   På mobil kan uppladdning av mappar vara begränsad; använd gärna dator.
4. Öppna fliken **Actions**, aktivera Actions om GitHub frågar, välj
   **Uppdatera IPTV-spellistor** → **Run workflow**. Vänta tills körningen blir grön.
5. Under `playlists/status.json` syns antal kanaler och datum för uppdatering.

**Om Actions inte får skriva till repot:** gå till **Settings → Actions → General →
Workflow permissions** och kontrollera att skrivbehörighet är tillåten. Själva
arbetsflödet har `contents: write`.

## Kontrollera vilka kurdiska kanaler som faktiskt svarar

Det ingår också ett **separat GitHub Actions-jobb** som heter **Kontrollera kurdiska TV-kanaler**.
Det testar varje M3U8-adress, följer eventuella underlistor och försöker hämta en liten del
av ett videosegment. När repot väl är publicerat:

1. Öppna **Actions → Kontrollera kurdiska TV-kanaler → Run workflow**.
2. Öppna filen **`reports/kurdistan-health.md`** efter körningen.
3. `MEDIA_NÅBAR` = både spellista och en bit media kunde hämtas (stark indikation).
   `SPELLISTA_NÅBAR` = spellistan svarar men mediasegmentet kunde inte bekräftas.
   `BLOCKERAD` = HTTP 401/403; kan vara geografisk spärr.
   `SAKNAS` = HTTP 404/410; troligen gammal adress.
   `OSÄKER` = timeout, DNS eller annan ofullständig kontroll.
   `FEL` = oväntat serverfel eller innehåll som inte är M3U8.

Jobbet körs också automatiskt **varje dag**. Rapporten verifierar nätåtkomst **från GitHubs
servrar**, inte spelbarhet i IBO Player på din TV i Sverige. Vi tar därför inte bort kanaler
automatiskt baserat på ett misslyckat test.

Testa lokalt med internetanslutning:

```bash
python scripts/check_streams.py
```

**Statisk kontroll 2026-11-15:** `kurdistan.m3u` har 59 unika korrekt formaterade HTTP(S)-adresser
(53 HTTPS och 6 HTTP). Detta är **inte** en livekontroll.

## Lägg till i IBO Player

1. Gå till IBO Players sida **Manage Playlists** med enhetens registrering redan vald.
2. Tryck **Add Playlist** (inte *Add XC Playlist*).
3. Namn: `Familje-TV`.
4. M3U URL: använd adressen för **Alla kanaler** ovan, från ditt publicerade repository.
5. Spara. Uppdatera/ladda om spellistan på TV:n.

**Lägg aldrig in TV:ns MAC-adress, enhetsnyckel, konto- eller IPTV-lösenord i
ett publikt GitHub-repository.**

## Hur uppdateringen fungerar

- GitHub Actions hämtar publicerade M3U-listor från IPTV-org dagligen cirka 04:17 UTC
  (och när `config.json` eller byggkoden ändras).
- Källorna prioriteras Kurdistan → Irak → Arabiska → Sverige → Turkiet → Internationella.
- Varje kategori har sin egen M3U-fil. Den gemensamma listan tar bort dubbletter
  med samma ström-URL men behåller kategorierna `group-title`.
- Om en källa inte går att ladda ned eller är tom misslyckas körningen **utan att
  skriva över** de befintliga listorna. Nästa schemalagda körning försöker igen.
- Uppdatering av källfiler **garanterar inte** att en enskild livestream spelar;
  en kanal kan vara tillfälligt nere, spärrad eller kräva en annan klient.

Redigera `config.json` för att ändra länder eller språk. Skriptet hämtar nätverkskällor **endast** från IPTV-org via HTTPS; de manuellt
insamlade tredjepartsadresserna lagras som lokal textfil utan att byggskriptet kontaktar
andra leverantörer. Detta är en lista med strömadresser, inte en TV-proxy. Med `channel_ids` kan du välja enstaka
kanaler från en viss källa, som Zagros TV i Kurdistan-gruppen. Flera källor under en kategori går bra.

## Utveckling lokalt

Kräver Python 3.10+ och internetanslutning vid byggning, men inga paket.

```bash
python -m unittest discover -s tests -v
python scripts/build.py
```

Källor: https://github.com/iptv-org/iptv/blob/master/PLAYLISTS.md och
https://github.com/iptv-org/iptv/blob/master/docs/playlists.md

## Källor för kompletterande kurdiska kanaler

- IPTV-org (Kurdish): https://github.com/iptv-org/iptv/blob/gh-pages/languages/kur.m3u
- IPTV-org (Iraq): https://github.com/iptv-org/iptv/blob/master/streams/iq.m3u
- Kurdish m3u, juni 2025: https://gist.github.com/khalatkurdi/90ccc561494f2993136c3642e1fa30ad
- Kurdish Channel, januari 2026: https://gist.github.com/nevzatokcu/43c72ad960f1579cedea6071e16d1821
- Kurdish channels, uppdaterad april 2026: https://gist.github.com/shawazomed/78d1b863db1e704511bad2b1516d466f
- Turkish IPTV examples (tredjepart): https://github.com/eren121tt-hue/turk-iptv

Endast publikt listade strömadresser. Alla är inte bekräftade att vara aktiva och
listade adresser innebär inte i sig bekräftelse på vidarepubliceringsrätt.
