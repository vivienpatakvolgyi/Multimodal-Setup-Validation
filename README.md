# Kognitív Tesztbatéria Esport Setupok Viselkedéses Validációjához

Ez a repository egy kísérleti pszichológiai tesztbattériát tartalmaz **esport környezetek validációjához**. A tesztbattéria potenciálisan alkalmas esport setupok összehasonlítására, mivel több olyan kognitív folyamatot mér, amelyek relevánsak lehetnek kompetitív videojátékok során. Egy egységes viselkedéses benchmark rendszert képez, amely egyszerre rögzíti a kognitív feladatok eseményeit, a billentyűzetet és az egérhasználatot.

A tesztbattéria PsychoPy keretrendszerrel készült, és minden eseményt egy központi CSV fájlba rögzít, lehetővé téve a részletes teljesítményanalízist különböző setup konfigurációk mellett.

## Esport relevancia

A tesztbattéria több olyan kognitív folyamatot mér, amelyek relevánsak lehetnek kompetitív videojátékok és esport környezetek szempontjából:

- **Reakcióidő és döntéshozatal**: Alapvető metrikák kompetitív játékokban
- **Vizuális figyelem és szelektivitás**: Célpontok azonosítása zavaró ingerek mellett
- **Válaszgátlás**: Impulzuskontroll, hibás akciók megelőzése
- **Munkamemória**: Információtartás és frissítés gyors tempójú játékokban
- **Tartós figyelem**: Teljesítmény fenntartása hosszú meccsek során
- **Kockázatértékelés**: Stratégiai döntéshozatal reward/risk szituációkban

A validációs folyamat során a játékosok különböző hardver beállításokkal (monitor, perifériák, szék, stb.) végzik el a teszteket, így összehasonlíthatók az egyes setupok mellett mért kognitív teljesítménymutatók.

## Telepítés

### Követelmények
- Python 3.8 vagy újabb
- Windows, macOS vagy Linux

### Függőségek telepítése

```bash
pip install -r requirements.txt
```

A `requirements.txt` fájl tartalmazza az összes szükséges csomagot:
- PsychoPy (≥2023.1.3)
- pynput (≥1.8.1)
- numpy, scipy, pandas
- pyglet, pillow

## Használat

### Validációs protokoll - Teljes battéria

Esport setup validációhoz ajánlott a teljes battéria futtatása minden tesztelendő konfiguráció mellett:

```bash
python run_experiment.py
```

A program sorban végrehajtja az összes tesztet, automatikus szünetekkel közöttük. A játékos a SPACE billentyűvel léphet tovább a szünetek után. Minden adat (válaszok, reakcióidők, perifériás inputok) egyetlen CSV fájlba kerül rögzítésre az `unified_logger` segítségével.

**Ajánlott mérési protokoll:**
1. Baseline mérés (standard setup)
2. Tesztelendő setup konfiguráció 1
3. Tesztelendő setup konfiguráció 2
4. ... további konfigurációk
5. Kontroll mérés (visszatérés baseline-ra)

### Egyedi tesztek futtatása

Specifikus kognitív területek célzott teszteléséhez az egyes feladatok önállóan is futtathatók:

```bash
python -c "import flanker; flanker.main()"    # Vizuális figyelem, reakcióidő
python -c "import go_nogo; go_nogo.main()"    # Impulzuskontroll
python -c "import twoback; twoback.main()"    # Munkamemória
python -c "import stroop; stroop.main()"      # Interferencia kezelés
python -c "import sart; sart.main()"          # Tartós figyelem, fáradtság
python -c "import bart; bart.main()"          # Kockázatértékelés, egér precizitás
```

## Tesztek leírása

### 1. Flanker teszt (`flanker.py`)

A **Flanker teszt** a figyelmi kontroll és a gátlási folyamatok mérésére szolgál. A résztvevőnek nyilak sorát mutatjuk, és a középső nyíl irányát kell meghatároznia, miközben a környező nyilak (flankerek) vagy azonos (kongruens), vagy ellentétes (inkongruens) irányba mutatnak.

- **Próbák száma:** 50
- **Billentyűk:** 'A' (bal), 'L' (jobb)
- **Válaszidő limit:** 2 másodperc
- **Mért változók:** Reakcióidő, pontosság, kongruencia-hatás

### 2. Go/No-Go teszt (`go_nogo.py`)

A **Go/No-Go teszt** a válaszgátlás és az impulzuskontroll vizsgálatára alkalmas. A résztvevőnek gyorsan reagálnia kell a "GO" jelzésekre (zöld stimulus), de vissza kell tartania a válaszát a "NO-GO" jelzéseknél (piros stimulus).

- **Próbák:** 20 GO, 5 NO-GO
- **Billentyű:** SPACE (csak GO jelzésnél)
- **Válaszidő limit:** 2 másodperc
- **Hibatípusok:** Téves válasz NO-GO-nál, elmaradt válasz GO-nál
- **Visszajelzés:** Azonnali vizuális feedback hibás válaszoknál

### 3. 2-Back teszt (`twoback.py`)

A **2-Back teszt** a munkamemória kapacitását és a frissítési folyamatokat méri. Betűk sorozata jelenik meg, és a résztvevőnek jelezni kell, ha az aktuális betű megegyezik a két lépéssel korábbival.

- **Blokkok:** 2 gyakorló + 2 éles blokk
- **Próbák blokkönként:** 25
- **Megjelenési idő:** 500 ms betű, 2500 ms szünet
- **Billentyű:** 'M' (egyezés esetén)
- **Cél:** 1/3 próba egyezés (véletlenszerűen generálva)

### 4. Stroop teszt (`stroop.py`)

