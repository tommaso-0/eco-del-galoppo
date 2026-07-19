import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import re
import random
from datetime import datetime

DATA_OGGI = datetime.now().strftime("%d/%m/%Y")
HTML_OUTPUT = "eco_del_galoppo.html"

sito_html = ""

try:
    with open("memoir.txt", "r", encoding="utf-8") as f:
        linee = [line.strip() for line in f if "|" in line]
    
    if linee:
        scelta = random.choice(linee)
        nome_campione, storia_campione = scelta.split("|", 1)
        campione_oggi = {"nome": nome_campione.strip(), "storia": storia_campione.strip()}
    else:
        campione_oggi = {"nome": "ERRORE ARCHIVIO", "storia": "Il file memoir.txt e vuoto o formattato male."}
except Exception:
    campione_oggi = {"nome": "ARCHIVIO NON TROVATO", "storia": "Assicurati di aver creato il file memoir.txt nella stessa cartella dello script."}

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
                
                if len(testo) > 35 and "Menu" not in testo and "Search" not in testo and "Cookie" not in testo and "Privacy" not in testo:
                    link_assoluto = urljoin(fonte['url'], link_grezzo)
                    
                    if link_assoluto not in url_visti:
                        notizie_estratte.append({'titolo': testo, 'url': link_assoluto})
                        url_visti.add(link_assoluto)
                        
                if len(notizie_estratte) == 5:
                    break
                    
            html_news += f'<div class="news-item"><div class="fonte">{fonte["nome"]}</div>'
            if notizie_estratte:
                for news in notizie_estratte:
                    html_news += f'<h4><a href="{news["url"]}" target="_blank">{news["titolo"]}</a></h4>'
            else:
                html_news += '<h4>Nessuna notizia rilevante al momento.</h4>'
            html_news += '</div>'
            
        except Exception:
            html_news += f'<div class="news-item"><div class="fonte">{fonte["nome"]}</div><h4>Collegamento alla redazione fallito.</h4></div>'

    return html_news

options = uc.ChromeOptions()
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

