import os
import requests
import feedparser
import re
from datetime import datetime, timedelta
from google import genai

# 1. Recupera i segreti dalla cassaforte di GitHub
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 2. Configura il client IA
client = genai.Client(api_key=GEMINI_API_KEY)

DATA_OGGI = datetime.now()

class OggettoNotizia:
    def __init__(self, title, link):
        self.title = str(title)
        self.link = str(link)

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

def contiene_asiatico(testo):
    try:
        return bool(re.search(r'[\u4e00-\u9FFF\u3040-\u309F\u30A0-\u30FF]', str(testo)))
    except:
        return False

# ==========================================
# RACCOLTA DATI (Dal tuo giornale)
# ==========================================
def raccoglia_notizie_per_ia():
    fonti = [
        {"nome": "ITALIAN POST RACING", "rss": "https://www.italianpostracing.it/feed/", "tipo": "diretto"},
        {"nome": "THOROUGHBRED DAILY NEWS", "rss": "https://www.thoroughbreddailynews.com/feed/", "tipo": "diretto"},
        {"nome": "ASIAN RACING REPORT", "rss": "https://asianracingreport.com/feed/", "tipo": "diretto"},
        {"nome": "BLOODHORSE (USA)", "rss": "https://news.google.com/rss/search?q=site:bloodhorse.com+when:7d&hl=en-US&gl=US&ceid=US:en", "tipo": "google"},
        {"nome": "PAULICK REPORT", "rss": "https://news.google.com/rss/search?q=site:paulickreport.com+when:7d&hl=en-US&gl=US&ceid=US:en", "tipo": "google"}
    ]
    
    testo_rss = ""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    for f in fonti:
        entries_finali = []
        try:
            res = requests.get(f['rss'], headers=headers, timeout=5)
            feed = feedparser.parse(res.content)
            if hasattr(feed, 'entries') and feed.entries:
                entries_finali = [OggettoNotizia(e.title, e.link) for e in feed.entries if hasattr(e, 'title') and hasattr(e, 'link')]
            
            if not entries_finali and f["tipo"] == "diretto":
                res_json = requests.get(f"https://api.rss2json.com/v1/api.json?rss_url={f['rss']}", timeout=5).json()
                if isinstance(res_json, dict) and res_json.get('status') == 'ok':
                    for item in res_json.get('items', []):
                        entries_finali.append(OggettoNotizia(item.get('title', ''), item.get('link', '#')))
            
            valide = 0
            for entry in entries_finali:
                if valide >= 2: break # Prendiamo le top 2 per fonte per non sovraccaricare il prompt
                titolo = getattr(entry, 'title', '')
                if f["tipo"] == "google" and " - " in titolo:
                    titolo = titolo.rsplit(" - ", 1)[0]
                if contiene_asiatico(titolo): continue
                testo_rss += f"- [{f['nome']}] {titolo}\n"
                valide += 1
        except:
            continue
    return testo_rss

def raccoglia_palinsesto_per_ia():
    oggi_str = DATA_OGGI.strftime('%Y-%m-%d')
    url = f"https://www.sportinglife.com/api/horse-racing/racing/racecards/{oggi_str}"
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    
    testo_palinsesto = ""
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            meetings = res.json() if isinstance(res.json(), list) else res.json().get('meetings', [])
            for m in meetings:
                if not isinstance(m, dict): continue
                races = m.get('races', [])
                nome_ipp = esplora_json(m, ['name', 'course_name', 'meeting_name', 'venue']) or "IPPODROMO"
                
                testo_palinsesto += f"\nIppodromo: {nome_ipp}\n"
                for r in races:
                    if not isinstance(r, dict): continue
                    ora = r.get('time', 'N/D')
                    titolo_c = r.get('race_name', r.get('name', 'Corsa'))
                    testo_palinsesto += f"  - Ore {ora}: {titolo_c}\n"
    except:
        testo_palinsesto = "Palinsesto non disponibile al momento."
    
    return testo_palinsesto

def manda_messaggio_telegram(testo):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": testo,
        "parse_mode": "HTML"
    }
    risposta = requests.post(url, json=payload)
    return risposta.status_code

def main():
    print("La Vedetta sta rastrellando notizie e palinsesto...")
    
    notizie = raccoglia_notizie_per_ia()
    palinsesto = raccoglia_palinsesto_per_ia()

    # Super-Prompt per Gemini 2.0 Flash
    prompt = f"""
    Sei un esperto opinionista e tipster di ippica (galoppo).
    Ti fornisco le notizie del giorno e il palinsesto odierno estratti dai feed ufficiali e da Sporting Life.
    
    NOTIZIE DEL GIORNO:
    {notizie}
    
    PALINSESTO ODIERNO:
    {palinsesto}
    
    Scrivi un "Briefing Mattutino" formattato con tag HTML di base (<b>, <i>) per Telegram.
    Crea esattamente queste 3 sezioni:
    1) 📰 <b>Le News:</b> Sintesi delle notizie più calde (max 3 punti chiave).
    2) 🏆 <b>Le Corse Imperdibili:</b> Segnala le 2 o 3 corse migliori o più importanti del palinsesto odierno.
    3) 🏇 <b>Da Tenere d'Occhio:</b> Estrai o suggerisci cavalli caldi o spunti tecnici interessanti in base ai dati forniti.
    
    Sii conciso, tecnico, usa un tono epico ma diretto. Evita introduzioni o conclusioni superflue, parti subito con le sezioni.
    """

    print("Chiedo il briefing all'Oracolo...")
    risposta_gemini = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt,
    )
    resoconto = risposta_gemini.text

    messaggio = f"🏇 <b>IL TUO BRIEFING MATTUTINO</b> 🏇\n\n{resoconto}"

    status = manda_messaggio_telegram(messaggio)
    if status == 200:
        print("Briefing consegnato con successo su Telegram!")
    else:
        print(f"Errore nell'invio del messaggio. Codice: {status}")

if __name__ == "__main__":
    main()
