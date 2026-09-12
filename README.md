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
├── requirements.txt    # Dipendenza Python (Flask)
├── assets/
│   └── logo.webp       # Logo circolare del brand
└── fonts/
    └── GeistPixel-Circle.woff2   # Font fallback display locale
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

### Notifica via email (opzionale)

Se imposti queste variabili d'ambiente, ogni richiesta viene anche inoltrata via SMTP:

```bash
export SMTP_HOST=smtp.example.com
export SMTP_PORT=587
export SMTP_USER=hello@sitebuyld.com
export SMTP_PASS=****************
export CONTACT_TO=hello@sitebuyld.com   # destinatario (default: hello@sitebuyld.com)
```

Se le variabili SMTP non sono configurate il messaggio viene comunque salvato su file e il form apre sempre `mailto:` come fallback.

---

## Lingue

- Selezione lingua via pill en/header e dentro il menu mobile: **EN / IT / FR / ES / DE**
- Scelta persistente in `localStorage` (`sitebuyld.lang`), default `en`
- Tutti i testi della pagina (incluse headline, prezzi, FAQ, form) sono tradotti in `main.js` → dizionario `I18N`

---

## Personalizzazione rapida

- **Logo**: sostituisci `assets/logo.webp`
- **Prezzi**: testo nei blocchi `.plan` di `index.html` (il prezzo barrato è `.was`, quello attuale `.now`)
- **Email di contatto**: cerca `hello@sitebuyld.com` in `index.html`, `main.js` e `server.py`
- **Video di sfondo**: URL dentro `<video class="bg-video">` in `index.html` (CloudFront)
- **Metriche hero**: attributi `data-target` / `data-suffix` / `data-decimals` in `.stat`

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