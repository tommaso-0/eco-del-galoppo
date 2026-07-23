import requests
from bs4 import BeautifulSoup
import feedparser
import random
import os
import re
from datetime import datetime, timedelta
import calendar

DATA_OGGI = datetime.now()
STR_OGGI = DATA_OGGI.strftime("%d/%m/%Y")
HTML_OUTPUT = "index.html"

# ==========================================
# 0. CANE DA TARTUFO
# ==========================================
def esplora_json(dizionario, chiavi_target):
    for chiave, valore in dizionario.items():
        if chiave.lower() in chiavi_target and isinstance(valore, str):
            return valore
    for chiave, valore in dizionario.items():
        if isinstance(valore, dict):
            risultato = esplora_json(valore, chiavi_target)
            if risultato: return risultato
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
    except Exception as e:
        pass
    return campione

# ==========================================
# 2. ROAD TO GLORY (MOTORE PERPETUO ESPANSO)
# ==========================================
def calcola_data_corsa(anno, mese, giorno_settimana, n_occorrenza):
    calendario_mese = calendar.monthcalendar(anno, mese)
    giorni_validi = [settimana[giorno_settimana] for settimana in calendario_mese if settimana[giorno_settimana] != 0]
    giorno_esatto = giorni_validi[-1] if n_occorrenza == -1 else giorni_validi[n_occorrenza - 1]
    return datetime(anno, mese, giorno_esatto, 12, 0)

def genera_calendario_g1():
    anno_corrente = DATA_OGGI.year
    
    # REGOLE STORICHE: 0=Lun, 1=Mar, 2=Mer, 3=Gio, 4=Ven, 5=Sab, 6=Dom
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
        
        # MEDIO ORIENTE
        {"nome": "Dubai World Cup (Meydan - UAE)", "mese": 3, "giorno": 5, "occ": -1},
        {"nome": "Saudi Cup (Riyadh - KSA)", "mese": 2, "giorno": 5, "occ": -1},
        
        # AUSTRALIA
        {"nome": "Melbourne Cup (Flemington - AUS)", "mese": 11, "giorno": 1, "occ": 1}, # 1° Martedì
        {"nome": "Cox Plate (Moonee Valley - AUS)", "mese": 10, "giorno": 5, "occ": -1},
        
        # ITALIA
        {"nome": "Derby Italiano (Capannelle - ITA)", "mese": 5, "giorno": 6, "occ": 3},
        {"nome": "Premio Jockey Club (San Siro - ITA)", "mese": 10, "giorno": 6, "occ": 3},
    ]
    
    prossime = []
    for corsa in regole_corse:
        data_corsa = calcola_data_corsa(anno_corrente, corsa["mese"], corsa["giorno"], corsa["occ"])
        giorni_mancanti = (data_corsa.date() - DATA_OGGI.date()).days
        
        # Passata all'anno successivo in automatico
        if giorni_mancanti < -2:
            data_corsa = calcola_data_corsa(anno_corrente + 1, corsa["mese"], corsa["giorno"], corsa["occ"])
            giorni_mancanti = (data_corsa.date() - DATA_OGGI.date()).days
            
        prossime.append((corsa["nome"], data_corsa.strftime("%d/%m/%Y"), giorni_mancanti))
        
    prossime.sort(key=lambda x: x[2])
    
    html = "<div class='rtg-container'>"
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
    html += "</div>"
    return html

# ==========================================
# 3. RASSEGNA STAMPA (SISTEMA IBRIDO)
# ==========================================
def contiene_asiatico(testo):
    return bool(re.search(r'[\u4e00-\u9FFF\u3040-\u309F\u30A0-\u30FF]', testo))

class NotiziaFake:
    pass

