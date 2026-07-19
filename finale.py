from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import re
import random
import os
from datetime import datetime

DATA_OGGI = datetime.now().strftime("%d/%m/%Y")
HTML_OUTPUT = "eco_del_galoppo.html"

# --- 1. GESTIONE MEMOIR ANTICRASH ED INTELLIGENTE ---
campione_oggi = {"nome": "IL CAVALLO DEL GIORNO", "storia": "Nessuna storia disponibile nell'archivio per l'edizione odierna."}
memoir_file = None

# Cerca il file ignorando le maiuscole/minuscole (es. trova sia memoir.txt che Memoir.txt)
for f in os.listdir('.'):
    if f.lower() == 'memoir.txt':
        memoir_file = f
        break

if memoir_file:
    try:
        with open(memoir_file, "r", encoding="utf-8") as f:
            linee = [line.strip() for line in f if "|" in line]
        if linee:
            scelta = random.choice(linee)
            nome_campione, storia_campione = scelta.split("|", 1)
            campione_oggi = {"nome": nome_campione.strip(), "storia": storia_campione.strip()}
    except Exception as e:
        print(f"Errore nella lettura del memoir: {e}")

# --- 2. RECUPERO NOTIZIE ---
def recupera_notizie(driver):
    html_news = ""
    fonti = [
        {"nome": "ITALIAN POST RACING", "url": "https://www.italianpostracing.it/"},
        {"nome": "EQUOS (GALOPPO)", "url": "https://equos.it/category/galoppo/"},
        {"nome": "RACING POST", "url": "https://www.racingpost.com/news/"},
        {"nome": "TDN EUROPE", "url": "https://www.thoroughbreddailynews.com/tdn-europe/"},
        {"nome": "ASIAN RACING REPORT", "url": "https://asianracingreport.com/"}
    ]
    
    for fonte in fonti:
        try:
            driver.get(fonte['url'])
            time.sleep(3) 
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            link_testi = soup.find_all('a', href=True)
            notizie_estratte = []
            url_visti = set()
            
            for a in link_testi:
                testo = a.get_text(strip=True)
                link_grezzo = a['href'].strip()
                if len(testo) > 35 and not any(escluso in testo for escluso in ["Menu", "Search", "Cookie", "Privacy"]):
                    link_assoluto = urljoin(fonte['url'], link_grezzo)
                    if link_assoluto not in url_visti:
                        notizie_estratte.append({'titolo': testo, 'url': link_assoluto})
                        url_visti.add(link_assoluto)
                if len(notizie_estratte) == 5:
                    break
                    
            html_news += f'<div class="news-item"><div class="fonte">{fonte["nome"]}</div>'
            if notizie_estratte:
                for news in notizie_estratte:
                    html_news += f'<div class="singola-notizia"><a href="{news["url"]}" target="_blank">{news["titolo"]}</a></div>'
            else:
                html_news += '<div class="singola-notizia">Nessuna notizia rilevante.</div>'
            html_news += '</div>'
        except Exception:
            html_news += f'<div class="news-item"><div class="fonte">{fonte["nome"]}</div><div class="singola-notizia">Collegamento alla redazione fallito.</div></div>'
    return html_news

# --- 3. CONFIGURAZIONE DRIVER ---
options = Options()
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

sito_html = ""

