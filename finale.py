import requests
from bs4 import BeautifulSoup
import feedparser
import random
import os
import re
from datetime import datetime, timedelta
import calendar
from concurrent.futures import ThreadPoolExecutor, as_completed

# Date Globali
DATA_OGGI = datetime.now()
STR_OGGI = DATA_OGGI.strftime("%d/%m/%Y")
HTML_OUTPUT = "index.html"

# Sessione condivisa: riusa le connessioni TCP invece di aprirne una nuova ad ogni richiesta
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

# ==========================================
# CLASSE NOTIZIA (Struttura Anti-Crash)
# ==========================================
class OggettoNotizia:
    def __init__(self, title, link):
        self.title = str(title)
        self.link = str(link)

# ==========================================
# 0. CANE DA TARTUFO
# ==========================================
def esplora_json(dizionario, chiavi_target):
    try:
        for chiave, valore in dizionario.items():
            if chiave.lower() in chiavi_target and isinstance(valore, str):
                return valore
        for chiave, valore in dizionario.items():
            if isinstance(valore, dict):
                risultato = esplora_json(valore, chiavi_target)
                if risultato: return risultato
    except:
        pass
    return None

# ==========================================
# 1. IL CAVALLO DEL GIORNO
# ==========================================
def recupera_cavallo_del_giorno():
    campione = {"nome": "ATTESA ARCHIVIO", "storia": "Carica il file memoir.txt su GitHub."}
    try:
        file_trovato = next((f for f in os.listdir('.') if f.lower() == 'memoir.txt'), None)
        if file_trovato:
            with open(file_trovato, "r", encoding="utf-8") as f:
                linee = [line.strip() for line in f if "|" in line]
            if linee:
                scelta = random.choice(linee)
                nome_c, storia_c = scelta.split("|", 1)
                campione = {"nome": nome_c.strip(), "storia": storia_c.strip()}
    except Exception:
        pass
    return campione

# ==========================================
# 2. ROAD TO GLORY (CALENDARIO PERPETUO BLINDATO)
# ==========================================
def calcola_data_corsa(anno, mese, giorno_settimana, n_occorrenza):
    try:
        calendario_mese = calendar.monthcalendar(anno, mese)
        giorni_validi = [settimana[giorno_settimana] for settimana in calendario_mese if settimana[giorno_settimana] != 0]
        # Previeni errori di indice
        if not giorni_validi: return DATA_OGGI
        giorno_esatto = giorni_validi[-1] if n_occorrenza == -1 else giorni_validi[n_occorrenza - 1]
        return datetime(anno, mese, giorno_esatto, 12, 0)
    except Exception:
        return DATA_OGGI # Paracadute in caso di errore matematico