def recupera_notizie():
    fonti = [
        # SITI "AMICI": feed diretti originali
        {"nome": "ITALIAN POST RACING", "rss": "https://www.italianpostracing.it/feed/", "tipo": "diretto"},
        {"nome": "THOROUGHBRED DAILY NEWS", "rss": "https://www.thoroughbreddailynews.com/feed/", "tipo": "diretto"},
        {"nome": "ASIAN RACING REPORT", "rss": "https://asianracingreport.com/feed/", "tipo": "diretto"},
        # SITI BLINDATI: usiamo il travestimento di Google News
        {"nome": "BLOODHORSE (USA)", "rss": "https://news.google.com/rss/search?q=site:bloodhorse.com+when:7d&hl=en-US&gl=US&ceid=US:en", "tipo": "google"},
        {"nome": "PAULICK REPORT", "rss": "https://news.google.com/rss/search?q=site:paulickreport.com+when:7d&hl=en-US&gl=US&ceid=US:en", "tipo": "google"}
    ]
    
    html_news = "<div class='news-grid'>"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    for f in fonti:
        html_news += f"<div class='news-block'><div class='news-source'>{f['nome']}</div><ul>"
        entries = []
        
        try:
            if f["tipo"] == "diretto":
                # Tentativo 1: Direttamente al sito
                try:
                    res = requests.get(f['rss'], headers=headers, timeout=5)
                    feed = feedparser.parse(res.content)
                    if feed.entries: entries = feed.entries
                except: pass
                
                # Tentativo 2 (Paracadute): API di RSS2JSON per eludere i blocchi
                if not entries:
                    try:
                        res_json = requests.get(f"https://api.rss2json.com/v1/api.json?rss_url={f['rss']}", timeout=5).json()
                        if res_json.get('status') == 'ok':
                            for item in res_json.get('items', []):
                                e = NotiziaFake()
                                e.title = item.get('title', '')
                                e.link = item.get('link', '')
                                entries.append(e)
                    except: pass
            else:
                # Usa il Ponte Google
                res = requests.get(f['rss'], headers=headers, timeout=5)
                feed = feedparser.parse(res.content)
                if feed.entries: entries = feed.entries
                
            notizie_valide = 0
            for entry in entries:
                if notizie_valide >= 3: break
                
                titolo_pulito = entry.title
                if f["tipo"] == "google" and " - " in titolo_pulito:
                    titolo_pulito = titolo_pulito.rsplit(" - ", 1)[0]
                    
                if contiene_asiatico(titolo_pulito): continue
                    
                html_news += f"<li><a href='{entry.link}' target='_blank'>{titolo_pulito}</a></li>"
                notizie_valide += 1
                
            if notizie_valide == 0:
                html_news += "<li><i>Nessun aggiornamento recente.</i></li>"
                
        except Exception:
            html_news += "<li><i>Feed temporaneamente non disponibile.</i></li>"
            
        html_news += "</ul></div>"
        
    html_news += "</div>"
    return html_news

