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

DATA_OGGI = datetime.utcnow()

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
# RACCOLTA DATI (NOTIZIE E PALINSESTO COMPLETO)
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
    headers = {"User-Agent": "Mozilla/5.0"}
    for f in fonti:
        entries_finali = []
        try:
            res = requests.get(f['rss'], headers=headers, timeout=5)
            feed = feedparser.parse(res.content)
            if hasattr(feed, 'entries') and feed.entries:
                entries_finali = [OggettoNotizia(e.title, e.link) for e in feed.entries if hasattr(e, 'title') and hasattr(e, 'link')]
            
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

def raccoglia_palinsesto_completo():
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
        testo_palinsesto = "Palinsesto non disponibile."
    return testo_palinsesto

# ==========================================
# RACCOLTA DATI (SOLO CORSE IMMINENTI + PARTENTI)
# ==========================================
def raccoglia_palinsesto_imminente(ore_finestra=3.5):
    oggi_str = DATA_OGGI.strftime('%Y-%m-%d')
    url = f"https://www.sportinglife.com/api/horse-racing/racing/racecards/{oggi_str}"
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    testo_palinsesto = ""
    
    # Orario UK per il calcolo (Sporting Life usa UK Time)
    ora_attuale_uk = DATA_OGGI + timedelta(hours=1) 
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            meetings = res.json() if isinstance(res.json(), list) else res.json().get('meetings', [])
            for m in meetings:
                if not isinstance(m, dict): continue
                nome_ipp = esplora_json(m, ['name', 'course_name', 'meeting_name', 'venue']) or "IPPODROMO"
                races = m.get('races', [])
                
                corse_imminenti = []
                for r in races:
                    if not isinstance(r, dict): continue
                    ora_str = r.get('time', '')
                    if not ora_str: continue
                    
                    try:
                        ore, minuti = map(int, ora_str.split(':'))
                        race_time = ora_attuale_uk.replace(hour=ore, minute=minuti, second=0)
                        diff_ore = (race_time - ora_attuale_uk).total_seconds() / 3600
                        
                        # Filtro a finestra: solo corse che partono entro le prossime X ore
                        if 0 <= diff_ore <= ore_finestra:
                            corse_imminenti.append(r)
                    except:
                        pass
                
                if corse_imminenti:
                    testo_palinsesto += f"\nIppodromo: {nome_ipp}\n"
                    for r in corse_imminenti:
                        ora = r.get('time', 'N/D')
                        titolo_c = r.get('race_name', r.get('name', 'Corsa'))
                        
                        # Cacciatore di Partenti (solo per le imminenti)
                        partenti_str = ""
                        race_id = r.get('race_summary_reference', {}).get('id') if isinstance(r.get('race_summary_reference'), dict) else None
                        if race_id:
                            try:
                                r_res = requests.get(f"https://www.sportinglife.com/api/horse-racing/race/{race_id}", headers=headers, timeout=5)
                                if r_res.status_code == 200:
                                    rides = r_res.json().get('rides', [])
                                    cavalli = [p.get('horse', {}).get('name', '') for p in rides if isinstance(p, dict) and isinstance(p.get('horse'), dict)]
                                    cavalli_validi = [c for c in cavalli if c]
                                    if cavalli_validi:
                                        partenti_str = f" [PARTENTI CONFERMATI: {', '.join(cavalli_validi)}]"
                            except: pass
                            
                        testo_palinsesto += f"  - Ore {ora}: {titolo_c}{partenti_str}\n"
    except Exception as e:
        testo_palinsesto = "Errore connessione palinsesto."
    return testo_palinsesto

def manda_messaggio_telegram(testo):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": testo, "parse_mode": "HTML"}
    risposta = requests.post(url, json=payload)
    return risposta.status_code