def genera_calendario_g1():
    html = "<div class='rtg-container'>"
    try:
        anno_corrente = DATA_OGGI.year

        # 0=Lun, 1=Mar, 2=Mer, 3=Gio, 4=Ven, 5=Sab, 6=Dom
        regole_corse = [
            # REGNO UNITO E IRLANDA
            {"nome": "King George VI (Ascot - UK)", "mese": 7, "giorno": 5, "occ": 4},
            {"nome": "Epsom Derby (Epsom - UK)", "mese": 6, "giorno": 5, "occ": 1},
            {"nome": "Juddmonte Int. (York - UK)", "mese": 8, "giorno": 2, "occ": 3},

            # FRANCIA
            {"nome": "Prix de l'Arc de Triomphe (FRA)", "mese": 10, "giorno": 6, "occ": 1},
            {"nome": "Prix du Jockey Club (FRA)", "mese": 6, "giorno": 6, "occ": 1},
            {"nome": "Prix Jacques le Marois (FRA)", "mese": 8, "giorno": 6, "occ": 2},

            # USA
            {"nome": "Kentucky Derby (USA)", "mese": 5, "giorno": 5, "occ": 1},
            {"nome": "Breeders' Cup Classic (USA)", "mese": 11, "giorno": 5, "occ": 1},
            {"nome": "Pegasus World Cup (USA)", "mese": 1, "giorno": 5, "occ": -1},

            # ASIA (HONG KONG E GIAPPONE)
            {"nome": "Hong Kong Cup (Sha Tin - HK)", "mese": 12, "giorno": 6, "occ": 2},
            {"nome": "Hong Kong Derby (Sha Tin - HK)", "mese": 3, "giorno": 6, "occ": 3},
            {"nome": "Japan Cup (Tokyo - JPN)", "mese": 11, "giorno": 6, "occ": -1},
            {"nome": "Arima Kinen (Nakayama - JPN)", "mese": 12, "giorno": 6, "occ": -1},

            # MEDIO ORIENTE E AUSTRALIA
            {"nome": "Dubai World Cup (Meydan - UAE)", "mese": 3, "giorno": 5, "occ": -1},
            {"nome": "Saudi Cup (Riyadh - KSA)", "mese": 2, "giorno": 5, "occ": -1},
            {"nome": "Melbourne Cup (Flemington - AUS)", "mese": 11, "giorno": 1, "occ": 1},
            {"nome": "Cox Plate (Moonee Valley - AUS)", "mese": 10, "giorno": 5, "occ": -1},

            # ITALIA
            {"nome": "Derby Italiano (Capannelle - ITA)", "mese": 5, "giorno": 6, "occ": 3},
            {"nome": "Premio Jockey Club (San Siro - ITA)", "mese": 10, "giorno": 6, "occ": 3},
        ]

        prossime = []
        for corsa in regole_corse:
            data_corsa = calcola_data_corsa(anno_corrente, corsa["mese"], corsa["giorno"], corsa["occ"])
            giorni_mancanti = (data_corsa.date() - DATA_OGGI.date()).days

            if giorni_mancanti < -2:
                data_corsa = calcola_data_corsa(anno_corrente + 1, corsa["mese"], corsa["giorno"], corsa["occ"])
                giorni_mancanti = (data_corsa.date() - DATA_OGGI.date()).days

            prossime.append((corsa["nome"], data_corsa.strftime("%d/%m/%Y"), giorni_mancanti))

        prossime.sort(key=lambda x: x[2])

        for c in prossime[:6]:
            lbl = f"TRA {c[2]} GIORNI" if c[2] > 0 else "OGGI/DOMANI!"
            if c[2] < 0: lbl = "APPENA CORSA"
            html += f"""
            <div class='rtg-box'>
                <span class='rtg-badge'>{lbl}</span>
                <div class='rtg-title'>{c[0]}</div>
                <div class='rtg-date'>{c[1]}</div>
            </div>
            """
    except Exception as e:
        html += f"<p>Errore Calcolo Calendario: {e}</p>"

    html += "</div>"
    return html

# ==========================================
# 3. RASSEGNA STAMPA (SISTEMA IBRIDO CON SCUDO, SCARICAMENTO PARALLELO)
# ==========================================
def contiene_asiatico(testo):
    try:
        return bool(re.search(r'[\u4e00-\u9FFF\u3040-\u309F\u30A0-\u30FF]', str(testo)))
    except:
        return False

def _fetch_fonte(f):
    """Scarica e normalizza le notizie di una singola fonte (eseguita in thread parallelo)."""
    entries_finali = []
    try:
        res = SESSION.get(f['rss'], timeout=5)
        feed = feedparser.parse(res.content)
        if getattr(feed, 'entries', None):
            entries_finali = [OggettoNotizia(e.title, e.link) for e in feed.entries if hasattr(e, 'title') and hasattr(e, 'link')]
    except Exception:
        pass

    # Fallback via API rss2json solo per i feed diretti (i feed "google" passano già da Google News)
    if not entries_finali and f["tipo"] == "diretto":
        try:
            res_json = SESSION.get(f"https://api.rss2json.com/v1/api.json?rss_url={f['rss']}", timeout=5).json()
            if isinstance(res_json, dict) and res_json.get('status') == 'ok':
                entries_finali = [OggettoNotizia(item.get('title', ''), item.get('link', '#'))
                                   for item in res_json.get('items', []) if isinstance(item, dict)]
        except Exception:
            pass

    # Stampa con scudo anti-ideogrammi
    html_items = []
    for entry in entries_finali:
        if len(html_items) >= 3:
            break
        titolo_pulito = getattr(entry, 'title', 'Senza Titolo')
        if f["tipo"] == "google" and " - " in titolo_pulito:
            titolo_pulito = titolo_pulito.rsplit(" - ", 1)[0]
        if contiene_asiatico(titolo_pulito):
            continue
        link_sicuro = getattr(entry, 'link', '#')
        html_items.append(f"<li><a href='{link_sicuro}' target='_blank' rel='noopener'>{titolo_pulito}</a></li>")

    if not html_items:
        html_items = ["<li><i>Nessun aggiornamento recente.</i></li>"]

    return f"<div class='news-block'><div class='news-source'>{f['nome']}</div><ul>{''.join(html_items)}</ul></div>"