try:
    # Rimosso il percorso locale, il cloud troverà da solo la sua versione di Chrome
    driver = uc.Chrome(options=options, use_subprocess=True, version_main=150)
    
    blocco_notizie_dinamico = recupera_notizie(driver)
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
            
            .titolo-sezione {{ font-weight: bold; font-size: 20px; text-transform: uppercase; border-bottom: 2px solid #000; padding-bottom: 5px; margin-bottom: 15px; font-family: 'Georgia', serif; }}
            
            .sezione-news-container {{
                max-height: 250px; 
                overflow-y: auto; 
                border: 1px solid #ccc; 
                padding: 15px; 
                background: #fff;
                margin-bottom: 30px;
                border-top: 4px double #000;
            }}
            
            .sezione-news-container::-webkit-scrollbar {{ width: 8px; }}
            .sezione-news-container::-webkit-scrollbar-track {{ background: #f1f1f1; border-left: 1px solid #ddd; }}
            .sezione-news-container::-webkit-scrollbar-thumb {{ background: #888; border-radius: 4px; }}
            .sezione-news-container::-webkit-scrollbar-thumb:hover {{ background: #555; }}

            .news-item {{ margin-bottom: 15px; }}
            .news-item h4 {{ margin: 0 0 6px 0; font-size: 14px; line-height: 1.4; font-family: 'Georgia', serif; font-weight: normal; }}
            
            .news-item h4 a {{ color: #111; text-decoration: none; display: block; }}
            .news-item h4 a:hover {{ text-decoration: underline; color: #555; }}
            
            .news-item .fonte {{ font-size: 11px; color: #333; text-transform: uppercase; font-weight: bold; border-bottom: 1px dashed #999; display: inline-block; margin-bottom: 4px; }}
            
            details.ippodromo {{ background-color: #fff; border: 1px solid #000; margin-bottom: 15px; }}
            summary.main-tendina {{ background-color: #222; color: #fff; padding: 12px; font-weight: bold; font-size: 15px; cursor: pointer; list-style: none; }}
            summary.main-tendina::-webkit-details-marker {{ display: none; }}
            summary.main-tendina::before {{ content: '[+] '; font-family: monospace; }}
            details[open] > summary.main-tendina::before {{ content: '[-] '; }}
            
            details.corsa {{ margin-bottom: 5px; border: 1px solid #ccc; background-color: #fafafa; }}
            summary.sub-tendina {{ background-color: #e0e0e0; color: #000; padding: 10px; font-weight: bold; font-size: 13px; cursor: pointer; list-style: none; border-bottom: 1px solid #aaa; text-transform: uppercase; display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }}
            summary.sub-tendina::-webkit-details-marker {{ display: none; }}
            summary.sub-tendina::before {{ content: '> '; font-size: 12px; font-family: monospace; font-weight: bold; }}
            details[open] > summary.sub-tendina::before {{ content: 'v '; }}
            
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
            <p class="sottotitolo" style="font-size: 12px; margin-top: 5px; text-transform: uppercase; border-top: 1px solid #000; display: inline-block; padding-top: 5px;">Edizione del: {DATA_OGGI}</p>
        </div>
        
        <div class="box-storico">
            <div class="box-titolo">*** Il Cavallo del Giorno ***</div>
            <b>{campione_oggi['nome']}</b><br><span style="font-size: 13px; display: inline-block; margin-top: 5px;">{campione_oggi['storia']}</span>
        </div>

        <div class="titolo-sezione">Rassegna Stampa Internazionale</div>
        <div class="sezione-news-container">
            {blocco_notizie_dinamico}
        </div>
        
        <div class="titolo-sezione">Partenti di Oggi</div>
    """

    menu_da_visitare = [
        {"nome": "Italia", "url": "https://www.ippica.biz/00_menu.asp", "base": "https://www.ippica.biz/0/14_tlx/"},
        {"nome": "Estero", "url": "https://www.ippica.biz/1/14_fnz/14_IB_progr_estere.asp?fnz=1&scroll=no&P01=2016&g=1", "base": "https://www.ippica.biz/1/14_tlx/"}
    ]
    
    link_validi = []
    
    for menu in menu_da_visitare:
        driver.get(menu['url'])
        time.sleep(4) 
        soup_menu = BeautifulSoup(driver.page_source, 'html.parser')
        
        for a_tag in soup_menu.find_all('a', href=True):
            href = a_tag['href'].strip()
            testo = a_tag.get_text(strip=True).upper()
            
            if '.asp?' in href.lower() and 'TG=T' not in href.upper():
                if 'CORSA=0' in href.upper() or testo == 'C':
                    
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
            time.sleep(3) 
            
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
                        
                    corsa_corrente["cavalli"].append({
                        "num": numero_formattato,
                        "nome": cavallo,
                        "peso": peso,
                        "fantino": fantino
                    })
                    
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
                
                badge_ora = f"<span class='badge-ora'>ORE {corsa['orario']}</span>" if corsa['orario'] else ""
                badge_dist = f"<span class='badge-distanza'>DIST. {corsa['distanza']}m</span>" if corsa['distanza'] else ""
                
                sito_html += f"<details class='corsa'><summary class='sub-tendina'><span>{titolo_pulito}</span> {badge_ora} {badge_dist}</summary>\n<table>\n<tr><th>N°</th><th>Cavallo</th><th>Peso</th><th>Fantino</th></tr>\n"
                
                for cav in corsa['cavalli']:
                    sito_html += f"<tr><td class='num'>[{cav['num']}]</td><td><b>{cav['nome']}</b></td><td>{cav['peso']}</td><td>{cav['fantino']}</td></tr>\n"
                
                sito_html += "</table>\n</details>\n"

            sito_html += "</div>\n</details>\n"

except Exception as e:
    sito_html += f"<br><div style='border:1px solid #000; padding:10px;'><b>Errore generico di elaborazione:</b> {e}</div>"

finally:
    sito_html += "</body></html>"
    with open(HTML_OUTPUT, "w", encoding="utf-8") as f:
        f.write(sito_html)
    try:
        driver.quit()
    except:
        pass