# ==========================================
# 4. PALINSESTO PALINSESTI
# ==========================================
def identifica_nazione(meeting, races):
    c_code = str(meeting.get('country', meeting.get('country_code', ''))).upper()
    
    if c_code in ['FRA', 'FR']: return "FRANCIA"
    if c_code in ['GB', 'UK', 'ENG', 'IRE', 'IRL']: return "REGNO UNITO E IRLANDA"
    if c_code in ['US', 'USA']: return "STATI UNITI"
    if c_code in ['JP', 'JPN']: return "GIAPPONE"
    if c_code in ['HK', 'HKG']: return "HONG KONG"
    if c_code in ['RSA', 'ZA', 'SAF']: return "SUDAFRICA"
    if c_code in ['AUS', 'NZ']: return "AUSTRALIA E NUOVA ZELANDA"
    
    testo_corse = " ".join([r.get('race_name', r.get('name', '')) for r in races]).upper()
    nome_ippodromo = str(meeting.get('name', meeting.get('course_name', ''))).upper()
    
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
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code != 200: continue
            
            meetings = res.json() if isinstance(res.json(), list) else res.json().get('meetings', [])
            if not meetings: continue
            
            raggruppamento = {}
            
            for m in meetings:
                races = m.get('races', [])
                if not races: continue
                
                nome_ipp = esplora_json(m, ['name', 'course_name', 'meeting_name', 'venue']) or "IPPODROMO"
                if nome_ipp == "IPPODROMO" and m.get('races'):
                    nome_ipp = esplora_json(m['races'][0], ['course_name', 'track', 'name']) or nome_ipp
                    
                nome_nazione = identifica_nazione(m, races)
                
                ippo_html = f"""
                <details class='ippo-accordion'>
                    <summary class='ippo-summary'>
                        <span>{nome_ipp.upper()}</span>
                    </summary>
                    <div class='ippo-content'>
                """
                
                for r in races:
                    ora = r.get('time', 'N/D')
                    titolo_c = r.get('race_name', r.get('name', 'Corsa'))
                    dist = r.get('distance', '')
                    race_id = r.get('race_summary_reference', {}).get('id')
                    
                    dist_html = f" | Dist: {dist}" if dist else ""
                    ippo_html += f"<div class='race-title'><b>{ora}</b> — {titolo_c} <small>{dist_html}</small></div>"
                    
                    if race_id:
                        try:
                            r_res = requests.get(f"https://www.sportinglife.com/api/horse-racing/race/{race_id}", headers=headers, timeout=5)
                            if r_res.status_code == 200:
                                rides = r_res.json().get('rides', [])
                                if rides:
                                    ippo_html += "<table class='race-table'><thead><tr><th>N°</th><th>Cavallo</th><th>Fantino</th></tr></thead><tbody>"
                                    for p in rides:
                                        num = str(p.get('cloth_number', p.get('saddle_cloth_number', '-'))).zfill(2)
                                        cav = p.get('horse', {}).get('name', 'N/D').upper()
                                        fan = p.get('jockey', {}).get('name', 'N/D')
                                        ippo_html += f"<tr><td class='num-col'>{num}</td><td class='horse-col'>{cav}</td><td class='jockey-col'>{fan}</td></tr>"
                                    ippo_html += "</tbody></table>"
                        except Exception:
                            ippo_html += "<p class='err-txt'>Dettagli partenti non disponibili.</p>"
                            
                ippo_html += "</div></details>"
                
                if nome_nazione not in raggruppamento:
                    raggruppamento[nome_nazione] = []
                raggruppamento[nome_nazione].append({"nome": nome_ipp.upper(), "html": ippo_html})

            html_out += f"<h3 class='day-header'>PALINSESTO {dq['lbl']} ({dq['val']})</h3>"
            
            for nazione in sorted(raggruppamento.keys()):
                html_out += f"<div class='nation-group-title'>{nazione}</div>"
                ippodromi_ordinati = sorted(raggruppamento[nazione], key=lambda x: x['nome'])
                for ippo in ippodromi_ordinati:
                    html_out += ippo['html']
                    
        except Exception as e:
            html_out += f"<p class='err-txt'>Errore caricamento palinsesto {dq['lbl']}: {e}</p>"
            
    return html_out

