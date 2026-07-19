from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import re
import random
from datetime import datetime

print("📰 Accensione rotative de 'L'Eco del Galoppo'...")

DATA_OGGI = datetime.now().strftime("%d/%m/%Y")
HTML_OUTPUT = "eco_del_galoppo.html"

# --- IL CAVALLO DEL GIORNO (Ripristinato il tuo archivio interno) ---
campioni = [
    {"nome": "TAP DANCE CITY", "storia": "Indimenticabile dominatore della Japan Cup del 2003. Sotto una pioggia battente, ha imposto un ritmo infernale fin dalla partenza, trionfando in solitaria con un distacco abissale di 9 lunghezze."},
    {"nome": "RIBOT", "storia": "Il 'Cavallo del Secolo'. Imbattuto in 16 corse, leggenda assoluta che ha calcato anche l'erba di San Rossore a Pisa prima di conquistare l'Arc de Triomphe per due volte di fila."}
]
campione_oggi = random.choice(campioni)

# ==========================================
# 🕵️ MODULO INFILTRAZIONE NOTIZIE UNIVERSALE (Ripristinata la tua logica H1/H2/H3)
# ==========================================
def recupera_notizie(driver):
    html_news = ""
    
    fonti = [
        {"nome": "ITALIAN POST RACING", "url": "https://www.italianpostracing.it/"},
        {"nome": "EQUOS (GALOPPO)", "url": "https://equos.it/category/galoppo/"},
        {"nome": "RACING POST", "url": "https://www.racingpost.com/news/"},
        {"nome": "TDN EUROPE", "url": "https://www.thoroughbreddailynews.com/tdn-europe/"},
        {"nome": "ASIAN RACING REPORT", "url": "https://asianracingreport.com/"}
    ]

    print("\n-> Avvio Rassegna Stampa Internazionale...")
    
    for fonte in fonti:
        print(f"   [📻] Contatto redazione: {fonte['nome']}...")
        try:
            driver.get(fonte['url'])
            time.sleep(3) 
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            titoli = soup.find_all(['h1', 'h2', 'h3'])
            notizie_estratte = []
            
            for t in titoli:
                testo = t.get_text(strip=True)
                if len(testo) > 25 and testo not in notizie_estratte and "Menu" not in testo and "Search" not in testo:
                    notizie_estratte.append(testo)
                if len(notizie_estratte) == 2: 
                    break
            
            if not notizie_estratte:
                link_testi = soup.find_all('a')
                for a in link_testi:
                    testo = a.get_text(strip=True)
                    if len(testo) > 30 and testo not in notizie_estratte and "Cookie" not in testo:
                        notizie_estratte.append(testo)
                    if len(notizie_estratte) == 2:
                        break

            html_news += f'<div class="news-item"><div class="fonte">{fonte["nome"]}</div>'
            if notizie_estratte:
                for news in notizie_estratte:
                    html_news += f'<h4>{news}</h4>'
                print(f"        ✔️ Acquisite {len(notizie_estratte)} breaking news.")
            else:
                html_news += '<h4>Nessuna notizia rilevante al momento.</h4>'
                print("        ⚠️ Nessun titolo rilevato.")
            html_news += '</div>'
            
        except Exception as e:
            print(f"        ❌ Errore di connessione: {e}")
            html_news += f'<div class="news-item"><div class="fonte">{fonte["nome"]}</div><h4>Collegamento alla redazione fallito.</h4></div>'

    return html_news

# ==========================================
# AVVIO DEL MOTORE CHROME CLOUD E IMPAGINATORE HTML
# ==========================================
options = Options()
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

try:
    print("\n📡 Avvio del sistema cloud multi-radar antiblocco...")
    # L'unica modifica: usiamo webdriver_manager per gestire Chrome in cloud
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    blocco_notizie_dinamico = recupera_notizie(driver)

    # Ripristinato il tuo layout originale in scala di grigi
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
            .news-item h4 {{ margin: 0 0 4px 0; font-size: 15px; line-height: 1.4; font-family: 'Georgia', serif; font-weight: normal; }}
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
            <p class="sottotitolo" style="font-size: 12px; margin-top: 5px; text-transform: uppercase; border-top: 1px solid #000; display: inline-block; padding-top: 5px;">Edizione del: {DATA_OGGI}</p>
        </div>
        
        <div class="box-storico">
            <div class="box-titolo">*** Il Cavallo del Giorno ***</div>
            <b>{campione_oggi['nome']}</b><br><span style="font-size: 13px;">{campione_oggi['storia']}</span>
        </div>

        <div class="sezione-news">
            <div class="titolo-sezione">Rassegna Stampa Internazionale</div>
            {blocco_notizie_dinamico}
        </div>
        
        <div class="titolo-sezione">Partenti di Oggi</div>
    """

    menu_da_visitare = [
        {"nome": "Italia", "url": "https://www.ippica.biz/00_menu.asp", "base": "https://www.ippica.biz/0/14_tlx/"},
        {"nome": "Estero", "url": "https://www.ippica.biz/1/14_fnz/14_IB_progr_estere.asp?fnz=1&scroll=no&P01=2016&g=1", "base": "https://www.ippica.biz/1/14_tlx/"}
    ]
    
    link_validi = []
    
    # Ripristinata fedelmente la tua logica originale di estrazione
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
        print("\n❌ NESSUNA CORSA TROVATA (O palinsesto vuoto).")
    else:
        print(f"\n✅ TROVATE {len(link_validi)} RIUNIONI DI GALOPPO!\n")
        print("="*50)
        
        for item in link_validi:
            nome_stampato = item['nome']
            nome_terminale = nome_stampato.replace(" <span class='etichetta-estero'>INT</span>", " (ESTERO)")
            
            print(f"🏇 {nome_terminale}")
            print("-" * 50)
            
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

                print(f"\n  > {titolo_pulito} | 🕒 {corsa['orario'] or 'N/D'} | 📏 {corsa['distanza'] or 'N/D'}m")
                
                badge_ora = f"<span class='badge-ora'>🕒 {corsa['orario']}</span>" if corsa['orario'] else ""
                badge_dist = f"<span class='badge-distanza'>📏 {corsa['distanza']}m</span>" if corsa['distanza'] else ""
                
                sito_html += f"<details class='corsa'><summary class='sub-tendina'><span>{titolo_pulito}</span> {badge_ora} {badge_dist}</summary>\n<table>\n<tr><th>N°</th><th>Cavallo</th><th>Peso</th><th>Fantino</th></tr>\n"
                
                for cav in corsa['cavalli']:
                    print(f"  [{cav['num']}] {cav['nome'].ljust(20)} | Peso: {cav['peso']} | Fantino: {cav['fantino']}")
                    sito_html += f"<tr><td class='num'>[{cav['num']}]</td><td><b>{cav['nome']}</b></td><td>{cav['peso']}</td><td>{cav['fantino']}</td></tr>\n"
                
                sito_html += "</table>\n</details>\n"

            sito_html += "</div>\n</details>\n"
            print("="*50 + "\n")

except Exception as e:
    print(f"\n❌ Errore critico catturato: {e}")
    sito_html += f"<br><div style='color:red; border:2px solid red; padding:10px;'><b>Errore improvviso:</b> {e}</div>"

finally:
    sito_html += "</body></html>"
    with open(HTML_OUTPUT, "w", encoding="utf-8") as f:
        f.write(sito_html)
    print(f"\n✅ STAMPA HTML COMPLETATA E SALVATA IN '{HTML_OUTPUT}'.")
    try:
        driver.quit()
    except:
        pass