def recupera_notizie():
    fonti = [
        {"nome": "ITALIAN POST RACING", "rss": "https://www.italianpostracing.it/feed/", "tipo": "diretto"},
        {"nome": "THOROUGHBRED DAILY NEWS", "rss": "https://www.thoroughbreddailynews.com/feed/", "tipo": "diretto"},
        {"nome": "ASIAN RACING REPORT", "rss": "https://asianracingreport.com/feed/", "tipo": "diretto"},
        {"nome": "BLOODHORSE (USA)", "rss": "https://news.google.com/rss/search?q=site:bloodhorse.com+when:7d&hl=en-US&gl=US&ceid=US:en", "tipo": "google"},
        {"nome": "PAULICK REPORT", "rss": "https://news.google.com/rss/search?q=site:paulickreport.com+when:7d&hl=en-US&gl=US&ceid=US:en", "tipo": "google"}
    ]

    # Scarica tutte le fonti in parallelo invece che una alla volta
    risultati = {}
    with ThreadPoolExecutor(max_workers=len(fonti)) as executor:
        future_to_i = {executor.submit(_fetch_fonte, f): i for i, f in enumerate(fonti)}
        for future in as_completed(future_to_i):
            i = future_to_i[future]
            try:
                risultati[i] = future.result()
            except Exception:
                risultati[i] = f"<div class='news-block'><div class='news-source'>{fonti[i]['nome']}</div><ul><li><i>Feed temporaneamente non disponibile.</i></li></ul></div>"

    return "<div class='news-grid'>" + "".join(risultati[i] for i in range(len(fonti))) + "</div>"

# ==========================================
# 4. PALINSESTO PALINSESTI (CON AGGIUNTE MEDIORIENTALI E ASIATICHE, PARTENTI IN PARALLELO)
# ==========================================
def identifica_nazione(meeting, races):
    try:
        c_code = str(meeting.get('country', meeting.get('country_code', ''))).upper()

        # Le grandi piazze Europee e Americane
        if c_code in ['FRA', 'FR']: return "FRANCIA"
        if c_code in ['GB', 'UK', 'ENG', 'IRE', 'IRL']: return "REGNO UNITO E IRLANDA"
        if c_code in ['US', 'USA']: return "STATI UNITI"
        if c_code in ['GER', 'DE']: return "GERMANIA"
        if c_code in ['ITY', 'ITA', 'IT']: return "ITALIA"

        # Le grandi piazze Asiatiche e Mediorientali
        if c_code in ['JP', 'JPN']: return "GIAPPONE"
        if c_code in ['HK', 'HKG']: return "HONG KONG"
        if c_code in ['UAE', 'AE']: return "EMIRATI ARABI UNITI (DUBAI)"
        if c_code in ['KSA', 'SA']: return "ARABIA SAUDITA"
        if c_code in ['BHR', 'BH']: return "BAHREIN"
        if c_code in ['QAT', 'QA']: return "QATAR"
        if c_code in ['MAC', 'MO']: return "MACAO"

        # Emisfero Sud
        if c_code in ['RSA', 'ZA', 'SAF']: return "SUDAFRICA"
        if c_code in ['AUS', 'NZ']: return "AUSTRALIA E NUOVA ZELANDA"

        testo_corse = " ".join([str(r.get('race_name', r.get('name', ''))) for r in races]).upper()
        nome_ippodromo = str(meeting.get('name', meeting.get('course_name', ''))).upper()

        # Rilevamento d'emergenza
        parole_francesi = ['PRIX', 'ATTELE', 'HURDLE', 'HAUTE', 'CHOISY', 'MEDOC', 'CHAROLAIS', 'CHALLENGE', 'AUTEUIL']
        if any(p in testo_corse for p in parole_francesi) or any(p in nome_ippodromo for p in ['VICHY', 'ENGHIEN', 'DEAUVILLE', 'AUTEUIL', 'CAGNES']):
            return "FRANCIA"

        if any(p in testo_corse for p in ['CLAIMING', 'ALLOWANCE', 'MAIDEN SPECIAL']):
            return "STATI UNITI"

        parole_uk = ['NURSERY', 'HANDICAP', 'STAKES', 'NOVICE', 'MAIDEN STAKES']
        if any(p in testo_corse for p in parole_uk):
            return "REGNO UNITO E IRLANDA"

        if not c_code or c_code == 'NONE':
            return "REGNO UNITO E IRLANDA"

        return c_code if c_code and c_code != 'NONE' else "INTERNAZIONALE"
    except Exception:
        return "INTERNAZIONALE"

