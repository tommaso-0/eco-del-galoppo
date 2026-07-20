import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import re
import random
import os
from datetime import datetime

print("📰 Accensione rotative de 'L'Eco del Galoppo'...")

DATA_OGGI = datetime.now()
STR_OGGI = DATA_OGGI.strftime("%d/%m/%Y")
HTML_OUTPUT = "eco_del_galoppo.html"

# ==========================================
# 1. IL CAVALLO DEL GIORNO (Dal memoir.txt)
# ==========================================
campione_oggi = {"nome": "ATTESA ARCHIVIO", "storia": "Carica il file memoir.txt su GitHub."}

try:
    file_trovato = next((f for f in os.listdir('.') if f.lower() == 'memoir.txt'), None)
    if file_trovato:
        with open(file_trovato, "r", encoding="utf-8") as f:
            linee = [line.strip() for line in f if "|" in line]
        if linee:
            scelta = random.choice(linee)
            nome_c, storia_c = scelta.split("|", 1)
            campione_oggi = {"nome": nome_c.strip(), "storia": storia_c.strip()}
except Exception as e:
    print(f"Errore caricamento memoir: {e}")

# ==========================================
# 2. CALENDARIO G1 DINAMICO (DATABASE TITANICO)
# ==========================================
def genera_calendario_g1():
    g1_database = [
        {"nome": "Sprinters Stakes (JPN)", "data": "04/10/2026"},
        {"nome": "Shuka Sho (JPN)", "data": "18/10/2026"},
        {"nome": "Kikuka Sho - St. Leger (JPN)", "data": "25/10/2026"},
        {"nome": "Tenno Sho Autumn (JPN)", "data": "01/11/2026"},
        {"nome": "Queen Elizabeth II Cup (JPN)", "data": "15/11/2026"},
        {"nome": "Mile Championship (JPN)", "data": "22/11/2026"},
        {"nome": "Japan Cup (JPN)", "data": "29/11/2026"},
        {"nome": "Champions Cup (JPN)", "data": "06/12/2026"},
        {"nome": "Hong Kong Cup (HK)", "data": "13/12/2026"},
        {"nome": "Hong Kong Vase (HK)", "data": "13/12/2026"},
        {"nome": "Arima Kinen (JPN)", "data": "27/12/2026"},
        {"nome": "Saudi Cup (KSA)", "data": "20/02/2027"},
        {"nome": "Dubai World Cup (UAE)", "data": "27/03/2027"},
        {"nome": "Dubai Sheema Classic (UAE)", "data": "27/03/2027"},
        {"nome": "Oka Sho - 1000 Guineas (JPN)", "data": "11/04/2027"},
        {"nome": "Satsuki Sho - 2000 Guineas (JPN)", "data": "18/04/2027"},
        {"nome": "Tenno Sho Spring (JPN)", "data": "02/05/2027"},
        {"nome": "Tokyo Yushun - Derby (JPN)", "data": "30/05/2027"},
        {"nome": "Takarazuka Kinen (JPN)", "data": "27/06/2027"},
        
        {"nome": "Sussex Stakes (UK)", "data": "29/07/2026"},
        {"nome": "Juddmonte International (UK)", "data": "19/08/2026"},
        {"nome": "Prix Jacques le Marois (FRA)", "data": "16/08/2026"},
        {"nome": "Irish Champion Stakes (IRE)", "data": "12/09/2026"},
        {"nome": "Prix de l'Arc de Triomphe (FRA)", "data": "04/10/2026"},
        {"nome": "Champion Stakes (UK)", "data": "17/10/2026"},
        {"nome": "Premio Jockey Club (ITA)", "data": "18/10/2026"},
        {"nome": "Premio Roma (ITA)", "data": "08/11/2026"},
        {"nome": "2000 Guineas Stakes (UK)", "data": "01/05/2027"},
        {"nome": "Derby Italiano (ITA)", "data": "23/05/2027"},
        {"nome": "Epsom Derby (UK)", "data": "05/06/2027"},
        {"nome": "Prix du Jockey Club (FRA)", "data": "06/06/2027"},
        {"nome": "Royal Ascot - Gold Cup (UK)", "data": "17/06/2027"},
        
        {"nome": "Cox Plate (AUS)", "data": "24/10/2026"},
        {"nome": "Melbourne Cup (AUS)", "data": "03/11/2026"},
        {"nome": "Breeders' Cup Turf (USA)", "data": "07/11/2026"},
        {"nome": "Breeders' Cup Classic (USA)", "data": "07/11/2026"},
        {"nome": "Pegasus World Cup (USA)", "data": "23/01/2027"},
        {"nome": "Kentucky Derby (USA)", "data": "01/05/2027"}
    ]
    
    prossime_corse = []
    for corsa in g1_database:
        data_corsa = datetime.strptime(corsa["data"], "%d/%m/%Y")
        if data_corsa >= DATA_OGGI:
            giorni_mancanti = (data_corsa - DATA_OGGI).days
            prossime_corse.append((corsa["nome"], corsa["data"], giorni_mancanti))
            
    prossime_corse.sort(key=lambda x: x[2])
    
    html_cal = "<div style='display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px;'>"
    for c in prossime_corse[:5]:
        etichetta = f"Tra {c[2]} giorni" if c[2] > 0 else "OGGI!"
        colore_badge = "#8b0000" if c[2] < 7 else "#333" 
        html_cal += f"""
        <div style='background: #fff; border: 1px solid #999; padding: 10px; border-radius: 4px; flex: 1; min-width: 180px;'>
            <div style='font-size: 11px; font-weight: bold; color: {colore_badge}; text-transform: uppercase;'>{etichetta}</div>
            <div style='font-family: Georgia, serif; font-weight: bold; font-size: 13px; margin: 5px 0;'>{c[0]}</div>
            <div style='font-size: 12px; color: #555;'>📅 {c[1]}</div>
        </div>
        """
    html_cal += "</div>"
    return html_cal

