# Sitebuyld

Landing page + backend per **Sitebuyld** — siti web moderni costruiti con l'AI a prezzi stracciati, consegnati in 48 ore.

Design ispirato alla pagina Instagram [@sitebuyld_official](https://www.instagram.com/sitebuyld_official): hero full-screen con video in loop, font display dot-matrix, animazioni di reveal in stile "Intelligence Designed To Evolve", e interfaccia multilinguale **EN · IT · FR · ES · DE**.

---

## Struttura

```
.
├── index.html          # Landing page completa (hero + sezioni + form)
├── styles.css          # Stile, animazioni, responsive, reduced-motion
├── main.js             # i18n (5 lingue), count-up, scrollspy, reveal, menu mobile, form
├── server.py           # Backend Flask: file statici + API contatti
├── cms.py              # CMS locale: CLI per gestire contenuti e testi (vedi sotto)
├── requirements.txt    # Dipendenza Python (Flask)
├── assets/
│   └── logo.webp       # Logo circolare del brand
├── fonts/
│   └── GeistPixel-Circle.woff2   # Font fallback display locale
└── data/               # Dati CMS (vedi "CMS di gestione")
```

---

## Sezioni della landing

1. **Hero** — video CloudFront full-bleed, banner di fiducia, headline, subhead, CTA, 4 metriche con count-up
2. **Marquee** — strip scorrevole con i punti di forza
3. **Product** — feature cards + percorso "dal brief al lancio" in 4 step
4. **Pricing** — 3 piani (Landing €79 / Business €149 / Store €299), pagamento unico
5. **Case Studies** — mock di siti consegnati con risultati
6. **Testimonials** — recensioni con avatar
7. **FAQ** — accordion nativo
8. **CTA finale** — Instagram + email
9. **Contact** — canali diretti + form contatti
10. **Footer** — logo, social, selettore lingua

> Navigazione: la voce **Pricing** è stata aggiunta alla nav (Home · Product · Pricing · Case Studies · Contact). Tutti i link decorativi ancora `#` andranno collegati quando avrai definito destinazioni/piani reali.

---

## Avvio locale

### Solo anteprima statica (frontend)

```bash
cd sitebuyld
python3 -m http.server 8000
# apri http://localhost:8000
```

### Con backend (form contatti funzionante)

```bash
cd sitebuyld
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 server.py
# apri http://localhost:5000
```

---

## API

| Metodo | Endpoint       | Descrizione                                             |
| ------ | -------------- | ------------------------------------------------------- |
| GET    | `/`            | Serve `index.html`                                      |
| GET    | `/api/health`  | Health check (`{"ok": true}`)                           |
| POST   | `/api/contact` | Salva un messaggio in `messages.json` e notifica via email |

Richiesta `POST /api/contact`:

```json
{
  "name": "Marco",
  "email": "marco@example.com",
  "message": "Vorrei un sito per la mia osteria.",
  "bilingual": true
}
```

Ogni messaggio viene salvato in `messages.json` (nella root, non committato via `.gitignore`).

---

## CMS di gestione (`cms.py`)

Il sito si gestisce con un piccolo CMS locale (Python puro, nessuna dipendenza extra).
La **fonte di verità** sono due file in `data/`, generati ma **non committati** perché
contengono contenuti locali e credenziali:

| File                          | Commit? | Contenuto                                              |
| ----------------------------- | ------- | ------------------------------------------------------ |
| `data/content.json`           | no      | Testi (5 lingue), marquee, stats, piani, case, recensioni, FAQ, link |
| `data/settings.json`          | no      | Config email/SMTP + destinatario contatti              |
| `data/content.example.json`   | **sì**  | Struttura completa di `content.json` (template vuoto per i collaboratori) |
| `data/settings.example.json`  | **sì**  | Struttura completa di `settings.json`, **senza password** |
| `messages.json` / `.csv`      | no      | Messaggi del form / esportazione dei messaggi          |

`cms.py` rigenera *solo* le sezioni marcate in `index.html` (`<!--#CMS:...-->`) e il
dizionario `I18N` di `main.js` (`/*#CMS:i18n#*/`), quindi non tocca il resto del codice.
I file `.example.json` in `data/` vengono riscritti a ogni modifica così i collaboratori
vedono sempre la struttura dei dati su GitHub.

### Comandi principali

```bash
python3 cms.py status              # riepilogo del sito
python3 cms.py sync                # importa index.html/main.js → data/content.json e rigenera
python3 cms.py build               # rigenera index.html/main.js da data/content.json
python3 cms.py list marquee|plans|works|quotes|faq|stats|messages
python3 cms.py add marquee "testo"  python3 cms.py add plan|work|quote|faq|stat
python3 cms.py rm marquee|plan|work|quote|faq|stat <indice>
python3 cms.py set text <chiave> <lingua> "<valore>"     # es. nav.home, it, "Casa"
python3 cms.py set link <nome> <valore>                  # email, instagram, handle, x
python3 cms.py set plan <indice> {was|now|name|desc|featN} <lingua> <valore>
python3 cms.py messages export [percorso.csv]            # esporta i contatti in CSV
```

> **Importante per i collaboratori:** dopo un `pull`, `data/content.json` non esiste sul
> tuo clone. La prima volta esegui `python3 cms.py sync` per importare i contenuti attuali
> dal sito nei file `data/` (uguaglianza con `data/content.example.json` per il template).
> Le sezioni strutturate vengono poi gestite solo tramite `cms.py`, non a mano in `index.html`.

### Notifica via email (opzionale)

Se imposti queste variabili d'ambiente, ogni richiesta viene anche inoltrata via SMTP:

```bash
export SMTP_HOST=smtp.example.com
export SMTP_PORT=587
export SMTP_USER=example@sitebuyld.com
export SMTP_PASS=****************
export CONTACT_TO=example@sitebuyld.com   # destinatario (default: example@sitebuyld.com)
```

Se le variabili SMTP non sono configurate il messaggio viene comunque salvato su file e il form apre sempre `mailto:` come fallback.

---

## Lingue

- Selezione lingua via pill en/header e dentro il menu mobile: **EN / IT / FR / ES / DE**
- Scelta persistente in `localStorage` (`sitebuyld.lang`), default `en`
- Tutti i testi della pagina (incluse headline, prezzi, FAQ, form) sono tradotti in `main.js` → dizionario `I18N`

---

## Personalizzazione rapida

> Le sezioni con cursore (piani, case, recensioni, FAQ, stats, marquee, link) e i testi
> multilingua vanno modificati tramite `cms.py` (o `data/content.json`), NON a mano in
> `index.html`/`main.js`: un `sync`/`build` successivo li sovrascriverebbe.

- **Logo**: sostituisci `assets/logo.webp`
- **Prezzi**: `python3 cms.py list plans` poi `python3 cms.py set plan ...` oppure edit di `data/content.json`
- **Email di contatto**: `python3 cms.py set link email <nuova@email.com>` (aggiorna tutto il sito)
- **Video di sfondo**: URL dentro `<video class="bg-video">` in `index.html` (CloudFront)
- **Metriche hero**: edit di `data/content.json` → `stats` (o `python3 cms.py set plan ...` analoghi)

---

## Deploy

### Backend (consigliato per form + SMTP)
Railway, Render, Fly.io o qualsiasi host Python con `requirements.txt` e avvio `python server.py`. Imposta `PORT` (e le variabili SMTP se vuoi le email).

### Solo frontend
Qualsiasi hosting statico (Vercel, Netlify, GitHub Pages) — la pagina funziona da sola; il form farà fallback a `mailto:`.

---

## Tech stack

- HTML + CSS + vanilla JS (nessun framework, nessun build step)
- Font: **Inter** (Google Fonts), **BubbledotICG-FinePos** (CDN OnlineWebFonts), **Geist Pixel Circle** (locale, fallback)
- Icone: **Font Awesome 6.5.2** (cdnjs)
- Backend: **Flask** (Python 3.10+)

---

© 2026 Sitebuyld