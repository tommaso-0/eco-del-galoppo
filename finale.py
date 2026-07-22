import requests
from bs4 import BeautifulSoup
import feedparser
import random
import os
import re
from datetime import datetime, timedelta

DATA_OGGI = datetime.now()
STR_OGGI = DATA_OGGI.strftime("%d/%m/%Y")
HTML_OUTPUT = "index.html"

# ==========================================
# 0. CANE DA TARTUFO (Per i nomi ippodromi)
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
        print(f"Errore caricamento memoir: {e}")
    return campione

# ==========================================
# 2. ROAD TO GLORY
# ==========================================
def genera_calendario_g1():
    g1_database = [
        {"nome": "Sussex Stakes (UK)", "data": "29/07/2026"},
        {"nome": "Prix Jacques le Marois (FRA)", "data": "16/08/2026"},
        {"nome": "Juddmonte International (UK)", "data": "19/08/2026"},
        {"nome": "Irish Champion Stakes (IRE)", "data": "12/09/2026"},
        {"nome": "Sprinters Stakes (JPN)", "data": "04/10/2026"},
        {"nome": "Prix de l'Arc de Triomphe (FRA)", "data": "04/10/2026"},
        {"nome": "Champion Stakes (UK)", "data": "17/10/2026"},
        {"nome": "Shuka Sho (JPN)", "data": "18/10/2026"},
        {"nome": "Premio Jockey Club (ITA)", "data": "18/10/2026"},
        {"nome": "Cox Plate (AUS)", "data": "24/10/2026"},
        {"nome": "Kikuka Sho - St. Leger (JPN)", "data": "25/10/2026"},
        {"nome": "Tenno Sho Autumn (JPN)", "data": "01/11/2026"},
        {"nome": "Melbourne Cup (AUS)", "data": "03/11/2026"},
        {"nome": "Breeders' Cup Classic (USA)", "data": "07/11/2026"},
        {"nome": "Premio Roma (ITA)", "data": "08/11/2026"},
        {"nome": "Japan Cup (JPN)", "data": "29/11/2026"},
        {"nome": "Hong Kong Cup (HK)", "data": "13/12/2026"},
        {"nome": "Arima Kinen (JPN)", "data": "27/12/2026"},
        {"nome": "Saudi Cup (KSA)", "data": "20/02/2027"},
        {"nome": "Dubai World Cup (UAE)", "data": "27/03/2027"},
        {"nome": "Kentucky Derby (USA)", "data": "01/05/2027"},
        {"nome": "Derby Italiano (ITA)", "data": "23/05/2027"},
        {"nome": "Epsom Derby (UK)", "data": "05/06/2027"},
        {"nome": "Prix du Jockey Club (FRA)", "data": "06/06/2027"}
    ]
    
    prossime = []
    for corsa in g1_database:
        d = datetime.strptime(corsa["data"], "%d/%m/%Y")
        if d >= DATA_OGGI - timedelta(days=1):
            giorni = (d - DATA_OGGI).days
            prossime.append((corsa["nome"], corsa["data"], giorni))
            
    prossime.sort(key=lambda x: x[2])
    
    html = "<div class='rtg-container'>"
    for c in prossime[:6]:
        lbl = f"TRA {c[2]} GIORNI" if c[2] > 0 else "OGGI!"
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
# 3. RASSEGNA STAMPA (Infallibile a 3 Livelli)
# ==========================================
def contiene_asiatico(testo):
    return bool(re.search(r'[\u4e00-\u9FFF\u3040-\u309F\u30A0-\u30FF]', testo))

def recupera_notizie():
    fonti = [
        {"nome": "ITALIAN POST RACING", "url": "https://www.italianpostracing.it", "rss": "https://www.italianpostracing.it/feed/"},
        {"nome": "THOROUGHBRED DAILY NEWS", "url": "https://www.thoroughbreddailynews.com", "rss": "https://www.thoroughbreddailynews.com/feed/"},
        {"nome": "ASIAN RACING REPORT", "url": "https://asianracingreport.com", "rss": "https://asianracingreport.com/feed/"},
        {"nome": "BLOODHORSE (USA)", "url": "https://www.bloodhorse.com", "rss": "https://www.bloodhorse.com/rss/news"},
        {"nome": "PAULICK REPORT", "url": "https://paulickreport.com", "rss": "https://paulickreport.com/feed/"}
    ]
    
    html_news = "<div class='news-grid'>"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }

    for f in fonti:
        html_news += f"<div class='news-block'><div class='news-source'>{f['nome']}</div><ul>"
        
        try:
            entries = []
            
            # LIVELLO 1: Connessione RSS Diretta
            try:
                res = requests.get(f['rss'], headers=headers, timeout=5)
                feed = feedparser.parse(res.content)
                if res.status_code == 200 and len(feed.entries) > 0:
                    entries = feed.entries
            except: pass
                
            # LIVELLO 2: Proxy AllOrigins (Maschera l'IP di GitHub)
            if not entries:
                try:
                    proxy_url = f"https://api.allorigins.win/get?url={f['rss']}"
                    res_proxy = requests.get(proxy_url, timeout=5)
                    if res_proxy.status_code == 200:
                        content = res_proxy.json().get('contents', '')
                        feed = feedparser.parse(content)
                        if len(feed.entries) > 0:
                            entries = feed.entries
                except: pass
            
            # LIVELLO 3: Forza Bruta HTML (Raschia la Homepage)
            if not entries:
                try:
                    res_html = requests.get(f['url'], headers=headers, timeout=5)
                    soup = BeautifulSoup(res_html.text, 'html.parser')
                    fuffa = ["menu", "search", "cookie", "privacy", "accedi", "abbonati", "login", "subscribe", "newsletter", "read more", "leggi tutto", "terms", "policy", "redazione", "chi siamo", "contact", "about", "advertisement"]
                    
                    for a_tag in soup.find_all('a', href=True):
                        testo = a_tag.get_text(strip=True)
                        # Filtriamo i link veri: testo lungo, no caratteri strani, no parole fuffa
                        if len(testo) > 35 and not any(ord(c) > 12000 for c in testo):
                            if not any(parola in testo.lower() for parola in fuffa):
                                link = a_tag['href']
                                if not link.startswith('http'):
                                    link = f['url'] + link if link.startswith('/') else f"{f['url']}/{link}"
                                
                                # Evitiamo doppioni
                                if not any(e.title == testo for e in entries):
                                    class OggettoNotizia: pass
                                    e = OggettoNotizia()
                                    e.title = testo
                                    e.link = link
                                    entries.append(e)
                except: pass

            # STAMPA RISULTATI
            notizie_valide = 0
            for entry in entries:
                if notizie_valide >= 3: break
                if contiene_asiatico(entry.title): continue
                    
                html_news += f"<li><a href='{entry.link}' target='_blank'>{entry.title}</a></li>"
                notizie_valide += 1
                
            if notizie_valide == 0:
                html_news += "<li><i>Nessun aggiornamento recente.</i></li>"
                
        except Exception:
            html_news += "<li><i>Feed temporaneamente non disponibile.</i></li>"
            
        html_news += "</ul></div>"
        
    html_news += "</div>"
    return html_news

# ==========================================
# 4. PALINSESTO PALINSESTI (ORDINATO PER NAZIONE)
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
</html>"""

    with open(HTML_OUTPUT, "w", encoding="utf-8") as f:
        f.write(html_final)
    print("Stampa de 'L'Eco del Galoppo' completata con successo.")

if __name__ == "__main__":
    genera_sito()