# ==========================================
# 3. RECUPERO NOTIZIE (Browser Invisibile + Filtro Cinese)
# ==========================================
def contiene_cinese(testo):
    return any('\u4e00' <= char <= '\u9fff' for char in testo)

def recupera_notizie_web(driver):
    html_news = ""
    fonti = [
        {"nome": "EQUOS (GALOPPO)", "url": "https://equos.it/category/galoppo/"},
        {"nome": "ITALIAN POST RACING", "url": "https://www.italianpostracing.it/"},
        {"nome": "RACING POST", "url": "https://www.racingpost.com/news/"},
        {"nome": "TDN EUROPE", "url": "https://www.thoroughbreddailynews.com/tdn-europe/"},
        {"nome": "ASIAN RACING REPORT", "url": "https://asianracingreport.com/"}
    ]

    for fonte in fonti:
        print(f"   [📻] Contatto redazione: {fonte['nome']}...")
        try:
            driver.get(fonte['url'])
            time.sleep(5) 
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            notizie_estratte = []

            if "EQUOS" in fonte['nome']:
                articoli = soup.find_all('article')
                for art in articoli:
                    titolo_tag = art.find(['h2', 'h3'])
                    if titolo_tag:
                        link_tag = titolo_tag.find('a')
                        if link_tag and link_tag.has_attr('href'):
                            testo = link_tag.get_text(strip=True)
                            if len(testo) > 15 and not contiene_cinese(testo):
                                url_notizia = urljoin(fonte['url'], link_tag['href'])
                                if not any(testo == n['titolo'] for n in notizie_estratte):
                                    notizie_estratte.append({'titolo': testo, 'url': url_notizia})
                    if len(notizie_estratte) == 3: break
            
            if not notizie_estratte:
                tutti_i_link = soup.find_all('a', href=True)
                for a_tag in tutti_i_link:
                    testo = a_tag.get_text(strip=True)
                    
                    if len(testo) > 25 and not contiene_cinese(testo):
                        testo_lower = testo.lower()
                        fuffa = ["menu", "search", "cookie", "privacy", "accedi", "abbonati", "login", "subscribe", "newsletter", "read more", "leggi tutto", "terms", "policy", "redazione", "chi siamo"]
                        
                        if not any(parola in testo_lower for parola in fuffa):
                            url_notizia = urljoin(fonte['url'], a_tag['href'])
                            if not any(testo == n['titolo'] for n in notizie_estratte):
                                notizie_estratte.append({'titolo': testo, 'url': url_notizia})
                                
                    if len(notizie_estratte) == 3: break

            html_news += f'<div class="news-item"><div class="fonte">{fonte["nome"]}</div>'
            if notizie_estratte:
                for news in notizie_estratte:
                    html_news += f'<h4><a href="{news["url"]}" target="_blank" style="color: #111; text-decoration: none;">{news["titolo"]}</a></h4>'
            else:
                html_news += '<h4>Nessuna notizia rilevante al momento.</h4>'
            html_news += '</div>'
            
        except Exception:
            html_news += f'<div class="news-item"><div class="fonte">{fonte["nome"]}</div><h4>Collegamento fallito.</h4></div>'

    return html_news