A **Stroop teszt** a klasszikus interferencia-paradigma, amely a verbális információ automatikus feldolgozását és a gátlási folyamatokat vizsgálja. Színszavak jelennek meg különböző tintaszínekkel, és a résztvevőnek a tintaszínt kell megnevezni, a szó jelentésétől függetlenül.

- **Próbák száma:** 40
- **Billentyűk:** P (piros), Z (zöld), K (kék), S (sárga)
- **Kondíciók:** Kongruens (szó és szín egyezik) és inkongruens (eltérő)
- **Válaszidő limit:** 2 másodperc
- **Mért változók:** Stroop-interferencia, reakcióidő különbség

### 5. SART - Sustained Attention to Response Task (`sart.py`)

A **SART** a tartós figyelem és a válaszelnyomás mérésére kifejlesztett teszt. Számjegyek (1-9) gyors sorozata jelenik meg, és a résztvevőnek minden számra reagálnia kell, **kivéve** a 3-as számjegyet.

- **Edzés:** 2×9 = 18 próba
- **Éles teszt:** 25×9 = 225 próba
- **Megjelenési idő:** 250 ms szám, 900 ms maszk
- **NO-GO stimulus:** 3-as számjegy
- **Billentyű:** SPACE (minden számnál, kivéve 3)
- **Változó betűméret:** 5 különböző méret véletlenszerűen

### 6. BART - Balloon Analogue Risk Task (`bart.py`)

A **BART** a kockázatvállalási hajlamot és a döntéshozatalt vizsgálja jutalom és veszteség kontextusában. A résztvevő léggömböket fújhat fel pumpálással, amely pénzjutalmat hoz, de a léggömb bármikor kipukkanhat, és elvész az adott körben gyűjtött pénz.


- **Blokkok:** 3 (kék, sárga, narancs léggömbök)
- **Próbák blokkönként:** 30
- **Pumpálás értéke:** 5 cent/pumpálás
- **Vezérlés:** Egérkattintás a gombokra
- **Döntés:** Pumpálás (további kockázat) vagy pénz összeszedése (biztonság)
- **Mért változók:** Pumpálások száma, összegyűjtött pénz, robbanások száma

## Adatrögzítés

Minden teszt eseményei (próbák kezdete/vége, válaszok, eredmények) az `unified_logger` révén kerülnek rögzítésre, amely:
- Egy központi CSV fájlt hoz létre időbélyeggel
- Rögzíti a billentyű- és egéreseményeket
- Minden kísérleti eseményt kontextuális információval együtt tárol
- Lehetővé teszi a komplett viselkedési adatok utólagos elemzését

**Validációs elemzéshez:** Az egyes setup konfigurációk mellett mért CSV fájlok összehasonlításával összehasonlítható:
- Reakcióidő változások (input laggal vagy megjelenítési különbségekkel összefüggő változások)
- Pontosságbeli különbségek különböző konfigurációk között
- Teljesítményváltozás hosszabb tesztelési szakaszok során
- Konzisztencia (teljesítmény stabilitása különböző beállítások mellett)

## Projekt struktúra

```
.
├── run_experiment.py      # Főprogram - teljes battéria futtatása
├── unified_logger.py      # Központi adatrögzítő rendszer
├── numpy_compat.py        # NumPy kompatibilitási patch PsychoPy-hoz
├── requirements.txt       # Python függőségek
│
├── flanker.py            # Flanker teszt
├── go_nogo.py            # Go/No-Go teszt
├── twoback.py            # 2-Back teszt
├── stroop.py             # Stroop teszt
├── sart.py               # SART teszt
├── bart.py               # BART teszt
│
└── [teszt_név]/          # Könyvtárak a vizuális stimulusokkal
    ├── flanker/
    ├── go_nogo/
    ├── twoback/stimuli/
    ├── stroop/
    ├── sart/
    └── bart/
```

## Megjegyzések

- A tesztek teljes képernyős módban futnak
- ESC billentyűvel bármikor megszakítható a teszt
- A stimulusok (képek) a megfelelő alkönyvtárakban találhatók
- A tesztek magyar nyelvű utasításokat használnak
- NumPy kompatibilitási patch automatikusan betöltődik a PsychoPy-hoz

**Esport validációs ajánlások:**
- Minden setup mellett végezzen baseline mérést a nap azonos szakában
- Minimálisan 3 ismétlés ajánlott konfiguráció/játékos kombinációnként
- Tartson standardizált pihenőidőket a mérések között
- Dokumentálja a hardver specifikációkat (monitor Hz, input device típusa, szék/asztal beállítások)
- Hasonlítsa össze a baseline vs. tesztelt setup adatait statisztikai módszerekkel

## Korlátok

A tesztbattéria nem klinikai vagy diagnosztikai célú eszköz.

A mért mutatók viselkedéses teljesítménymutatók, amelyek számos tényezőtől függhetnek, beleértve:

- gyakorlási hatásokat,
- fáradtságot,
- motivációt,
- napszakot,
- környezeti zavaró tényezőket.

A rendszer elsődleges célja különböző környezeti vagy technikai konfigurációk összehasonlítása standardizált feladatok segítségével.

## Kimeneti adatok

A rendszer minden résztvevőhöz egy időbélyegzett CSV fájlt generál.

A napló tartalmazhatja:

- stimulus megjelenési eseményeket
- billentyűleütéseket
- egérmozgásokat
- egérkattintásokat
- reakcióidőket
- válaszpontosságot
- blokk- és feladatváltási eseményeket

A különböző tesztek eseményei egységes formátumban kerülnek rögzítésre, ami lehetővé teszi a későbbi statisztikai feldolgozást.