# Macbeth – Your Own Mac Pet

Macbeth on kerge macOS-i ekraanilemmikloom: must šoti terjer elab läbipaistvas raamita aknas, püsib teiste akende kohal ning reageerib hiirele ainult oma nähtava silueti piires. Rakendus töötab ka enne päris spriidipildi lisamist — sel juhul kuvatakse sisseehitatud terjerilaadne varupilt.

## Võimalused

- läbipaistev, raamita ja alati pealmine macOS-i aken;
- nähtav kõigil macOS-i Spaces-töölaudadel ja toetatud täisekraanirakenduste kohal;
- macOS-i ülemise menüüriba ikoon, kust saab Macbethi näidata, juhtida ja sulgeda;
- 3×3 PNG sprite sheeti automaatne lõikamine üheksaks kaadriks;
- koera horisontaalne peegeldamine vastavalt liikumissuunale;
- vasaku hiirenupuga lohistamine ja lohistamise ajal jooksmisanimatsioon;
- läbipaistvad aknaosad lasevad hiireklikid allolevale rakendusele läbi;
- tegevusetuse olekumasin: 5 sekundi järel istumine ning 30–60 sekundit hiljem magamine;
- paremklõpsumenüü: **Wave**, **Rest**, **Sit**, **Random pose**, **Screenshot**, **Move on its own for 30 seconds** ja **Quit Macbeth**;
- avatud akna ekraanipilt väikese istuva Macbethi vesimärgiga, automaatne salvestus ja lõikelauale kopeerimine;
- topeltklõps paneb Macbethi lehvitama;
- hiirega Macbethi kohale liikudes valitakse 50/50 üks kahest istumispoosist ning 10 sekundi tegevusetuse järel läheb ta tagasi magama;
- 30-sekundiline iseseisev kõndimine/jooksmine koos suunamuutuste ja pausidega;
- spriidifaili puudumise või vigase PNG korral sisseehitatud varupilt.

## Nõuded

- macOS 12 või uuem;
- Python 3.9 või uuem (soovitatav 3.11 või 3.12);
- PyQt6.