# ==========================================
# 4. RISULTATI DI IERI (Estrattore Anti Pop-up)
# ==========================================
def recupera_risultati_ieri(driver):
    html_risultati = ""
    print("   [📻] Intercettazione Risultati Ippica.biz...")
    try:
        driver.get("https://www.ippica.biz/00_menu.asp")
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        link_pagina_arrivi = None
        for a_tag in soup.find_all('a', href=True):
            testo = a_tag.get_text(strip=True).upper()
            if 'ARRIVI' in testo or 'RISULTATI' in testo:
                link_pagina_arrivi = urljoin("https://www.ippica.biz/0/14_tlx/", a_tag['href'].strip())
                break
                
        link_trovati = []
        
        if link_pagina_arrivi:
            driver.get(link_pagina_arrivi)
            time.sleep(4)
            soup_arrivi = BeautifulSoup(driver.page_source, 'html.parser')
            
            for a_tag in soup_arrivi.find_all('a', href=True):
                href = a_tag['href'].strip()
                testo = a_tag.get_text(strip=True)
                
                if 'javascript:zoom' in href:
                    match_url = re.search(r"javascript:zoom\(['\"]([^'\"]+)['\"]\)", href)
                    if match_url:
                        url_pulito = match_url.group(1).replace("%27", "")
                        nome_gara = testo if testo else "Vedi"
                        
                        if url_pulito not in [l['url'] for l in link_trovati]:
                            link_trovati.append({"nome": nome_gara, "url": url_pulito})
        
        if link_trovati:
            html_risultati += "<div style='display:flex; flex-wrap:wrap; gap:10px; margin-top:10px;'>"
            for l in link_trovati:
                etichetta = f"🏁 Corsa {l['nome']}" if l['nome'].isdigit() else f"🏁 {l['nome']}"
                html_risultati += f"<a href='{l['url']}' target='_blank' style='display:inline-block; background:#e0e0e0; color:#111; padding:8px 12px; border:1px solid #999; border-radius:4px; text-decoration:none; font-weight:bold; font-size:13px;'>{etichetta}</a>"
            html_risultati += "</div>"
        else:
            html_risultati += "<p style='font-size: 13px; font-style: italic;'>(In attesa dei dispacci ufficiali. Nessun risultato rilevato sul server).</p>"
            
    except Exception as e:
        html_risultati += f"<p style='color:red;'>Errore radar risultati: {e}</p>"
        
    return html_risultati

# ==========================================
# 5. AVVIO DEL MOTORE E IMPAGINATORE HTML
# ==========================================
options = uc.ChromeOptions()
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu') 
options.add_argument('--window-size=1920,1080') 
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

