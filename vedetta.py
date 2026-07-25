import os
import requests
import feedparser
import re
from datetime import datetime
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
    ora_attuale_utc_obj = datetime.utcnow()
    
    # ==========================================
    # MODALITÀ MATTINO: BRIEFING COMPLETO (PROMPT IN INGLESE)
    # ==========================================
    if ora_attuale_utc_obj.hour < 10:
        print("È mattina: La Vedetta sta rastrellando notizie e palinsesto...")
        notizie = raccoglia_notizie_per_ia()
        palinsesto = raccoglia_palinsesto_per_ia()

        if len(palinsesto) > 15000:
            palinsesto = palinsesto[:15000] + "\n\n[...PALINSESTO TRONCATO...]"

        prompt_sistema = "You are an expert international horse racing analyst and tipster. You are analytical, precise, and factual. You MUST write your final response entirely in Italian."
        prompt_utente = f"""
        I am providing you with today's horse racing news and the daily racecards extracted from official feeds.
        
        TODAY'S NEWS:
        {notizie}
        
        TODAY'S RACECARDS:
        {palinsesto}
        
        Write a "Briefing Mattutino" (Morning Briefing) formatted with basic HTML tags (<b>, <i>) for Telegram.
        You MUST write the entire text in Italian.
        
        Follow this strict editorial style. Do NOT invent facts. Do NOT confuse race names with horse names.
        
        1) 📰 <b>Il punto della situazione:</b> Write a solid, factual paragraph summarizing the actual news provided above. Link the events together logically.
        2) 🏆 <b>Le Corse Imperdibili:</b> Select 2 or 3 of the most important races from the racecards. Format as: <b>Ore [Time]</b> — <i>[Race Name]</i>. Provide a strictly technical and factual analysis of why these races are important today.
        3) 🏇 <b>Da Tenere d'Occhio:</b> Extract 2 or 3 specific horses mentioned in the news. Explain EXACTLY WHY they are important based ONLY on the provided text. No generic hyperbole.
        
        Do not add any introductory or concluding remarks. Start immediately with the sections.
        """

        risposta_groq = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_utente}
            ]
        )
        
        resoconto = risposta_groq.choices[0].message.content
        messaggio = f"🏇 <b>IL TUO BRIEFING MATTUTINO</b> 🏇\n\n{resoconto}"

        status = manda_messaggio_telegram(messaggio)
        if status == 200:
            print("Briefing mattutino consegnato!")

    # ==========================================
    # MODALITÀ POMERIGGIO: RADAR G1 MINIMAL (PROMPT IN INGLESE)
    # ==========================================
    else:
        print("Non è mattina. Attivazione RADAR G1 POMERIDIANO...")
        palinsesto = raccoglia_palinsesto_per_ia()
        
        if len(palinsesto) > 12000:
            palinsesto = palinsesto[:12000] + "\n\n[...PALINSESTO TRONCATO...]"
            
        prompt_radar_sistema = "You are an emergency horse racing radar. Your ONLY purpose is to scan the provided racecards for Group 1 (G1) races and extract their data. You are strictly factual. You MUST write your final response in Italian."
        prompt_radar_utente = f"""
        Here is today's horse racing schedule (racecards):
        
        {palinsesto}
        
        Search ONLY for Group 1 races (e.g., G1, Group 1, major international classics).
        
        RULES:
        - If you do NOT find any Group 1 race in the schedule, you MUST reply ONLY with this exact word: NESSUN_ALLARME
        - If you find a Group 1 race, write a message using EXACTLY AND ONLY this HTML format, copying the textual data directly from the racecard. Do NOT invent anything. Do NOT add any commentary.
        
        🚨 <b>ALLARME G1 IN PROGRAMMA OGGI</b> 🚨
        📍 <b>Ippodromo:</b> [Racecourse Name]
        ⏰ <b>Partenza:</b> Ore [Race Time from the schedule]
        🏆 <b>Corsa:</b> [Race Name]
        """

        risposta_groq = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0.0, # Temperatura 0 = Niente fantasia, solo fredda estrazione dati
            messages=[
                {"role": "system", "content": prompt_radar_sistema},
                {"role": "user", "content": prompt_radar_utente}
            ]
        )
        
        alert = risposta_groq.choices[0].message.content.strip()
        
        if alert == "NESSUN_ALLARME" or "NESSUN_ALLARME" in alert:
            print("Nessun G1 mondiale all'orizzonte. Silenzio radio mantenuto.")
        else:
            status = manda_messaggio_telegram(alert)
            if status == 200:
                print("🚨 ALLARME G1 CONSEGNATO SU TELEGRAM!")
            else:
                print(f"Errore nell'invio dell'allarme. Codice: {status}")

