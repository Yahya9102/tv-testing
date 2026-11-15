# tv-testing

Egna, offentliga M3U-spellistor för IBO Player, automatiska kanaluppdateringar och dagliga nätverkstester av kurdiska strömkandidater.

## Direkta M3U-länkar för IBO Player

| Spellista | URL |
|---|---|
| **Kurdistan** | https://raw.githubusercontent.com/Yahya9102/tv-testing/main/playlists/kurdistan.m3u |
| **Alla kategorier** | https://raw.githubusercontent.com/Yahya9102/tv-testing/main/playlists/all.m3u |
| Irak | https://raw.githubusercontent.com/Yahya9102/tv-testing/main/playlists/iraq.m3u |
| Arabiska | https://raw.githubusercontent.com/Yahya9102/tv-testing/main/playlists/arabic.m3u |
| Sverige | https://raw.githubusercontent.com/Yahya9102/tv-testing/main/playlists/sweden.m3u |
| Turkiet | https://raw.githubusercontent.com/Yahya9102/tv-testing/main/playlists/turkey.m3u |
| Internationella | https://raw.githubusercontent.com/Yahya9102/tv-testing/main/playlists/international.m3u |

## Automatik

- **Actions → Uppdatera IPTV-spellistor** bygger om listorna från IPTV-org och kuraterade källor dagligen.
- **Actions → Kontrollera kurdiska TV-kanaler** testar HLS-manifest och segment och skriver en rapport till `reports/kurdistan-health.md`.
- Vid första användningen kan du öppna fliken **Actions** och köra respektive workflow manuellt.

Kurdistan-listan har en levererad uppsättning av 59 listade strömadresser, inklusive reservadresser. Det är *inte* 59 live-verifierade fungerande TV-kanaler. IBO Player kan behöva uppdateras för att läsa om spellistan.

## Källor, begränsningar och säkerhet

Adresser kommer främst från [IPTV-org](https://github.com/iptv-org/iptv) och kompletterande öppna listor. En publicerad URL är inte en garanti för drift, geografisk tillgänglighet eller rätt att återdistribuera kanalens innehåll. Projektet tillhandahåller ingen videoserver, betalkanaler, kringgående av DRM eller åtkomst till tidigare PIN-skyddat abonnemang. Lägg inte privata tokens, inloggningar eller hemliga strömlänkar i detta publika repo.

Källor och reservadresser finns i `sources/`; automatiseringen finns i `.github/workflows/`; testerna finns i `tests/`.