def _fetch_dettaglio_corsa(race_id, headers):
    """Scarica i partenti di una singola corsa (eseguita in thread parallelo)."""
    try:
        r_res = SESSION.get(f"https://www.sportinglife.com/api/horse-racing/race/{race_id}", headers=headers, timeout=5)
        if r_res.status_code == 200:
            return r_res.json().get('rides', [])
    except Exception:
        pass
    return None

def recupera_palinsesto_globale():
    date_query = [
        {"lbl": "OGGI", "val": DATA_OGGI.strftime('%Y-%m-%d')},
        {"lbl": "DOMANI", "val": (DATA_OGGI + timedelta(days=1)).strftime('%Y-%m-%d')}
    ]

    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    html_out = ""

    for dq in date_query:
        url = f"https://www.sportinglife.com/api/horse-racing/racing/racecards/{dq['val']}"
        try:
            res = SESSION.get(url, headers=headers, timeout=10)
            if res.status_code != 200: continue

            try:
                meetings = res.json() if isinstance(res.json(), list) else res.json().get('meetings', [])
            except Exception:
                continue

            if not meetings: continue

            # Fase 1: raccogli tutti i race_id del giorno
            race_ids = []
            for m in meetings:
                if not isinstance(m, dict): continue
                for r in m.get('races', []):
                    if not isinstance(r, dict): continue
                    ref = r.get('race_summary_reference')
                    if isinstance(ref, dict) and ref.get('id'):
                        race_ids.append(ref['id'])

            # Fase 2: scarica tutti i dettagli partenti in parallelo (max 10 richieste contemporanee)
            dettagli_per_id = {}
            if race_ids:
                with ThreadPoolExecutor(max_workers=min(10, len(race_ids))) as executor:
                    future_to_id = {executor.submit(_fetch_dettaglio_corsa, rid, headers): rid for rid in race_ids}
                    for future in as_completed(future_to_id):
                        dettagli_per_id[future_to_id[future]] = future.result()

            raggruppamento = {}

            for m in meetings:
                if not isinstance(m, dict): continue
                races = m.get('races', [])
                if not races or not isinstance(races, list): continue

                nome_ipp = esplora_json(m, ['name', 'course_name', 'meeting_name', 'venue']) or "IPPODROMO"
                if nome_ipp == "IPPODROMO" and isinstance(races[0], dict):
                    nome_ipp = esplora_json(races[0], ['course_name', 'track', 'name']) or nome_ipp

                nome_nazione = identifica_nazione(m, races)

                ippo_html = f"""
                <details class='ippo-accordion'>
                    <summary class='ippo-summary'><span>{str(nome_ipp).upper()}</span></summary>
                    <div class='ippo-content'>
                """

                for r in races:
                    if not isinstance(r, dict): continue
                    ora = r.get('time', 'N/D')
                    titolo_c = r.get('race_name', r.get('name', 'Corsa'))
                    dist = r.get('distance', '')

                    race_id = None
                    if isinstance(r.get('race_summary_reference'), dict):
                        race_id = r.get('race_summary_reference').get('id')

                    dist_html = f" | Dist: {dist}" if dist else ""
                    ippo_html += f"<div class='race-title'><b>{ora}</b> — {titolo_c} <small>{dist_html}</small></div>"

                    rides = dettagli_per_id.get(race_id) if race_id else None
                    if race_id and rides is None:
                        ippo_html += "<p class='err-txt'>Dettagli partenti non disponibili.</p>"
                    elif rides:
                        ippo_html += "<table class='race-table'><thead><tr><th>N°</th><th>Cavallo</th><th>Fantino</th></tr></thead><tbody>"
                        for p in rides:
                            if not isinstance(p, dict): continue
                            num = str(p.get('cloth_number', p.get('saddle_cloth_number', '-'))).zfill(2)
                            cav = p.get('horse', {}).get('name', 'N/D').upper() if isinstance(p.get('horse'), dict) else 'N/D'
                            fan = p.get('jockey', {}).get('name', 'N/D') if isinstance(p.get('jockey'), dict) else 'N/D'
                            ippo_html += f"<tr><td class='num-col'>{num}</td><td class='horse-col'>{cav}</td><td class='jockey-col'>{fan}</td></tr>"
                        ippo_html += "</tbody></table>"

                ippo_html += "</div></details>"

                raggruppamento.setdefault(nome_nazione, []).append({"nome": str(nome_ipp).upper(), "html": ippo_html})

            html_out += f"<h3 class='day-header'>PALINSESTO {dq['lbl']} ({dq['val']})</h3>"
            for nazione in sorted(raggruppamento.keys()):
                html_out += f"<div class='nation-group-title'>{nazione}</div>"
                for ippo in sorted(raggruppamento[nazione], key=lambda x: x['nome']):
                    html_out += ippo['html']

        except Exception:
            html_out += f"<p class='err-txt'>Errore caricamento palinsesto {dq['lbl']}: Impossibile connettersi ai server.</p>"

    return html_out