# ==========================================
# 5. GENERATORE HTML STILE GIORNALE MINIMAL
# ==========================================
def genera_sito():
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
            --bg-color: #e9e9e9;
            --card-bg: #ffffff;
            --text-main: #111111;
            --text-muted: #555555;
            --border-color: #222222;
            --border-light: #d1d1d1;
        }}
        
        body {{
            font-family: 'Georgia', 'Times New Roman', serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 20px;
            line-height: 1.5;
        }}
        
        .paper-container {{
            max-width: 960px;
            margin: 0 auto;
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            padding: 30px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        }}
        
        header {{
            text-align: center;
            border-bottom: 3px double var(--border-color);
            padding-bottom: 15px;
            margin-bottom: 25px;
        }}
        
        header h1 {{
            font-size: 42px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin: 0;
            font-weight: 900;
        }}
        
        .sub-header {{
            font-style: italic;
            font-size: 14px;
            color: var(--text-muted);
            margin-top: 5px;
        }}
        
        .issue-date {{
            font-family: 'Courier New', monospace;
            font-size: 12px;
            text-transform: uppercase;
            border-top: 1px solid var(--border-color);
            margin-top: 10px;
            padding-top: 5px;
            font-weight: bold;
        }}
        
        .section-title {{
            font-family: 'Georgia', serif;
            font-size: 18px;
            text-transform: uppercase;
            font-weight: bold;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 3px;
            margin-top: 30px;
            margin-bottom: 15px;
            letter-spacing: 0.5px;
        }}
        
        /* Cavallo del giorno */
        .memoir-box {{
            border: 1px solid var(--border-color);
            background: #fafafa;
            padding: 15px 20px;
            margin-bottom: 25px;
        }}
        .memoir-title {{
            font-family: 'Courier New', monospace;
            font-size: 11px;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-muted);
            margin-bottom: 5px;
        }}
        .memoir-name {{
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .memoir-text {{
            font-size: 14px;
            color: #333;
        }}
        
        /* Road to Glory */
        .rtg-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 12px;
        }}
        .rtg-box {{
            border: 1px solid var(--border-light);
            padding: 12px;
            background: #fff;
        }}
        .rtg-badge {{
            font-family: 'Courier New', monospace;
            font-size: 10px;
            font-weight: bold;
            background: #222;
            color: #fff;
            padding: 2px 6px;
            text-transform: uppercase;
        }}
        .rtg-title {{
            font-size: 14px;
            font-weight: bold;
            margin-top: 6px;
        }}
        .rtg-date {{
            font-size: 12px;
            color: var(--text-muted);
        }}
        
        /* News Grid */
        .news-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
        }}
        .news-block {{
            border-top: 1px solid var(--border-color);
            padding-top: 10px;
        }}
        .news-source {{
            font-family: 'Courier New', monospace;
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
            margin-bottom: 8px;
        }}
        .news-block ul {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        .news-block li {{
            font-size: 13px;
            margin-bottom: 8px;
            position: relative;
            padding-left: 12px;
        }}
        .news-block li::before {{
            content: "—";
            position: absolute;
            left: 0;
            color: var(--text-muted);
        }}
        .news-block a {{
            color: var(--text-main);
            text-decoration: none;
        }}
        .news-block a:hover {{
            text-decoration: underline;
        }}
        
        /* Accordion Palinsesto */
        .day-header {{
            font-family: 'Courier New', monospace;
            font-size: 14px;
            background: #222;
            color: #fff;
            padding: 6px 10px;
            border: 1px solid #000;
            margin-top: 25px;
        }}
        .nation-group-title {{
            font-family: 'Courier New', monospace;
            font-size: 15px;
            font-weight: bold;
            text-transform: uppercase;
            background: #e6e6e6;
            padding: 6px 10px;
            margin-top: 15px;
            margin-bottom: 8px;
            border-left: 4px solid #000;
        }}
        .ippo-accordion {{
            border: 1px solid var(--border-light);
            margin-bottom: 8px;
            background: #fff;
        }}
        .ippo-summary {{
            padding: 10px 15px;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            background: #fafafa;
        }}
        .ippo-content {{
            padding: 15px;
            border-top: 1px solid var(--border-light);
        }}
        .race-title {{
            font-size: 14px;
            margin-top: 10px;
            margin-bottom: 5px;
            border-bottom: 1px dashed #ccc;
            padding-bottom: 3px;
            color: #111;
        }}
        .race-table {{
            width: 100%;
            border-collapse: collapse;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            margin-bottom: 15px;
        }}
        .race-table th {{
            text-align: left;
            border-bottom: 1px solid #000;
            padding: 4px;
            background: #f0f0f0;
            color: #000;
        }}
        .race-table td {{
            border-bottom: 1px solid #eee;
            padding: 4px;
            color: #222;
        }}
        .num-col {{ width: 35px; font-weight: bold; }}
        .horse-col {{ font-weight: bold; }}
        .err-txt {{ font-size: 12px; font-style: italic; color: #666; }}
    </style>
</head>
<body>
    <div class="paper-container">
        <header>
            <h1>L'Eco del Galoppo</h1>
            <div class="sub-header">La nostra dose quotidiana di zoccoli e gloria.</div>
            <div class="issue-date">Edizione del {STR_OGGI}</div>
        </header>
        
        <div class="memoir-box">
            <div class="memoir-title">Il Cavallo del Giorno</div>
            <div class="memoir-name">{cavallo['nome']}</div>
            <div class="memoir-text">{cavallo['storia']}</div>
        </div>
        
        <div class="section-title">Road to Glory — Prossimi Gran Premi</div>
        {calendario}
        
        <div class="section-title">Rassegna Stampa Internazionale</div>
        {notizie}
        
        <div class="section-title">Palinsesto Globale e Partenti</div>
        {palinsesto}
    </div>
</body>
</html>