def main():
    # ==========================================
    # MODALITÀ MATTINO: BRIEFING (SNAI STYLE)
    # ==========================================
    if DATA_OGGI.hour < 10:
        print("È mattina: Generazione Briefing in stile SNAI...")
        notizie = raccoglia_notizie_per_ia()
        palinsesto = raccoglia_palinsesto_completo()

        if len(palinsesto) > 15000: palinsesto = palinsesto[:15000] + "\n[...]"

        prompt_sistema = "You are an elite Oddsmaker and technical analyst for SNAI (Italy). You are strictly factual, analyzing form, tactics, distance, and class. You NEVER hallucinate names. You MUST write entirely in Italian."
        prompt_utente = f"""
        TODAY'S NEWS: {notizie}
        TODAY'S SCHEDULE: {palinsesto}
        
        Write a "Briefing Mattutino" (Morning Briefing) formatted with HTML tags (<b>, <i>) for Telegram.
        Write entirely in Italian using a professional, technical Oddsmaker tone (e.g., discussing distance suitability, recent Group performances, ground).
        
        1) 📰 <b>Il punto della situazione:</b> A factual summary of the news provided.
        2) 🏆 <b>Le Corse Imperdibili:</b> Select 2 major races from the schedule. Format: <b>Ore [Time]</b> — <i>[Race Name]</i>. Explain technically why they are important.
        3) 🏇 <b>Da Tenere d'Occhio:</b> Extract 2-3 specific horses mentioned in the news. Write a technical profile for each (pedigree, preferred distance, recent form, running style), exactly like a SNAI Oddsmaker comment. Do NOT use hyperbole.
        """

        risposta_groq = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_utente}
            ]
        )
        messaggio = f"🏇 <b>IL TUO BRIEFING MATTUTINO</b> 🏇\n\n{risposta_groq.choices[0].message.content}"
        manda_messaggio_telegram(messaggio)
        print("Briefing mattutino consegnato!")

    # ==========================================
    # MODALITÀ POMERIGGIO: RADAR G1 A FINESTRA (SNAI STYLE)
    # ==========================================
    else:
        print("Pomeriggio/Sera: Ricerca G1 in partenza nelle prossime 3 ore...")
        palinsesto_imminente = raccoglia_palinsesto_imminente(ore_finestra=3.5)
        
        if not palinsesto_imminente.strip():
            print("Nessuna corsa rilevante nelle prossime ore.")
            return

        prompt_radar_sistema = "You are an elite Oddsmaker for SNAI. You analyze upcoming horse races objectively. You must write entirely in Italian."
        prompt_radar_utente = f"""
        Here are the races starting in the NEXT 3 HOURS, including the exact confirmed runners [PARTENTI CONFERMATI: ...]:
        
        {palinsesto_imminente}
        
        Search ONLY for Group 1 (G1, Grade 1) races.
        
        RULES:
        - If NO Group 1 races are in this specific list, reply ONLY with: NESSUN_ALLARME
        - If you find a Group 1 race, create a technical alert formatted EXACTLY like this:
        
        🚨 <b>ALLARME G1 IN PARTENZA</b> 🚨
        📍 <b>Ippodromo:</b> [Racecourse Name]
        ⏰ <b>Partenza:</b> Ore [Time]
        🏆 <b>Corsa:</b> [Race Name]
        
        📝 <b>Commento Corsa:</b> [Write a SNAI-style technical overview: evaluate the race scheme, the absolute favorite, distance, and context]
        
        📊 <b>I Protagonisti:</b>
        [For the top 3 or 4 horses from the PARTENTI CONFERMATI list, write a bullet point]
        - <b>[Horse Name]:</b> [Write a technical Oddsmaker profile: assess its form, running style, recent G1 results, and chances today]
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
            print("Nessun G1 nella finestra oraria attuale. Silenzio radio mantenuto.")
        else:
            status = manda_messaggio_telegram(alert)
            if status == 200:
                print("🚨 ALLARME G1 CONSEGNATO SU TELEGRAM!")
            else:
                print(f"Errore Telegram: {status}")

if __name__ == "__main__":
    main()