# ==========================================
# 5. GENERATORE HTML STILE GIORNALE MODERNO
# ==========================================
def genera_sito():
    try:
        cavallo = recupera_cavallo_del_giorno()
        calendario = genera_calendario_g1()
        notizie = recupera_notizie()
        palinsesto = recupera_palinsesto_globale()

        html_final = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>L'Eco del Galoppo</title>
    <style>
        :root {{
            --bg-color: #f4f3f0;
            --card-bg: #ffffff;
            --text-main: #1a1a1a;
            --text-muted: #6b6b6b;
            --border-color: #1a1a1a;
            --border-light: #e2e0da;
            --accent: #a6321f;
        }}

        * {{ box-sizing: border-box; }}

        body {{
            font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 24px 16px;
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
        }}

        .paper-container {{
            max-width: 900px;
            margin: 0 auto;
            background: var(--card-bg);
            border-radius: 14px;
            padding: 32px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.06);
        }}

        header {{
            text-align: center;
            padding-bottom: 18px;
            margin-bottom: 8px;
        }}

        header h1 {{
            font-family: 'Georgia', serif;
            font-size: 38px;
            margin: 0;
            font-weight: 900;
            letter-spacing: -0.5px;
        }}

        .sub-header {{
            font-style: italic;
            font-size: 14px;
            color: var(--text-muted);
            margin-top: 4px;
        }}

        .issue-date {{
            display: inline-block;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 12px;
            padding: 4px 12px;
            background: var(--text-main);
            color: #fff;
            border-radius: 20px;
            font-weight: 600;
        }}

        /* Barra di navigazione rapida — per saltare subito alla sezione che ti serve */
        .quick-nav {{
            position: sticky;
            top: 0;
            z-index: 10;
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            justify-content: center;
            background: var(--card-bg);
            padding: 12px 0 20px;
            margin-bottom: 20px;
            border-bottom: 1px solid var(--border-light);
        }}
        .quick-nav a {{
            font-size: 13px;
            font-weight: 600;
            text-decoration: none;
            color: var(--text-main);
            background: var(--bg-color);
            padding: 6px 14px;
            border-radius: 20px;
            transition: background 0.15s;
        }}
        .quick-nav a:hover {{ background: var(--accent); color: #fff; }}

        .section-title {{
            font-family: 'Georgia', serif;
            font-size: 20px;
            font-weight: bold;
            border-left: 4px solid var(--accent);
            padding-left: 10px;
            margin-top: 36px;
            margin-bottom: 16px;
            scroll-margin-top: 90px; /* evita che la nav sticky copra il titolo dopo un salto */
        }}

        /* Cavallo del giorno */
        .memoir-box {{
            border-radius: 10px;
            background: #faf9f6;
            border: 1px solid var(--border-light);
            padding: 18px 22px;
            margin-bottom: 10px;
        }}
        .memoir-title {{
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--accent);
            margin-bottom: 6px;
        }}
        .memoir-name {{ font-size: 20px; font-weight: bold; margin-bottom: 6px; }}
        .memoir-text {{ font-size: 14px; color: #333; }}

        /* Road to Glory */
        .rtg-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 12px;
        }}
        .rtg-box {{
            border: 1px solid var(--border-light);
            border-radius: 10px;
            padding: 14px;
            background: #fff;
            transition: transform 0.15s;
        }}
        .rtg-box:hover {{ transform: translateY(-2px); }}
        .rtg-badge {{
            font-size: 10px;
            font-weight: 700;
            background: var(--accent);
            color: #fff;
            padding: 3px 8px;
            border-radius: 12px;
            text-transform: uppercase;
        }}
        .rtg-title {{ font-size: 14px; font-weight: 700; margin-top: 8px; }}
        .rtg-date {{ font-size: 12px; color: var(--text-muted); }}

        /* News Grid */
        .news-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 20px;
        }}
        .news-block {{
            border-top: 2px solid var(--text-main);
            padding-top: 10px;
        }}
        .news-source {{
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--accent);
            margin-bottom: 8px;
        }}
        .news-block ul {{ list-style: none; padding: 0; margin: 0; }}
        .news-block li {{
            font-size: 13.5px;
            margin-bottom: 10px;
            padding-left: 14px;
            position: relative;
        }}
        .news-block li::before {{
            content: "→";
            position: absolute;
            left: 0;
            color: var(--accent);
        }}
        .news-block a {{ color: var(--text-main); text-decoration: none; }}
        .news-block a:hover {{ color: var(--accent); text-decoration: underline; }}

        /* Accordion Palinsesto */
        .day-header {{
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 1px;
            background: var(--text-main);
            color: #fff;
            padding: 8px 14px;
            border-radius: 8px;
            margin-top: 28px;
        }}
        .nation-group-title {{
            font-size: 14px;
            font-weight: 700;
            text-transform: uppercase;
            background: #f0efe9;
            padding: 8px 14px;
            margin-top: 16px;
            margin-bottom: 8px;
            border-radius: 8px;
            border-left: 4px solid var(--accent);
        }}
        .ippo-accordion {{
            border: 1px solid var(--border-light);
            border-radius: 10px;
            margin-bottom: 8px;
            background: #fff;
            overflow: hidden;
        }}
        .ippo-summary {{
            padding: 12px 16px;
            font-size: 14px;
            font-weight: 700;
            cursor: pointer;
            background: #fafaf8;
            list-style: none;
        }}
        .ippo-summary::-webkit-details-marker {{ display: none; }}
        .ippo-summary::before {{
            content: "▸ ";
            color: var(--accent);
        }}
        details[open] .ippo-summary::before {{ content: "▾ "; }}
        .ippo-content {{ padding: 14px 16px; border-top: 1px solid var(--border-light); }}
        .race-title {{
            font-size: 13.5px;
            margin-top: 10px;
            margin-bottom: 5px;
            color: #111;
        }}
        .race-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            margin-bottom: 14px;
        }}
        .race-table th {{
            text-align: left;
            padding: 6px 4px;
            background: #f4f3f0;
            color: #000;
            font-size: 11px;
            text-transform: uppercase;
        }}
        .race-table td {{ border-bottom: 1px solid #f0efe9; padding: 6px 4px; color: #222; }}
        .num-col {{ width: 35px; font-weight: bold; color: var(--accent); }}
        .horse-col {{ font-weight: 600; }}
        .err-txt {{ font-size: 12px; font-style: italic; color: #999; }}

        @media (max-width: 600px) {{
            body {{ padding: 12px 8px; }}
            .paper-container {{ padding: 18px; border-radius: 10px; }}
            header h1 {{ font-size: 28px; }}
            .quick-nav {{ gap: 6px; }}
            .quick-nav a {{ font-size: 12px; padding: 5px 10px; }}
        }}
    </style>
</head>
<body>
    <div class="paper-container">
        <header>
            <h1>L'Eco del Galoppo</h1>
            <div class="sub-header">La nostra dose quotidiana di zoccoli e gloria.</div>
            <div class="issue-date">Edizione del {STR_OGGI}</div>
        </header>

        <nav class="quick-nav">
            <a href="#cavallo">🐴 Cavallo del giorno</a>
            <a href="#rtg">🏆 Road to Glory</a>
            <a href="#news">📰 Rassegna Stampa</a>
            <a href="#palinsesto">📋 Palinsesto</a>
        </nav>

        <div id="cavallo" class="memoir-box">
            <div class="memoir-title">Il Cavallo del Giorno</div>
            <div class="memoir-name">{cavallo['nome']}</div>
            <div class="memoir-text">{cavallo['storia']}</div>
        </div>

        <div id="rtg" class="section-title">Road to Glory — Prossimi Gran Premi</div>
        {calendario}

        <div id="news" class="section-title">Rassegna Stampa Internazionale</div>
        {notizie}

        <div id="palinsesto" class="section-title">Palinsesto Globale e Partenti</div>
        {palinsesto}
    </div>
</body>
</html>"""

        with open(HTML_OUTPUT, "w", encoding="utf-8") as f:
            f.write(html_final)
        print("Stampa de 'L'Eco del Galoppo' completata con successo.")
    except Exception as e:
        print(f"ERRORE CRITICO DI SISTEMA: {e}")

if __name__ == "__main__":
    genera_sito()