try:
    print("Avvio del browser...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    print("Recupero notizie in corso...")
    blocco_notizie_dinamico = recupera_notizie(driver)
    
    # HTML E CSS
    sito_html = f"""
    <!DOCTYPE html>
    <html lang="it">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>L'Eco del Galoppo</title>
        <style>
            body {{ font-family: 'Georgia', serif; background-color: #f4f3ee; color: #2b2b2b; margin: 0; padding: 20px; line-height: 1.6; }}
            .container {{ max-width: 900px; margin: 0 auto; background: #fff; padding: 30px; border: 1px solid #d3d3d3; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }}
            .header {{ text-align: center; border-bottom: 5px double #111; padding-bottom: 20px; margin-bottom: 30px; }}
            .header h1 {{ margin: 0; font-family: 'Georgia', serif; font-size: 38px; text-transform: uppercase; font-weight: bold; letter-spacing: 2px; }}
            .header p.sottotitolo {{ margin: 10px 0 0 0; font-style: italic; font-size: 16px; color: #555; }}
            .data-edizione {{ font-size: 13px; text-transform: uppercase; border-top: 1px solid #111; display: inline-block; padding-top: 5px; margin-top: 10px; font-weight: bold; }}
            .box-storico {{ border: 2px solid #8b0000; padding: 20px; margin-bottom: 40px; background-color: #faf9f6; border-radius: 4px; }}
            .box-titolo {{ font-weight: bold; text-align: center; border-bottom: 1px solid #8b0000; padding-bottom: 10px; margin-bottom: 15px; text-transform: uppercase; color: #8b0000; font-size: 18px; }}
            .storico-testo {{ font-size: 15px; text-align: justify; }}
            .titolo-sezione {{ font-weight: bold; font-size: 24px; text-transform: uppercase; border-bottom: 3px solid #111; padding-bottom: 5px; margin-bottom: 25px; margin-top: 40px; }}
            .news-item {{ background: #fff; padding: 25px; margin-bottom: 25px; border: 1px solid #e0e0e0; border-radius: 6px; box-shadow: 0 2px 5px rgba(0,0,0,0.03); }}
            .news-item .fonte {{ font-family: 'Arial', sans-serif; font-size: 14px; font-weight: bold; color: #8b0000; text-transform: uppercase; border-bottom: 2px solid #8b0000; padding-bottom: 5px; margin-bottom: 15px; display: inline-block; letter-spacing: 1px; }}
            .singola-notizia {{ margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px dashed #ddd; }}
            .singola-notizia:last-child {{ margin-bottom: 0; padding-bottom: 0; border-bottom: none; }}
            .singola-notizia a {{ color: #1a1a1a; text-decoration: none; font-size: 17px; font-weight: bold; display: block; line-height: 1.4; transition: color 0.2s; }}
            .singola-notizia a:hover {{ color: #8b0000; text-decoration: underline; }}
            details.ippodromo {{ background-color: #fff; border: 1px solid #111; margin-bottom: 20px; border-radius: 4px; overflow: hidden; }}
            summary.main-tendina {{ background-color: #2b2b2b; color: #fff; padding: 15px; font-weight: bold; font-size: 16px; cursor: pointer; list-style: none; text-transform: uppercase; }}
            details.corsa {{ margin: 10px; border: 1px solid #ccc; background-color: #fafafa; }}
            summary.sub-tendina {{ background-color: #e9e9e9; color: #111; padding: 12px; font-weight: bold; font-size: 14px; cursor: pointer; list-style: none; border-bottom: 1px solid #bbb; text-transform: uppercase; }}
            .badge-ora, .badge-distanza {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; border: 1px solid #999; margin-left: 10px; font-family: 'Arial', sans-serif; }}
            .badge-ora {{ background: #fff; color: #111; }}
            .badge-distanza {{ background: #555; color: #fff; border-color: #222; }}
            table {{ width: 100%; border-collapse: collapse; font-size: 14px; background-color: #fff; font-family: 'Arial', sans-serif; }}
            th, td {{ padding: 12px 8px; border-bottom: 1px solid #eee; text-align: left; }}
            th {{ background-color: #f5f5f5; text-transform: uppercase; color: #555; font-size: 12px; }}
            .num {{ font-weight: bold; width: 40px; text-align: center; background: #fafafa; border-right: 1px solid #eee; }}
            .etichetta-estero {{ font-size: 11px; color: #fff; background: #8b0000; padding: 3px 6px; margin-left: 10px; border-radius: 3px; font-family: 'Arial', sans-serif; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>L'Eco del Galoppo</h1>
                <p class="sottotitolo">"La nostra dose quotidiana di zoccoli e gloria."</p>
                <div class="data-edizione">Edizione del: {DATA_OGGI}</div>
            </div>
            
            <div class="box-storico">
                <div class="box-titolo">*** Il Cavallo del Giorno ***</div>
                <div class="storico-testo"><b>{campione_oggi['nome']}</b><br><br>{campione_oggi['storia']}</div>
            </div>

            <div class="titolo-sezione">Rassegna Stampa Internazionale</div>
            <div class="sezione-news-container">
                {blocco_notizie_dinamico}
            </div>
            
            <div class="titolo-sezione">Partenti di Oggi</div>
    """

    print("Ricerca corse su ippica.biz (metodo classico)...")
    menu_da_visitare = [
        {"nome": "Italia", "url": "https://www.ippica.biz/00_menu.asp", "base": "https://www.ippica.biz/0/14_tlx/"},
        {"nome": "Estero", "url": "https://www.ippica.biz/1/14_fnz/14_IB_progr_estere.asp?fnz=1&scroll=no&P01=2016&g=1", "base": "https://www.ippica.biz/1/14_tlx/"}
    ]
    
    link_validi = []
    
    for menu in menu_da_visitare:
        driver.get(menu['url'])
        time.sleep(4) 
        soup_menu = BeautifulSoup(driver.page_source, 'html.parser')
        
        # QUI HO REINSERITO LA TUA LOGICA ORIGINALE CHE FUNZIONAVA PERFETTAMENTE
        for a_tag in soup_menu.find_all('a', href=True):
            href = a_tag['href'].strip()
            testo = a_tag.get_text(strip=True).upper()
            
            if '.asp?' in href.lower() and 'TG=T' not in href.upper():
                if 'CORSA=0' in href.upper() or testo == 'C' or 'IPPO=' in href.upper():
                    
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
            driver.get(item['url'])
            time.sleep(3) 
            sito_html += f"<details class='ippodromo'><summary class='main-tendina'>+ {item['nome']}</summary>\n<div style='padding: 10px;'>\n"
            
            corse_ippodromo = []
            corsa_corrente = {"titolo": "CORSA 1", "orario": "", "distanza": "", "cavalli": []}
            num_corsa = 1
            last_num = 999
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            for riga in soup.find_all('tr'):
                celle = [c.get_text(strip=True) for c in riga.find_all(['td', 'th'])]
                testo_riga = " ".join(celle).upper()
                if not celle or "CAVALLO" in testo_riga: continue
                
                match_ora = re.search(r'(?:ORE|ALLE)\s*(\d{1,2}[:\.]\d{2})', testo_riga)
                if match_ora and not corsa_corrente["orario"]: corsa_corrente["orario"] = match_ora.group(1).replace(".", ":")
                
                testo_dist_pulito = testo_riga.replace(".", "").replace(",", "")
                match_dist = re.search(r'(?:METRI|MT|\bM\b)\s*(\d{3,4})|(\d{3,4})\s*(?:METRI|MT|\bM\b)', testo_dist_pulito)
                if match_dist and not corsa_corrente["distanza"]: corsa_corrente["distanza"] = match_dist.group(1) if match_dist.group(1) else match_dist.group(2)

                is_horse = False
                if len(celle) >= 5:
                    num_raw = celle[1].replace(".", "").replace("°", "").strip()
                    if num_raw.isdigit(): is_horse = True

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
                        peso, fantino = val5, val4
                    else:
                        peso, fantino = val4, val5
                        
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
            
            if corsa_corrente["cavalli"]: corse_ippodromo.append(corsa_corrente)
                
            for corsa in corse_ippodromo:
                titolo_pulito = re.sub(r'(?i)(?:-?\s*ORE\s*\d{1,2}[:\.]\d{2})', '', corsa['titolo'])
                titolo_pulito = re.sub(r'(?i)(?:-?\s*(?:METRI|MT\.?|M\.?)\s*\d{3,4})', '', titolo_pulito)
                titolo_pulito = re.sub(r'(?i)(?:\d{3,4}\s*(?:METRI|MT\.?|M\.?))', '', titolo_pulito)
                titolo_pulito = titolo_pulito.strip(' -')
                if not titolo_pulito: titolo_pulito = f"CORSA"
                
                badge_ora = f"<span class='badge-ora'>ORE {corsa['orario']}</span>" if corsa['orario'] else ""
                badge_dist = f"<span class='badge-distanza'>DIST. {corsa['distanza']}m</span>" if corsa['distanza'] else ""
                
                sito_html += f"<details class='corsa'><summary class='sub-tendina'><span>{titolo_pulito}</span> {badge_ora} {badge_dist}</summary>\n<table>\n<tr><th>N°</th><th>Cavallo</th><th>Peso</th><th>Fantino</th></tr>\n"
                for cav in corsa['cavalli']:
                    sito_html += f"<tr><td class='num'>[{cav['num']}]</td><td><b>{cav['nome']}</b></td><td>{cav['peso']}</td><td>{cav['fantino']}</td></tr>\n"
                sito_html += "</table>\n</details>\n"
            sito_html += "</div>\n</details>\n"

except Exception as e:
    print(f"ERRORE CRITICO: {e}")
    sito_html += f"<br><div style='border:2px solid red; padding:20px; background:#ffe6e6;'><b>Errore generico di elaborazione:</b><br>{e}</div>"

finally:
    sito_html += "</div></body></html>" 
    with open(HTML_OUTPUT, "w", encoding="utf-8") as f:
        f.write(sito_html)
    try:
        driver.quit()
    except:
        pass
    print("Stampa conclusa.")
