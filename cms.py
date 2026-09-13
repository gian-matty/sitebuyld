#!/usr/bin/env python3
"""sitebuyld CMS — engine + CLI per gestire il sito.

Motore condiviso tra il pannello web (admin.py) e la CLI.
Source of truth: data/content.json + data/settings.json.
Ogni modifica rigenera `index.html` e `main.js` (scrittura diretta nei file).
"""

import argparse
import csv
import html as html_mod
import json
import os
import re
import sys
import csv as _csv

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
CONTENT_FILE = os.path.join(DATA_DIR, "content.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
INDEX_FILE = os.path.join(BASE, "index.html")
MAINJS_FILE = os.path.join(BASE, "main.js")
MESSAGES_FILE = os.path.join(BASE, "messages.json")

LANGS = ["en", "it", "fr", "es", "de"]

# ------------------------------------------------ utilities

def esc_html(value):
    return html_mod.escape(str(value), quote=True)


def esc_js(value):
    return json.dumps(str(value), ensure_ascii=False)


def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def empty_multi():
    return {lang: "" for lang in LANGS}


DEFAULT_SETTINGS = {
    "contact_to": "example@sitebuyld.com",
    "smtp_host": "smtp.example.com",
    "smtp_port": 587,
    "smtp_user": "",
    "smtp_pass": "",
    "smtp_from": "Sitebuyld <no-reply@example.com>",
    "smtp_use_tls": True,
}


def load_settings():
    return load_json(SETTINGS_FILE, dict(DEFAULT_SETTINGS))


def save_settings(settings):
    save_json(SETTINGS_FILE, settings)


def write_examples(content):
    example_content = json.loads(json.dumps(content))
    example_paths = {
        CONTENT_FILE: "content.example.json",
    }
    for target, filename in example_paths.items():
        path = os.path.join(DATA_DIR, filename)
        save_json(path, example_content)

    settings_example = {k: v for k, v in load_settings().items()}
    settings_example["smtp_pass"] = ""
    save_json(os.path.join(DATA_DIR, "settings.example.json"), settings_example)


def save_content(content):
    save_json(CONTENT_FILE, content)
    write_examples(content)


def is_multi(value):
    return isinstance(value, dict) and set(value) == set(LANGS)


def lang_value(struct, field, lang):
    val = struct.get(field, {})
    if not is_multi(val):
        val = empty_multi()
    return val.get(lang, val.get("en", ""))


# ------------------------------------------------ I18N parsing (seed)

def parse_i18n(src):
    m = re.search(r"const I18N = \{(.*?)\n\};", src, re.S)
    if not m:
        return {}
    block = m.group(1)
    langs = {}
    for lm in re.finditer(r"^\s{2}(\w+): \{(.*?)^\s{2}\},", block, re.S | re.M):
        lang, body = lm.group(1), lm.group(2)
        keys = {}
        for km in re.finditer(r'"([^"]+)"\s*:\s*("(?:[^"\\]|\\.)*")', body):
            try:
                keys[km.group(1)] = json.loads(km.group(2))
            except ValueError:
                continue
        langs[lang] = keys
    return langs


STRUCT_KEY = re.compile(r"^(?:stats|price|work|tst|faq)\.(?:\w)?\d+")


def classify_key(key):
    if key.startswith("stats."):
        return "stats"
    if re.match(r"^price\.p\d+", key):
        return "plan"
    if re.match(r"^work\.\d+", key):
        return "work"
    if re.match(r"^tst\.\d+", key):
        return "quote"
    if re.match(r"^faq\.\d+", key):
        return "faq"
    return "text"


# ------------------------------------------------ index.html parsing (seed)

STAT_RE = re.compile(
    r'<div class="stat anim" style="--d:\s*([\d.]+)s"'
    r'\s+data-target="([\d.]+)"\s+data-decimals="(\d+)"\s+data-suffix="([^"]*)">'
    r'\s*<span class="s-icon"[^>]*>(.*?)</span>'
    r'\s*<span class="s-value">[^<]*</span>'
    r'\s*<span class="s-label" data-i18n="(stats\.\d+)">[^<]*</span>'
    r'\s*</div>',
    re.S,
)

PLAN_RE = re.compile(
    r'<article class="plan(?: featured)? r" style="--d:\s*([\d.]+)s">'
    r"(?:\s*<span class=\"plan-tag\"[^>]*>.*?</span>)?"
    r'\s*<h3 class="plan-name" data-i18n="(price\.p\d+name)">(.*?)</h3>'
    r'\s*<p class="plan-desc" data-i18n="(price\.p\d+desc)">(.*?)</p>'
    r'\s*<div class="plan-price">'
    r'\s*<span class="was"[^>]*>(.*?)</span>'
    r'\s*<span class="now">.*?<i[^>]*>(.*?)</i>(.*?)</span>'
    r"\s*</div>"
    r"\s*<ul class=\"plan-feats\">(.*?)</ul>",
    re.S,
)

WORK_RE = re.compile(
    r'<article class="work r" style="--d:\s*([\d.]+)s">'
    r'\s*<div class="browser"[^>]*>.*?<span class="b-url">(.*?)</span>\s*</div>'
    r'\s*<div class="work-body">'
    r'\s*<h3 data-i18n="(work\.\d+name)">(.*?)</h3>'
    r'\s*<p data-i18n="(work\.\d+desc)">(.*?)</p>'
    r'\s*<div class="tags">(.*?)</div>'
    r"\s*</div>"
    r"\s*</article>",
    re.S,
)

QUOTE_RE = re.compile(
    r'<figure class="quote r" style="--d:\s*([\d.]+)s">'
    r'\s*<span class="q-stars"[^>]*>(.*?)</span>'
    r'\s*<blockquote data-i18n="(tst\.\d+q)">(.*?)</blockquote>'
    r'\s*<figcaption>'
    r'\s*<span class="q-avatar"[^>]*>(.*?)</span>'
    r'\s*<span><strong data-i18n="(tst\.\d+n)">.*?</strong> <em data-i18n="(tst\.\d+r)">.*?</em></span>'
    r"\s*</figcaption>"
    r"\s*</figure>",
    re.S,
)

FAQ_RE = re.compile(
    r'<details class="r" style="--d:\s*([\d.]+)s">'
    r'\s*<summary data-i18n="(faq\.\d+q)">.*?</summary>'
    r'\s*<p data-i18n="(faq\.\d+a)">.*?</p>'
    r"\s*</details>",
    re.S,
)


def strip_html(text):
    return re.sub(r"<[^>]+>", "", text)


def parse_index(src):
    data = {}

    marquee = re.search(r'<div class="marquee-track">(.*?)</div>', src, re.S)
    items = []
    if marquee:
        for sm in re.finditer(r"<span>(.*?)</span>", marquee.group(1), re.S):
            items.append(strip_html(sm.group(1)))
        data["marquee"] = items[: len(items) // 2]

    stats = []
    for sm in STAT_RE.finditer(src):
        stats.append(
            {
                "icon": sm.group(5).strip(),
                "target": float(sm.group(2)),
                "decimals": int(sm.group(3)),
                "suffix": sm.group(4),
            }
        )
    data["stats"] = stats

    plans = []
    for pm in PLAN_RE.finditer(src):
        feats_html = pm.group(9)
        nfeats = len(re.findall(r"<li", feats_html))
        was_text, cur_text, now_text = pm.group(6), pm.group(7), pm.group(8)
        was = int(re.sub(r"[^0-9]", "", was_text) or 0)
        now = int(re.sub(r"[^0-9]", "", now_text) or 0)
        currency = re.sub(r"[0-9\s]", "", was_text) or "€"
        plans.append(
            {
                "featured": " featured" in pm.group(0),
                "was": was,
                "now": now,
                "feat_count": nfeats,
            }
        )
        data["currency"] = currency
    data["plans"] = plans

    works = []
    for wm in WORK_RE.finditer(src):
        tags = [strip_html(t) for t in re.findall(r"<span[^>]*>(.*?)</span>", wm.group(7), re.S)]
        works.append({"url": strip_html(wm.group(2)), "tag_count": len(tags)})
    data["works"] = works

    quotes = []
    for qm in QUOTE_RE.finditer(src):
        quotes.append(
            {
                "stars": qm.group(2).count("*"),
                "avatar": strip_html(qm.group(5)),
            }
        )
    data["quotes"] = quotes

    faq_count = len(FAQ_RE.findall(src))
    data["faq_count"] = faq_count

    ig = re.search(r"https://www\.instagram\.com/[A-Za-z0-9_.-]+", src)
    email = re.search(r"mailto:([^\"']+)", src)
    handle = re.search(r">@([^<]+)</span>", src)
    xmatch = re.search(r'<a href="([^"]*)"[^>]*>\s*<i class="fa-brands fa-x-twitter"', src)
    data["links"] = {
        "instagram": ig.group(0) if ig else "https://www.instagram.com/",
        "handle": handle.group(1) if handle else "",
        "email": email.group(1) if email else "example@sitebuyld.com",
        "x": xmatch.group(1) if xmatch else "#",
    }
    return data


# ------------------------------------------------ content building

def build_content(i18n, index):
    langs = i18n or {lang: {} for lang in LANGS}
    texts = {lang: {} for lang in LANGS}

    plans = []
    works = []
    quotes = []
    faqs = []
    stats = list(index.get("stats", []))

    for lang in LANGS:
        keys = langs.get(lang, {})
        for key, val in keys.items():
            kind = classify_key(key)
            if kind != "text":
                continue
            texts[lang][key] = val

    for i, stat in enumerate(stats):
        stat["label"] = {}
        for lang in LANGS:
            stat["label"][lang] = langs.get(lang, {}).get("stats.%d" % (i + 1), "")

    for i, plan in enumerate(index.get("plans", [])):
        idx = i + 1
        p = {"featured": plan["featured"], "was": plan["was"], "now": plan["now"]}
        out = {}
        for lang in LANGS:
            d = langs.get(lang, {})
            base = "price.p%d" % idx
            out["name"] = out.get("name", {})
            out["desc"] = out.get("desc", {})
            out["name"][lang] = d.get(base + "name", "")
            out["desc"][lang] = d.get(base + "desc", "")
            feats = []
            for j in range(1, plan["feat_count"] + 1):
                feats.append(d.get("%sf%d" % (base, j), ""))
            out.setdefault("feats", {})[lang] = feats
        p.update(out)
        plans.append(p)

    for i, work in enumerate(index.get("works", [])):
        idx = i + 1
        w = {"url": work["url"]}
        out = {}
        for lang in LANGS:
            d = langs.get(lang, {})
            base = "work.%d" % idx
            out.setdefault("name", {})[lang] = d.get(base + "name", "")
            out.setdefault("desc", {})[lang] = d.get(base + "desc", "")
            tags = []
            for j in range(1, work["tag_count"] + 1):
                tags.append(d.get("%st%d" % (base, j), ""))
            out.setdefault("tags", {})[lang] = tags
        w.update(out)
        works.append(w)

    for i, quote in enumerate(index.get("quotes", [])):
        idx = i + 1
        q = {"stars": quote["stars"], "avatar": quote["avatar"]}
        out = {}
        for lang in LANGS:
            d = langs.get(lang, {})
            base = "tst.%d" % idx
            out.setdefault("q", {})[lang] = d.get(base + "q", "")
            out.setdefault("name", {})[lang] = d.get(base + "n", "")
            out.setdefault("role", {})[lang] = d.get(base + "r", "")
        q.update(out)
        quotes.append(q)

    for i in range(index.get("faq_count", 0)):
        idx = i + 1
        f = {}
        for lang in LANGS:
            d = langs.get(lang, {})
            base = "faq.%d" % idx
            f.setdefault("q", {})[lang] = d.get(base + "q", "")
            f.setdefault("a", {})[lang] = d.get(base + "a", "")
        faqs.append(f)

    content = {
        "texts": texts,
        "marquee": index.get("marquee", []),
        "currency": index.get("currency", "€"),
        "stats": stats,
        "plans": plans,
        "works": works,
        "quotes": quotes,
        "faq": faqs,
        "links": index.get(
            "links",
            {
                "instagram": "https://www.instagram.com/",
                "handle": "@sitebuyld",
                "email": "example@sitebuyld.com",
                "x": "#",
            },
        ),
    }
    return content


def ensure_content():
    if os.path.exists(CONTENT_FILE):
        return load_json(CONTENT_FILE)
    return sync_content(build=True)


def sync_content(build=False):
    i18n = parse_i18n(open(MAINJS_FILE, "r", encoding="utf-8").read())
    index = parse_index(open(INDEX_FILE, "r", encoding="utf-8").read())
    content = build_content(i18n, index)
    save_content(content)
    if build:
        render_all(content)
    return content


# ------------------------------------------------ rendering

def delay(i, step=0.08):
    return round(0.05 + step * i, 2)


def render_marquee(items):
    if not items:
        items = ["Sitebuyld"]
    line = "".join('<span>%s</span>' % esc_html(item) for item in items)
    return (
        '      <div class="marquee-track">\n'
        "        %s\n"
        "        %s\n"
        "      </div>" % (line, line)
    )


def render_stats(stats):
    blocks = []
    for i, stat in enumerate(stats):
        label = stat.get("label", {})
        decimals = int(stat.get("decimals", 0))
        zero = "0" + ("." + "0" * decimals if decimals else "")
        icon = stat.get("icon", "")
        github_neutral = ""
        html = (
            '        <div class="stat anim" style="--d: {ds}s" data-target="{target}" '
            'data-decimals="{dec}" data-suffix="{suffix}">\n'
'          <span class="s-icon" aria-hidden="true">{icon}</span>\n'
        '          <span class="s-value">{zero}{suffix}</span>\n'
        '          <span class="s-label" data-i18n="stats.{n}">{lbl}</span>\n'
        "        </div>"
    ).format(
            ds=0.5 + 0.08 * i,
            target="{:g}".format(stat.get("target", 0)),
            dec=decimals,
            suffix=esc_html(stat.get("suffix", "")),
            icon=icon,
            zero=zero,
            n=i + 1,
            lbl=esc_html(label.get("en", "")),
        )
        blocks.append(html)
    return "      <footer class=\"stats\">\n%s\n      </footer>" % "\n".join(blocks)


def render_plan(plan, i):
    base = "price.p%d" % (i + 1)
    featured = ' featured' if plan.get("featured") else ""
    tag = (
        '        <span class="plan-tag" data-i18n="price.reco">%s</span>\n'
        % esc_html(plan.get("tag", {}).get("en", "") or "Most popular")
        if plan.get("featured")
        else ""
    )
    feats = plan.get("feats", {})
    feats_html = "\n".join(
        '            <li data-i18n="price.p{f}f{j}">{t}</li>'.format(
            f=i + 1, j=j + 1, t=esc_html(feats.get("en", [])[j])
        )
        for j in range(len(feats.get("en", [])))
    )
    currency = plan.get("currency", "€")
    html = (
        '        <article class="plan{feat} r" style="--d: {d}s">\n'
        "{tag}          <h3 class=\"plan-name\" data-i18n=\"{base}name\">{name}</h3>\n"
        '          <p class="plan-desc" data-i18n="{base}desc">{desc}</p>\n'
        '          <div class="plan-price">\n'
        '            <span class="was" aria-hidden="true">{was}</span>\n'
        '            <span class="now"><i>{cur}</i>{now}</span>\n'
        "          </div>\n"
        '          <ul class="plan-feats">\n{feats}\n          </ul>\n'
        '          <a class="btn" href="#contact" data-i18n="price.cta">Order this site</a>\n'
        "        </article>"
    ).format(
        feat=featured,
        d=delay(i),
        tag=tag,
        base=base,
        name=esc_html(plan.get("name", {}).get("en", "")),
        desc=esc_html(plan.get("desc", {}).get("en", "")),
        was=esc_html(currency + str(plan.get("was", 0))),
        cur=esc_html(currency),
        now=esc_html(plan.get("now", 0)),
        feats=feats_html,
    )
    return html


def render_work(work, i):
    base = "work.%d" % (i + 1)
    tags = work.get("tags", {})
    tags_html = "\n".join(
        '              <span data-i18n="work.{i}t{j}">{t}</span>'.format(
            i=i + 1, j=j + 1, t=esc_html(tags.get("en", [])[j])
        )
        for j in range(len(tags.get("en", [])))
    )
    html = (
        '        <article class="work r" style="--d: {d}s">\n'
        '          <div class="browser" aria-hidden="true">\n'
        '            <span class="b-dot"></span><span class="b-dot"></span><span class="b-dot"></span>\n'
        '            <span class="b-url">{url}</span>\n'
        "          </div>\n"
        '          <div class="work-body">\n'
        '            <h3 data-i18n="{base}name">{name}</h3>\n'
        '            <p data-i18n="{base}desc">{desc}</p>\n'
        '            <div class="tags">\n{tags}\n            </div>\n'
        "          </div>\n"
        "        </article>"
    ).format(
        d=delay(i, 0.10),
        url=esc_html(work.get("url", "")),
        base=base,
        name=esc_html(work.get("name", {}).get("en", "")),
        desc=esc_html(work.get("desc", {}).get("en", "")),
        tags=tags_html,
    )
    return html


def render_quote(quote, i):
    base = "tst.%d" % (i + 1)
    stars = "*" * int(quote.get("stars", 3))
    html = (
        '        <figure class="quote r" style="--d: {d}s">\n'
        '          <span class="q-stars" aria-hidden="true">{stars}</span>\n'
        '          <blockquote data-i18n="{base}q">{q}</blockquote>\n'
        "          <figcaption>\n"
        '            <span class="q-avatar" aria-hidden="true">{avatar}</span>\n'
        '            <span><strong data-i18n="{base}n">{n}</strong> <em data-i18n="{base}r">{r}</em></span>\n'
        "          </figcaption>\n"
        "        </figure>"
    ).format(
        d=delay(i, 0.10),
        stars=esc_html(stars),
        base=base,
        q=esc_html(quote.get("q", {}).get("en", "")),
        avatar=esc_html(quote.get("avatar", "?")),
        n=esc_html(quote.get("name", {}).get("en", "")),
        r=esc_html(quote.get("role", {}).get("en", "")),
    )
    return html


def render_faq(faq, i):
    base = "faq.%d" % (i + 1)
    html = (
        '        <details class="r" style="--d: {d}s">\n'
        '          <summary data-i18n="{base}q">{q}</summary>\n'
        '          <p data-i18n="{base}a">{a}</p>\n'
        "        </details>"
    ).format(
        d=delay(i, 0.05),
        base=base,
        q=esc_html(faq.get("q", {}).get("en", "")),
        a=esc_html(faq.get("a", {}).get("en", "")),
    )
    return html


def render_contact_rows(links):
    ig = links.get("instagram", "")
    email = links.get("email", "")
    handle = links.get("handle", "")
    if handle and not handle.startswith("@"):
        handle = "@" + handle
    if not handle:
        handle = "@" + ig.rstrip("/").rsplit("/", 1)[-1] if ig else "@sitebuyld"
    html = (
        '          <a class="contact-row" href="{ig}" target="_blank" rel="noopener">\n'
        '            <i class="fa-brands fa-instagram" aria-hidden="true"></i>\n'
        "            <span>{handle}</span>\n"
        "          </a>\n"
        '          <a class="contact-row" href="mailto:{email}">\n'
        '            <i class="fa-solid fa-envelope" aria-hidden="true"></i>\n'
        "            <span>{email}</span>\n"
        "          </a>"
    ).format(ig=esc_html(ig), handle=esc_html(handle), email=esc_html(email))
    return html


def render_socials(links):
    html = (
        '        <a href="{ig}" target="_blank" rel="noopener" aria-label="Instagram">\n'
        '          <i class="fa-brands fa-instagram" aria-hidden="true"></i>\n'
        "        </a>\n"
        '        <a href="mailto:{email}" aria-label="Email">\n'
        '          <i class="fa-solid fa-envelope" aria-hidden="true"></i>\n'
        "        </a>\n"
        '        <a href="{x}" aria-label="X / Twitter">\n'
        '          <i class="fa-brands fa-x-twitter" aria-hidden="true"></i>\n'
        "        </a>"
    ).format(
        ig=esc_html(links.get("instagram", "")),
        email=esc_html(links.get("email", "")),
        x=esc_html(links.get("x", "#")),
    )
    return html


def replace_marked(src, name, inner, style="html"):
    if style == "html":
        start = "<!--#CMS:%s#-->" % name
    else:
        start = "/*#CMS:%s#*/" % name
    end = start.replace("#CMS:", "#/CMS:")
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    m = pattern.search(src)
    if not m:
        raise ValueError("marker %s not found in file" % name)
    indent = re.match(r"[ \t]*", m.group(0)).group(0)
    return pattern.sub(start + "\n" + inner + "\n" + indent + end, src)


def render_index(content):
    src = open(INDEX_FILE, "r", encoding="utf-8").read()

    src = replace_marked(src, "marquee", render_marquee(content.get("marquee", [])))
    src = replace_marked(src, "stats", render_stats(content.get("stats", [])))
    rows = []
    for i, p in enumerate(content.get("plans", [])):
        rows.append(render_plan(p, i))
    src = replace_marked(src, "plans", "\n".join(rows))

    rows = []
    for i, w in enumerate(content.get("works", [])):
        rows.append(render_work(w, i))
    src = replace_marked(src, "works", "\n".join(rows))

    rows = []
    for i, q in enumerate(content.get("quotes", [])):
        rows.append(render_quote(q, i))
    src = replace_marked(src, "quotes", "\n".join(rows))

    rows = []
    for i, f in enumerate(content.get("faq", [])):
        rows.append(render_faq(f, i))
    src = replace_marked(src, "faq", "\n".join(rows))

    src = replace_marked(src, "contact-rows", render_contact_rows(content.get("links", {})))
    src = replace_marked(src, "socials", render_socials(content.get("links", {})))

    links = content.get("links", {})
    ig = links.get("instagram", "")
    email = links.get("email", "")
    if ig:
        src = re.sub(r"https://www\.instagram\.com/[A-Za-z0-9_.-]+", ig, src)
    if email:
        src = re.sub(r"mailto:[^\"']+", "mailto:" + email, src)

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(src)


def build_i18n_js(content):
    texts = content.get("texts", {})
    plans = content.get("plans", [])
    works = content.get("works", [])
    quotes = content.get("quotes", [])
    faqs = content.get("faq", [])
    stats = content.get("stats", [])

    struct = {}
    for lang in LANGS:
        keys = {}
        for i, stat in enumerate(stats):
            keys["stats.%d" % (i + 1)] = lang_value(stat, "label", lang)
        for i, plan in enumerate(plans):
            base = "price.p%d" % (i + 1)
            keys[base + "name"] = lang_value(plan, "name", lang)
            keys[base + "desc"] = lang_value(plan, "desc", lang)
            feats = plan.get("feats", {}).get(lang, [])
            for j, feat in enumerate(feats):
                keys["%sf%d" % (base, j + 1)] = feat
        for i, work in enumerate(works):
            base = "work.%d" % (i + 1)
            keys[base + "name"] = lang_value(work, "name", lang)
            keys[base + "desc"] = lang_value(work, "desc", lang)
            tags = work.get("tags", {}).get(lang, [])
            for j, tag in enumerate(tags):
                keys["%st%d" % (base, j + 1)] = tag
        for i, quote in enumerate(quotes):
            base = "tst.%d" % (i + 1)
            keys[base + "q"] = lang_value(quote, "q", lang)
            keys[base + "n"] = lang_value(quote, "name", lang)
            keys[base + "r"] = lang_value(quote, "role", lang)
        for i, faq in enumerate(faqs):
            base = "faq.%d" % (i + 1)
            keys[base + "q"] = lang_value(faq, "q", lang)
            keys[base + "a"] = lang_value(faq, "a", lang)
        struct[lang] = keys

    langs_js = []
    for lang in LANGS:
        merged = {}
        merged.update(content.get("texts", {}).get(lang, {}))
        merged.update(struct.get(lang, {}))
        pairs = ["      %s: %s," % (esc_js(k), esc_js(v)) for k, v in merged.items()]
        langs_js.append("  %s: {\n%s\n  }," % (lang, "\n".join(pairs)))
    return "const I18N = {\n" + "\n".join(langs_js) + "\n};"


def render_mainjs(content):
    src = open(MAINJS_FILE, "r", encoding="utf-8").read()
    email = content.get("links", {}).get("email", "example@sitebuyld.com")
    src = re.sub(r'const CONTACT_EMAIL = "[^"]*";', 'const CONTACT_EMAIL = %s;' % esc_js(email), src, count=1)
    src = replace_marked(src, "i18n", build_i18n_js(content), style="js")
    with open(MAINJS_FILE, "w", encoding="utf-8") as f:
        f.write(src)


def render_all(content):
    render_index(content)
    render_mainjs(content)


# ------------------------------------------------ messages helpers

def load_messages():
    msgs = load_json(MESSAGES_FILE, [])
    return msgs if isinstance(msgs, list) else []


def save_messages(msgs):
    save_json(MESSAGES_FILE, msgs)


# ------------------------------------------------ CLI

def cmd_status(args):
    content = ensure_content()
    msgs = load_messages()
    print("sitebuyld CMS")
    print("  marquee items :", len(content.get("marquee", [])))
    print("  stats         :", len(content.get("stats", [])))
    print("  plans         :", len(content.get("plans", [])))
    print("  works         :", len(content.get("works", [])))
    print("  quotes        :", len(content.get("quotes", [])))
    print("  faq           :", len(content.get("faq", [])))
    print("  email         :", content.get("links", {}).get("email", ""))
    print("  messages      :", len(msgs), "(unread:", sum(1 for m in msgs if not m.get("read")), ")")


def cmd_sync(args):
    content = sync_content(build=not args.no_build)
    print("content synced to data/content.json (%d langs)" % len(content["texts"]))
    if not args.no_build:
        print("index.html and main.js regenerated")


def cmd_build(args):
    content = ensure_content()
    render_all(content)
    print("index.html and main.js regenerated from data/content.json")


def mutate(content):
    save_content(content)
    render_all(content)


def cmd_list(args):
    content = ensure_content()
    if args.what == "marquee":
        for i, item in enumerate(content.get("marquee", [])):
            print(i, item)
    elif args.what == "plans":
        for i, p in enumerate(content.get("plans", [])):
            print(i, p.get("featured") and "[featured]" or "", p.get("name", {}).get("en", ""), p.get("currency", "€") + str(p.get("now", 0)))
    elif args.what == "works":
        for i, w in enumerate(content.get("works", [])):
            print(i, w.get("name", {}).get("en", ""), w.get("url", ""))
    elif args.what == "quotes":
        for i, q in enumerate(content.get("quotes", [])):
            print(i, q.get("name", {}).get("en", ""))
    elif args.what == "faq":
        for i, f in enumerate(content.get("faq", [])):
            print(i, f.get("q", {}).get("en", ""))
    elif args.what == "stats":
        for i, s in enumerate(content.get("stats", [])):
            print(i, s.get("target"), s.get("suffix", ""), s.get("label", {}).get("en", ""))
    elif args.what == "messages":
        for m in load_messages():
            print(m.get("id", "?"), "R" if m.get("read") else "U", m.get("name"), m.get("email"), m.get("created_at"))


def cmd_add(args):
    content = ensure_content()
    if args.what == "marquee":
        if not getattr(args, "value", "") and not args.values:
            raise SystemExit("usage: cms.py add marquee <text>")
        v = args.values[-1] if args.values else args.value
        content.setdefault("marquee", []).append(v)
        mutate(content)
        print("marquee item added:", v)
    elif args.what == "plan":
        per = ["New plan"] * len(LANGS)
        content.setdefault("plans", []).append({
            "featured": False, "was": 99, "now": 49,
            "name": dict(zip(LANGS, per)),
            "desc": dict(zip(LANGS, ["New plan description."] * len(LANGS))),
            "feats": {lang: ["Feature 1"] for lang in LANGS},
        })
        mutate(content)
        print("plan added")
    elif args.what == "work":
        content.setdefault("works", []).append({
            "url": "example.com",
            "name": dict(zip(LANGS, ["New project"] * len(LANGS))),
            "desc": dict(zip(LANGS, ["Case study description."] * len(LANGS))),
            "tags": {lang: ["Tag"] for lang in LANGS},
        })
        mutate(content)
        print("work added")
    elif args.what == "quote":
        content.setdefault("quotes", []).append({
            "stars": 3, "avatar": "?",
            "q": dict(zip(LANGS, ["Quoted text."] * len(LANGS))),
            "name": dict(zip(LANGS, ["Name"] * len(LANGS))),
            "role": dict(zip(LANGS, ["Role"] * len(LANGS))),
        })
        mutate(content)
        print("quote added")
    elif args.what == "faq":
        content.setdefault("faq", []).append({
            "q": dict(zip(LANGS, ["Question"] * len(LANGS))),
            "a": dict(zip(LANGS, ["Answer"] * len(LANGS))),
        })
        mutate(content)
        print("faq added")
    elif args.what == "stat":
        content.setdefault("stats", []).append({
            "icon": "*", "target": 1, "decimals": 0, "suffix": "",
            "label": dict(zip(LANGS, ["Stat label"] * len(LANGS))),
        })
        mutate(content)
        print("stat added")
    else:
        raise SystemExit("unknown: %s" % args.what)


def cmd_rm(args):
    content = ensure_content()
    key = {"marquee": "marquee", "plan": "plans", "work": "works", "quote": "quotes", "faq": "faq", "stat": "stats"}[args.what]
    items = content.get(key, [])
    if not (0 <= args.index < len(items)):
        raise SystemExit("index out of range")
    removed = items.pop(args.index)
    mutate(content)
    print("removed %s[%d]" % (key, args.index))


def cmd_set(args):
    content = ensure_content()
    what = args.set_what
    if not what:
        raise SystemExit("usage: cms.py set {text|link|plan} ...")
    value = " ".join(getattr(args, "value", []) or []).strip()

    if what == "text":
        lang = canonical_lang(args.lang)
        content["texts"].setdefault(lang, {})[args.key] = value
        print("texts[%s][%s] = %r" % (lang, args.key, value))
    elif what == "link":
        content.setdefault("links", {})[args.name] = value
        print("links[%s] = %r" % (args.name, value))
    elif what == "plan":
        plan = content["plans"][args.index]
        field, lang = args.field, args.lang
        if field in ("was", "now"):
            plan[field] = int(float(value))
        elif field == "featured":
            plan[field] = value.lower() in ("1", "true", "yes", "si")
        elif field == "name":
            plan.setdefault("name", {})[lang] = value
        elif field == "desc":
            plan.setdefault("desc", {})[lang] = value
        elif field.startswith("feat"):
            n = int(field[4:]) - 1
            feats = plan.setdefault("feats", {}).setdefault(lang, [])
            while len(feats) <= n:
                feats.append("")
            feats[n] = value
        else:
            raise SystemExit("unknown plan field: %s" % field)
        print("plan updated")
    else:
        raise SystemExit("unknown set target: %s" % what)
    mutate(content)


def canonical_lang(name):
    name = name.lower()
    return name if name in LANGS else "en"


def cmd_messages(args):
    msgs = load_messages()
    if args.action == "export":
        path = args.csv or (os.path.join(BASE, "messages.csv"))
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "created_at", "name", "email", "bilingual", "message"])
            for m in msgs:
                writer.writerow([
                    m.get("id", ""), m.get("created_at", ""), m.get("name", ""),
                    m.get("email", ""), m.get("bilingual", False), m.get("message", ""),
                ])
        print("exported %d messages to %s" % (len(msgs), path))
    elif args.action == "rm":
        before = len(msgs)
        msgs = [m for m in msgs if m.get("id") != args.id]
        print("removed %d message(s)" % (before - len(msgs)))
        save_messages(msgs)
    elif args.action == "read":
        for m in msgs:
            if m.get("id") == args.id:
                m["read"] = True
                save_messages(msgs)
                print("marked as read")
                return
        raise SystemExit("message not found")
    else:
        cmd_list(args)