if __name__ == "__main__":
    main()
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
    ora_attuale_utc_obj = datetime.utcnow()
    ora_attuale_utc = ora_attuale_utc_obj.strftime('%H:%M')
    
    # ==========================================
    # MODALITÀ MATTINO: BRIEFING COMPLETO
    # ==========================================
    if ora_attuale_utc_obj.hour < 10:
        print("È mattina: La Vedetta sta rastrellando notizie e palinsesto...")
        notizie = raccoglia_notizie_per_ia()
        palinsesto = raccoglia_palinsesto_per_ia()

        if len(palinsesto) > 15000:
            palinsesto = palinsesto[:15000] + "\n\n[...PALINSESTO TRONCATO...]"

        prompt_sistema = "Sei un esperto opinionista e tipster di ippica (galoppo). Sii conciso, tecnico, usa un tono epico ma diretto."
        prompt_utente = f"""
        Ti fornisco le notizie del giorno e il palinsesto odierno estratti dai feed ufficiali e da Sporting Life.
        
        NOTIZIE DEL GIORNO:
        {notizie}
        
        PALINSESTO ODIERNO:
        {palinsesto}
        
        Scrivi un "Briefing Mattutino" formattato con tag HTML di base (<b>, <i>) per Telegram.
        Segui RIGOROSAMENTE questo nuovo stile editoriale d'autore:
        
        1) 📰 <b>Il punto della situazione:</b> Un unico blocco narrativo epico sulle notizie principali.
        2) 🏆 <b>Le Corse Imperdibili:</b> Per ogni corsa, orario esatto in grassetto e analisi tecnica profonda.
        3) 🏇 <b>Da Tenere d'Occhio:</b> Spunti tecnici sui cavalli.
        
        Niente introduzioni o conclusioni superflue.
        """

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
            print("Briefing mattutino consegnato!")

    # ==========================================
    # MODALITÀ POMERIGGIO: RADAR G1 TELECRONISTA
    # ==========================================
    else:
        print("Non è mattina. Attivazione RADAR G1 POMERIDIANO...")
        palinsesto = raccoglia_palinsesto_per_ia()
        notizie = raccoglia_notizie_per_ia() 
        
        if len(palinsesto) > 12000:
            palinsesto = palinsesto[:12000] + "\n\n[...PALINSESTO TRONCATO...]"
        if len(notizie) > 5000:
            notizie = notizie[:5000] + "\n\n[...NOTIZIE TRONCATE...]"
            
        prompt_radar_sistema = "Sei un sofisticato radar d'emergenza e un esaltante telecronista di ippica (galoppo internazionale)."
        prompt_radar_utente = f"""
        Ecco il palinsesto completo di oggi e le ultime notizie:
        
        NOTIZIE:
        {notizie}
        
        PALINSESTO:
        {palinsesto}
        
        ⏰ REGOLE TEMPORALI PER IL CALCOLO:
        - In questo esatto momento sono le ore {ora_attuale_utc} (Orario Universale UTC).
        - Tutti gli orari scritti nel PALINSESTO qui sopra sono normalizzati sul fuso orario del Regno Unito (UK Time).
        - Usa questa informazione per calcolare automaticamente e in modo preciso quanto tempo manca all'apertura delle gabbie!
        
        Cerca SOLO E SOLTANTO corse di importanza planetaria (Group 1, grandi classiche mondiali) previste per il pomeriggio/sera.
        
        REGOLE D'INGAGGIO:
        - Se NON trovi nessun G1, rispondi SOLO con questa parola esatta: NESSUN_ALLARME
        - Se trovi un G1, suona l'allarme scrivendo un messaggio adrenalinico seguendo ESATTAMENTE questo formato HTML:
        
        🚨 <b>ALLARME G1 IMMINENTE: [NOME DELLA CORSA]</b> 🚨
        
        📍 <b>Ippodromo:</b> [Nome Ippodromo]
        ⏰ <b>Partenza:</b> Ore [Orario della Corsa del Palinsesto] <i>(Mancano circa [Scrivi il tempo mancante da ora]!)</i>
        
        🏇 <b>I Protagonisti:</b> [Elenca i cavalli principali e i favoriti che si sfideranno, deducendoli dalle notizie o dalla tua conoscenza]
        
        🎙️ <b>La Telecronaca:</b> [Scrivi un commento epico in stile telecronista sportivo. Spiega la posta in palio e carica a mille l'attesa!]
        """

        risposta_groq = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0.2, 
            messages=[
                {"role": "system", "content": prompt_radar_sistema},
                {"role": "user", "content": prompt_radar_utente}
            ]
        )
        
        alert = risposta_groq.choices[0].message.content.strip()
        
        if alert == "NESSUN_ALLARME" or "NESSUN_ALLARME" in alert:
            print("Nessun G1 mondiale all'orizzonte. Silenzio radio mantenuto.")
        else:
            status = manda_messaggio_telegram(alert)
            if status == 200:
                print("🚨 ALLARME G1 CONSEGNATO SU TELEGRAM!")
            else:
                print(f"Errore nell'invio dell'allarme. Codice: {status}")

if __name__ == "__main__":
    main()
