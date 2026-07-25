import os
import requests
import feedparser
import re
from datetime import datetime, timedelta
from groq import Groq

# 1. Recupera i segreti dalla cassaforte di GitHub
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# 2. Configura il client IA (Groq)
client = Groq(api_key=GROQ_API_KEY)

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
# RACCOLTA DATI 
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
                if valide >= 2: break 
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
    # Recupera l'ora attuale in fuso orario UTC
    ora_attuale = datetime.utcnow().hour
    
    # Esegue il blocco del briefing SOLO se è prima delle 10:00 UTC (mattina)
    if ora_attuale < 10:
        print("È mattina: La Vedetta sta rastrellando notizie e palinsesto...")
        
        notizie = raccoglia_notizie_per_ia()
        palinsesto = raccoglia_palinsesto_per_ia()

        # LIMITATORE DI GIRI
        if len(palinsesto) > 15000:
            palinsesto = palinsesto[:15000] + "\n\n[...PALINSESTO TRONCATO PER LIMITI DI SPAZIO...]"

        prompt_sistema = "Sei un esperto opinionista e tipster di ippica (galoppo). Sii conciso, tecnico, usa un tono epico ma diretto."
        
        prompt_utente = f"""
        Ti fornisco le notizie del giorno e il palinsesto odierno estratti dai feed ufficiali e da Sporting Life.
        
        NOTIZIE DEL GIORNO:
        {notizie}
        
        PALINSESTO ODIERNO:
        {palinsesto}
        
        Scrivi un "Briefing Mattutino" formattato con tag HTML di base (<b>, <i>) per Telegram.
        Segui RIGOROSAMENTE questo nuovo stile editoriale d'autore:
        
        1) 📰 <b>Il punto della situazione:</b> NON usare elenchi puntati o trattini. Scrivi un unico blocco narrativo (testo continuo d'autore) bello corposo e discorsivo. Collega gli eventi tra loro e spiega il contesto e le implicazioni delle notizie sul mondo del turf.
        2) 🏆 <b>Le Corse Imperdibili:</b> Per ogni corsa, scrivi prima l'orario esatto di partenza in grassetto (es. <b>Ore 14:15</b> — <i>Nome Corsa</i>), seguito da un'analisi tecnica approfondita del perché è imperdibile (genealogia, posta in palio, qualità partenti).
        3) 🏇 <b>Da Tenere d'Occhio:</b> Un approfondimento fluido sui cavalli in rampa di lancio e sui soggetti caldi per i grandi appuntamenti stagionali, mantenendo un taglio tecnico e incisivo.
        
        Evita introduzioni o conclusioni superflue, parti subito con il testo delle sezioni.
        """

        print("Chiedo il briefing all'Oracolo (Groq Llama 3.3)...")
        
        # Chiamata API aggiornata per Groq
        risposta_groq = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_utente}
            ]
        )
        
        resoconto = risposta_groq.choices[0].message.content

        messaggio = f"🏇 <b>IL TUO BRIEFING MATTUTINO</b> 🏇\n\n{resoconto}"

        status = manda_messaggio_telegram(messaggio)
        if status == 200:
            print("Briefing consegnato con successo su Telegram!")
        else:
            print(f"Errore nell'invio del messaggio. Codice: {status}")
            
    else:
        print("Non è mattina. Salto l'invio del Briefing Mattutino per evitare spam.")
        # Spazio riservato: in futuro qui sotto metteremo il codice per gli allarmi G1 pomeridiani!

if __name__ == "__main__":
    main()