def build_parser():
    p = argparse.ArgumentParser(prog="cms.py", description="sitebuyld CMS")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("status", help="show site status")
    sp = sub.add_parser("sync", help="import site content into data/content.json")
    sp.add_argument("--no-build", action="store_true", help="only update json, do not regenerate files")
    sub.add_parser("build", help="regenerate index.html/main.js from data/content.json")

    lp = sub.add_parser("list", help="list items")
    lp.add_argument("what", choices=["marquee", "plans", "works", "quotes", "faq", "stats", "messages"])

    ap = sub.add_parser("add", help="add an item")
    ap.add_argument("what", choices=["marquee", "plan", "work", "quote", "faq", "stat"])
    ap.add_argument("value", nargs="?", default="")
    ap.add_argument("values", nargs="*")

    rp = sub.add_parser("rm", help="remove an item by index")
    rp.add_argument("what", choices=["marquee", "plan", "work", "quote", "faq", "stat"])
    rp.add_argument("index", type=int)

    sp2 = sub.add_parser("set", help="set a value (run with no subcommand to see help)")
    st_sub = sp2.add_subparsers(dest="set_what")

    tp = st_sub.add_parser("text", help="set a text key for a language")
    tp.add_argument("key")
    tp.add_argument("lang")
    tp.add_argument("value", nargs="*")

    lp = st_sub.add_parser("link", help="set a site link/email/handle")
    lp.add_argument("name")
    lp.add_argument("value", nargs="*")

    pp = st_sub.add_parser("plan", help="set a plan field")
    pp.add_argument("index", type=int)
    pp.add_argument("field")  # was | now | featured | name | desc | featN
    pp.add_argument("lang")
    pp.add_argument("value", nargs="*")

    mp = sub.add_parser("messages", help="manage contact messages")
    mp.add_argument("action", choices=["list", "export", "rm", "read"])
    mp.add_argument("id", nargs="?", default="")
    mp.add_argument("csv", nargs="?", default="")

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not args.cmd:
        build_parser().print_help()
        return 0
    if args.cmd == "status":
        cmd_status(args)
    elif args.cmd == "sync":
        cmd_sync(args)
    elif args.cmd == "build":
        cmd_build(args)
    elif args.cmd == "list":
        cmd_list(args)
    elif args.cmd == "add":
        cmd_add(args)
    elif args.cmd == "rm":
        cmd_rm(args)
    elif args.cmd == "set":
        cmd_set(args)
    elif args.cmd == "messages":
        cmd_messages(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())