try:
    print("\n📡 Avvio del driver Chrome in incognito...")
    driver = uc.Chrome(options=options, use_subprocess=True, version_main=150)
    
    blocco_notizie = recupera_notizie_web(driver)
    blocco_calendario = genera_calendario_g1()
    blocco_risultati = recupera_risultati_ieri(driver)
    
    sito_html = f"""
    <!DOCTYPE html>
    <html lang="it">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>L'Eco del Galoppo</title>
        <style>
            body {{ font-family: 'Courier New', Courier, monospace; background-color: #f4f4f4; color: #111; margin: 0; padding: 15px; }}
            .header {{ text-align: center; border-bottom: 4px double #000; padding-bottom: 10px; margin-bottom: 20px; }}
            .header h1 {{ margin: 0; font-family: 'Georgia', serif; font-size: 32px; text-transform: uppercase; font-weight: bold; }}
            .header p.sottotitolo {{ margin: 5px 0 0 0; font-family: 'Georgia', serif; font-style: italic; font-size: 14px; }}
            
            .box-storico {{ border: 2px dashed #000; padding: 15px; margin-bottom: 20px; background-color: #fff; }}
            .box-titolo {{ font-weight: bold; text-align: center; border-bottom: 1px solid #000; padding-bottom: 5px; margin-bottom: 10px; text-transform: uppercase; }}
            
            .sezione-news {{ margin-bottom: 30px; border-top: 4px double #000; padding-top: 15px; }}
            .titolo-sezione {{ font-weight: bold; font-size: 20px; text-transform: uppercase; border-bottom: 2px solid #000; padding-bottom: 5px; margin-bottom: 15px; font-family: 'Georgia', serif; }}
            .news-item {{ margin-bottom: 15px; }}
            .news-item h4 {{ margin: 0 0 6px 0; font-size: 15px; line-height: 1.4; font-family: 'Georgia', serif; font-weight: normal; }}
            .news-item h4 a:hover {{ text-decoration: underline !important; }}
            .news-item .fonte {{ font-size: 11px; color: #333; text-transform: uppercase; font-weight: bold; border-bottom: 1px dashed #999; display: inline-block; margin-bottom: 4px; }}
            
            details.ippodromo {{ background-color: #fff; border: 1px solid #000; margin-bottom: 15px; }}
            summary.main-tendina {{ background-color: #222; color: #fff; padding: 12px; font-weight: bold; font-size: 15px; cursor: pointer; list-style: none; }}
            summary.main-tendina::-webkit-details-marker {{ display: none; }}
            summary.main-tendina::before {{ content: '[+] '; font-family: monospace; }}
            details[open] > summary.main-tendina::before {{ content: '[-] '; }}
            
            details.corsa {{ margin-bottom: 5px; border: 1px solid #ccc; background-color: #fafafa; }}
            summary.sub-tendina {{ background-color: #e0e0e0; color: #000; padding: 10px; font-weight: bold; font-size: 13px; cursor: pointer; list-style: none; border-bottom: 1px solid #aaa; text-transform: uppercase; display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }}
            summary.sub-tendina::-webkit-details-marker {{ display: none; }}
            summary.sub-tendina::before {{ content: '► '; font-size: 11px; }}
            details[open] > summary.sub-tendina::before {{ content: '▼ '; }}
            
            .badge-ora {{ background: #e0e0e0; color: #000; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; border: 1px solid #999; letter-spacing: 0.5px; }}
            .badge-distanza {{ background: #444; color: #fff; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; border: 1px solid #222; letter-spacing: 0.5px; }}
            
            table {{ width: 100%; border-collapse: collapse; font-size: 14px; text-align: left; background-color: #fff; }}
            th, td {{ padding: 10px 5px; border-bottom: 1px dashed #ccc; }}
            th {{ border-bottom: 2px solid #000; background-color: #eee; text-transform: uppercase; }}
            .num {{ font-weight: bold; width: 35px; text-align: center; }}
            .etichetta-estero {{ font-size: 11px; color: #fff; background: #555; padding: 2px 6px; margin-left: 10px; border-radius: 4px; vertical-align: middle; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>L'Eco del Galoppo</h1>
            <p class="sottotitolo">"La nostra dose quotidiana di zoccoli e gloria."</p>
            <p class="sottotitolo" style="font-size: 12px; margin-top: 5px; text-transform: uppercase; border-top: 1px solid #000; display: inline-block; padding-top: 5px;">Edizione del: {STR_OGGI}</p>
        </div>
        
        <div class="box-storico">
            <div class="box-titolo">*** Il Cavallo del Giorno ***</div>
            <b>{campione_oggi['nome']}</b><br><span style="font-size: 13px;">{campione_oggi['storia']}</span>
        </div>
        
        <div class="sezione-news" style="background: #e9e9e9; padding: 15px; border: 1px solid #000;">
            <div class="titolo-sezione" style="border-bottom: 1px dashed #000; padding-bottom: 10px; margin-top: 0;">Road to G1</div>
            {blocco_calendario}
        </div>

        <div class="sezione-news">
            <div class="titolo-sezione">Rassegna Stampa Internazionale</div>
            {blocco_notizie}
        </div>
        
        <div class="titolo-sezione">Archivio Risultati di Ieri</div>
        {blocco_risultati}
        
        <div class="titolo-sezione" style="margin-top: 40px;">Partenti di Oggi</div>
    """

    menu_da_visitare = [
        {"nome": "Italia", "url": "https://www.ippica.biz/00_menu.asp", "base": "https://www.ippica.biz/0/14_tlx/"},
        {"nome": "Estero", "url": "https://www.ippica.biz/1/14_fnz/14_IB_progr_estere.asp?fnz=1&scroll=no&P01=2016&g=1", "base": "https://www.ippica.biz/1/14_tlx/"}
    ]
    
    link_validi = []
    
    for menu in menu_da_visitare:
        driver.get(menu['url'])
        time.sleep(5) 
        soup_menu = BeautifulSoup(driver.page_source, 'html.parser')
        
        for a_tag in soup_menu.find_all('a', href=True):
            href = a_tag['href'].strip()
            testo = a_tag.get_text(strip=True).upper()
            
            if '.asp?' in href.lower() and 'TG=T' not in href.upper():
                if 'CORSA=0' in href.upper() or 'IPPO=' in href.upper() or testo == 'C':
                    
                    match_ippo = re.search(r'IPPO=([^&]+)', href.upper())
                    nome_tendina = match_ippo.group(1).replace("%20", " ").replace("+", " ").upper() if match_ippo else "GARA"
                    if menu['nome'] == "Estero":
                        nome_tendina += " <span class='etichetta-estero'>INT</span>"
                    
                    url_assoluto = None
                    match_http = re.search(r'(http[s]?://[^\s\)\'"]+)', href)
                    
                    if match_http:
                        url_assoluto = match_http.group(1).replace("%27", "")
                    else:
                        match_file = re.search(r'([a-zA-Z0-9_]+\.asp\?[^\s\)\'"]+)', href)
                        if match_file:
                            file_pulito = match_file.group(1).replace("%27", "").replace("&amp;", "&")
                            url_assoluto = menu['base'] + file_pulito
                    
                    if url_assoluto and not any(l['nome'] == nome_tendina for l in link_validi):
                        link_validi.append({'url': url_assoluto, 'nome': nome_tendina})
    
    if not link_validi:
        sito_html += "<p><em>Nessuna corsa al galoppo in programma per oggi.</em></p>"
    else:
        for item in link_validi:
            nome_stampato = item['nome']
            driver.get(item['url'])
            time.sleep(4) 
            
            sito_html += f"<details class='ippodromo'><summary class='main-tendina'>{nome_stampato}</summary>\n<div style='padding: 10px;'>\n"
            
            corse_ippodromo = []
            corsa_corrente = {"titolo": "CORSA 1", "orario": "", "distanza": "", "cavalli": []}
            num_corsa = 1
            last_num = 999
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            for riga in soup.find_all('tr'):
                celle = [c.get_text(strip=True) for c in riga.find_all(['td', 'th'])]
                testo_riga = " ".join(celle).upper()
                
                if not celle or "CAVALLO" in testo_riga:
                    continue
                
                match_ora = re.search(r'(?:ORE|ALLE)\s*(\d{1,2}[:\.]\d{2})', testo_riga)
                if match_ora and not corsa_corrente["orario"]:
                    corsa_corrente["orario"] = match_ora.group(1).replace(".", ":")
                
                testo_dist_pulito = testo_riga.replace(".", "").replace(",", "")
                match_dist = re.search(r'(?:METRI|MT|\bM\b)\s*(\d{3,4})|(\d{3,4})\s*(?:METRI|MT|\bM\b)', testo_dist_pulito)
                if match_dist and not corsa_corrente["distanza"]:
                    corsa_corrente["distanza"] = match_dist.group(1) if match_dist.group(1) else match_dist.group(2)

                is_horse = False
                num_raw = ""
                if len(celle) >= 5:
                    num_raw = celle[1].replace(".", "").replace("°", "").strip()
                    if num_raw.isdigit():
                        is_horse = True

                if is_horse:
                    num_int = int(num_raw)
                    if num_int <= last_num and last_num != 999:
                        corse_ippodromo.append(corsa_corrente)
                        num_corsa += 1
                        corsa_corrente = {"titolo": f"CORSA {num_corsa}", "orario": "", "distanza": "", "cavalli": []}
                        
                    last_num = num_int
                    numero_formattato = str(num_int).zfill(2)
                    cavallo = celle[2]
                    val4 = celle[4] if len(celle) > 4 else "?"
                    val5 = celle[5] if len(celle) > 5 else "?"
                    
                    if re.match(r'^\d+([.,]\d+)?$', val5):
                        peso = val5
                        fantino = val4
                    else:
                        peso = val4
                        fantino = val5
                        
                    corsa_corrente["cavalli"].append({"num": numero_formattato, "nome": cavallo, "peso": peso, "fantino": fantino})
                    
                elif len(celle) == 1 and any(k in testo_riga for k in ["CORSA", "PREMIO", "PRIX", "ORE"]):
                    if len(corsa_corrente["cavalli"]) > 0:
                        corse_ippodromo.append(corsa_corrente)
                        num_corsa += 1
                        corsa_corrente = {"titolo": celle[0], "orario": "", "distanza": "", "cavalli": []}
                        last_num = 999
                        m_ora = re.search(r'(?:ORE|ALLE)\s*(\d{1,2}[:\.]\d{2})', testo_riga)
                        if m_ora: corsa_corrente["orario"] = m_ora.group(1).replace(".", ":")
                        m_dist = re.search(r'(?:METRI|MT|\bM\b)\s*(\d{3,4})|(\d{3,4})\s*(?:METRI|MT|\bM\b)', testo_dist_pulito)
                        if m_dist: corsa_corrente["distanza"] = m_dist.group(1) if m_dist.group(1) else m_dist.group(2)
                    else:
                        corsa_corrente["titolo"] = celle[0]
            
            if corsa_corrente["cavalli"]:
                corse_ippodromo.append(corsa_corrente)
                
            for corsa in corse_ippodromo:
                titolo_pulito = re.sub(r'(?i)(?:-?\s*ORE\s*\d{1,2}[:\.]\d{2})', '', corsa['titolo'])
                titolo_pulito = re.sub(r'(?i)(?:-?\s*(?:METRI|MT\.?|M\.?)\s*\d{3,4})', '', titolo_pulito)
                titolo_pulito = re.sub(r'(?i)(?:\d{3,4}\s*(?:METRI|MT\.?|M\.?))', '', titolo_pulito)
                titolo_pulito = titolo_pulito.strip(' -')
                if not titolo_pulito: titolo_pulito = f"CORSA"

                badge_ora = f"<span class='badge-ora'>🕒 {corsa['orario']}</span>" if corsa['orario'] else ""
                badge_dist = f"<span class='badge-distanza'>📏 {corsa['distanza']}m</span>" if corsa['distanza'] else ""
                
                sito_html += f"<details class='corsa'><summary class='sub-tendina'><span>{titolo_pulito}</span> {badge_ora} {badge_dist}</summary>\n<table>\n<tr><th>N°</th><th>Cavallo</th><th>Peso</th><th>Fantino</th></tr>\n"
                
                for cav in corsa['cavalli']:
                    sito_html += f"<tr><td class='num'>[{cav['num']}]</td><td><b>{cav['nome']}</b></td><td>{cav['peso']}</td><td>{cav['fantino']}</td></tr>\n"
                
                sito_html += "</table>\n</details>\n"

            sito_html += "</div>\n</details>\n"

except Exception as e:
    sito_html += f"<br><div style='color:red; border:2px solid red; padding:10px;'><b>Errore del radar:</b> {e}</div>"

finally:
    sito_html += "</body></html>"
    with open(HTML_OUTPUT, "w", encoding="utf-8") as f:
        f.write(sito_html)
    try:
        driver.quit()
    except:
        pass
    print("Stampa completata con successo.")