> Pythonit on mugav paigaldada [python.org](https://www.python.org/downloads/macos/) paketiga või Homebrew abil. Valmis `.app` ei nõua lõppkasutajalt Pythonit.

## Kiirkäivitus Terminalis

Klooni repositoorium või ava Terminalis projekti kaust, seejärel käivita:

```bash
cd "/tee/Macbeth - Your own Mac Pet"
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 main.py
```

Kui `scottish_terrier_sprites.png` ei ole veel lisatud, käivitub rakendus varupildiga. Sulgemiseks tee koeral paremklõps ja vali **Quit Macbeth**.

### Kasulikud käivitusvalikud

```bash
# Kasuta mõnd muud 3×3 PNG-faili
python3 main.py --sprite "/täielik/tee/minu_spriidid.png"

# Muuda koera suurust (lubatud 64–512, vaikimisi 160)
python3 main.py --size 200

# Kuva laadimise diagnostika
python3 main.py --debug
```

## Sprite sheet

Pane läbipaistva taustaga PNG projekti juurkausta täpselt selle nimega:

```text
scottish_terrier_sprites.png
```

Pilt lõigatakse võrdseks 3×3 ruudustikuks. Parima tulemuse annab pilt, mille laius ja kõrgus jaguvad kolmega ning mille igas lahtris on koer sarnase suuruse, joonduse ja jalgealusega. Ruudustiku vaikekaardistus on:

| Lahter | Rida/veerg | Kasutus |
|---:|:---:|---|
| 0 | 1/1 | Walk/Run 1 |
| 1 | 1/2 | Sit / vaatab üles |
| 2 | 1/3 | Sit / keel väljas |
| 3 | 2/1 | Rest/Sleep |
| 4 | 2/2 | Sit / eestvaade |
| 5 | 2/3 | Idle/Walk 2 |
| 6 | 3/1 | Sit / külgvaade |
| 7 | 3/2 | Wave |
| 8 | 3/3 | Run 2 |

See kaardistus vastab repositooriumiga kaasas olevale pildile. **Sit** valib juhuslikult lahtri 1, 2, 4 või 6. Kui asenduspildi poosid on teises järjekorras, muuda `ANIMATION_FRAMES` ja `SIT_FRAME_CHOICES` väärtusi failis `macbeth_pet/animations.py`. Algset pilti ei pea eelnevalt tükeldama.

## Juhtimine

- **Lohistamine:** hoia koera peal vasakut hiirenuppu ja liiguta. Koer jookseb ja vaatab liikumise suunas.
- **Topeltklõps:** Wave.
- **Hiirega hõljumine:** Macbeth valib võrdselt kas viltuse peaga või eestvaates istumispoosi. Kui 10 sekundi jooksul uut tegevust ei tule, jääb ta uuesti magama.
- **Paremklõps:** tegevuste menüü.
- **Menüüriba ikoon:** klõpsa ekraani ülaservas Macbethi ikooni ja vali **Show Macbeth**, kui tahad ta uuesti nähtavale tuua. Samast menüüst saab kasutada põhilisi tegevusi ja rakenduse sulgeda.
- **Screenshot:** vali kaamerakursoriga avatud aken. Valmis PNG saab paremasse alanurka väikese istuva Macbethi, salvestatakse kausta `Pictures/Macbeth Screenshots` ning kopeeritakse lõikelauale. Valiku katkestamiseks vajuta `Esc`.
- **Move on its own for 30 seconds:** koer liigub praegusel ekraanil iseseisvalt ja pöördub servades tagasi. Lohistamine katkestab iseseisva liikumise.
- **Quit Macbeth:** lõpetab rakenduse.

Akna kuju arvutatakse jooksva kaadri alfakanalist. Seetõttu jõuavad koera ümber olevates läbipaistvates kohtades tehtud klikid alloleva aknani, kuid nähtav koer ise jääb lohistatavaks ja klõpsatavaks.

## Testid

Olekumasina testid ei ava graafilist akent:

```bash
python3 -m unittest discover -v
```

Graafilist käitumist tasub pärast oma sprite sheeti lisamist päris Macil käsitsi kontrollida: lohistamine mõlemas suunas, Docki erinevad asukohad, mitu monitori ning kõik paremklõpsumenüü valikud.

## Iseseisva `.app` faili loomine PyInstalleriga

Paigalda arendussõltuvused samasse virtuaalkeskkonda:

```bash
source .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
```

Seejärel loo rakendus kaasasoleva spec-failiga:

```bash
python3 -m PyInstaller --clean --noconfirm Macbeth.spec
```

Valmis rakendus asub siin:

```text
dist/Macbeth.app
```

Pärast build'i saad `Macbeth.app` faili Finderis tavapärase rakendusena avada — Terminali ei ole enam vaja. Lohista rakendus soovi korral kausta `/Applications`. Et Macbeth käivituks automaatselt koos Maciga, ava **System Settings → General → Login Items & Extensions**, vajuta **Open at Login** loendis `+` ja vali `Macbeth.app`. Seejärel töötab ta taustal seni, kuni valid koera paremklõpsumenüüst **Quit Macbeth**.

`Macbeth.spec` lisab `scottish_terrier_sprites.png` paketti ainult siis, kui fail build'i ajal olemas on. Ilma failita töötab ka pakendatud rakendus varupildiga. Kui tahad pilti hiljem ilma uut build'i tegemata vahetada, pane `scottish_terrier_sprites.png` Finderis `Macbeth.app` kõrvale ja käivita rakendus uuesti.

Esimesel käivitamisel võib macOS tundmatu arendaja rakenduse blokeerida. Enda arvutis testi jaoks tee rakendusel Finderis **Control-click → Open → Open**. Avalikuks levitamiseks tuleks `.app` allkirjastada Apple Developer ID sertifikaadiga ja notariseerida; see ei ole kohaliku build'i jaoks vajalik.

## Projekti struktuur

```text
.
├── main.py                       # käivituspunkt
├── Macbeth.spec                  # PyInstaller macOS-i retsept
├── requirements.txt              # rakenduse sõltuvus
├── requirements-dev.txt          # pakendamise tööriist
├── macbeth_pet/
│   ├── app.py                    # käsurida ja rakenduse käivitus
│   ├── animations.py             # 3×3 lõikamine, kaadrid, varupilt
│   ├── behavior.py               # puhas tegevusetuse olekumasin
│   ├── macos_overlay.py           # native always-on-top ja Spaces
│   ├── pet_window.py             # läbipaistev aken, hiir ja liikumine
│   └── screenshot.py             # ekraanipildi vesimärk ja failitee
└── tests/
    └── test_behavior.py
```

## Tõrkeotsing

**Koera asemel kuvatakse varupilt.** Kontrolli failinime, PNG loetavust ja asukohta. Käivita `python3 main.py --debug`, et näha, millist teed prooviti laadida.

**Animatsioonid ei vasta pildi poosidele.** Kohanda `ANIMATION_FRAMES` väärtusi failis `macbeth_pet/animations.py` vastavalt ülalolevale lahtrite numeratsioonile.

**Koer jääb Docki taha või valele monitorile.** Rakendus kasutab käivitamisel hiirekursori all oleva ekraani kasutatavat ala. Lohista koer soovitud ekraanile. macOS-i Spaces või täisekraanirežiim võivad alati-pealmise akna nähtavust süsteemi enda reeglite järgi piirata.

**Ekraanipilt on tühi või macOS ei luba seda teha.** Ava **System Settings → Privacy & Security → Screen & System Audio Recording** ja luba juurdepääs Terminalile või `Macbeth.app`-ile, sõltuvalt sellest, kuidas rakendus käivitati. Pärast loa muutmist käivita rakendus uuesti.

**Soovin rakenduse jõuga peatada.** Terminalist käivitades vajuta `Ctrl+C`; pakendatud rakenduse saab lõpetada ka Activity Monitorist.

