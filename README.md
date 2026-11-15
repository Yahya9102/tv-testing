# tv-testing

En gemensam M3U-spellista med flera kategorier, avsedd för IBO Player. **Det finns bara en TV-spellista att lägga in.** Inga inloggningsuppgifter eller någon egen videoserver behövs för publika strömmar.

## Lägg till i IBO Player

**Namn:** TV Testing

**M3U-adress:**

`https://raw.githubusercontent.com/Yahya9102/tv-testing/main/playlists/all.m3u`

Lägg in den en gång med **Add Playlist**. Spelaren läser M3U-fältet `group-title` och kan sortera kanalerna i kategorierna:

- **Kurdiska**
- **Persiska**
- **Irakiska**
- **Arabiska**
- **Svenska**
- **Turkiska**
- **Internationella**

Kategorierna finns **inne i `playlists/all.m3u`**, inte som olika spellistor. En strömadress som förekommer i flera källor placeras i första matchande kategori för att undvika dubbletter.

## Automatisk uppdatering och tester

- `Uppdatera IPTV-spellistor` hämtar nya URL-adresser från IPTV-org var sjätte timme och bygger **bara `all.m3u`** samt statistik i `status.json`.
- Om en källa tillfälligt är nere behåller skriptet tidigare adresser i den kategorin, i stället för att tömma listan.
- `Kontrollera kanalernas strömadresser` försöker dagligen hämta M3U8-manifest och videosegment för de kurdiska och persiska kanalerna **i samma huvudlista**. Rapporter finns i `reports/`.
- `Kontrollera kodtester` kör Python-enhetstester vid kodändringar. Det blockerar inte schemalagda kanaluppdateringar.

**Viktigt:** Strömtesterna är diagnostik och tar inte automatiskt bort kanaler från huvudlistan. Att en adress fungerar från GitHubs nätverk garanterar inte uppspelning från Sverige; enstaka kanaler kan fortfarande vara döda eller geografiskt blockerade. Publicerade adresser innebär inte någon verifierad rätt att vidaresända innehållet. Undvik privata abonnemangslänkar, konton eller tokens i detta publika repo.

Källkonfiguration: `config.json` och `sources/`.

Senaste statistik: `playlists/status.json`.
