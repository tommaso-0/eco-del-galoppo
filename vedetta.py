import os
import requests
import feedparser
import re
import time
from datetime import datetime, timedelta
from groq import Groq

# 1. Recupera i segreti dalla cassaforte di GitHub
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# 2. Configura il client IA (Groq) - Usiamo il modello Llama 3.1 70B che è il più intelligente su Groq
client = Groq(api_key=GROQ_API_KEY)
MODELLO_IA = "openai/gpt-oss-120b"

DATA_OGGI = datetime.utcnow()

class OggettoNotizia:
    def __init__(self, title, link, published_dt):
        self.title = str(title)
        self.link = str(link)
        self.published = published_dt

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

def pulisci_output_telegram(testo):
    # Rimuove i pensieri nascosti
    testo_pulito = re.sub(r'<thought>.*?</thought>', '', testo, flags=re.DOTALL)
    # Converte il Markdown (**) in HTML (<b>) se l'IA fa di testa sua
    testo_pulito = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', testo_pulito)
    # Distrugge i tag HTML illegali per Telegram
    testo_pulito = testo_pulito.replace('<br>', '\n').replace('<br/>', '\n').replace('</br>', '')
    return testo_pulito.strip()
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
        try:
            res = requests.get(f['rss'], headers=headers, timeout=5)
            feed = feedparser.parse(res.content)
            
            valide = 0
            for entry in feed.entries:
                if valide >= 2: break 
                
                # FILTRO ANTI-ZOMBIE (Scarta notizie più vecchie di 48 ore)
                dt_pub = DATA_OGGI
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    dt_pub = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                
                if (DATA_OGGI - dt_pub).total_seconds() > (48 * 3600):
                    continue # Notizia troppo vecchia, saltala
                
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
        res = requests.get(url, headers=headers, timeout=15)
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
                    
                    # NOVITÀ: Estrae i partenti anche al mattino SOLO per le corse importanti (Group, Listed, Class 1)
                    partenti_str = ""
                    if any(kw in titolo_c.upper() for kw in ["GROUP ", "GRADE ", "LISTED", "CLASS 1", "STAKES"]):
                        race_id = r.get('race_summary_reference', {}).get('id') if isinstance(r.get('race_summary_reference'), dict) else None
                        if race_id:
                            try:
                                r_res = requests.get(f"https://www.sportinglife.com/api/horse-racing/race/{race_id}", headers=headers, timeout=5)
                                if r_res.status_code == 200:
                                    rides = r_res.json().get('rides', [])
                                    cavalli = [p.get('horse', {}).get('name', '') for p in rides if isinstance(p, dict) and isinstance(p.get('horse'), dict)]
                                    cavalli_validi = [c for c in cavalli if c][:12] # Prende i primi 12
                                    if cavalli_validi:
                                        partenti_str = f" [PARTENTI CHIAVE: {', '.join(cavalli_validi)}]"
                            except: pass
                            
                    testo_palinsesto += f"  - Ore {ora}: {titolo_c}{partenti_str}\n"
    except:
        testo_palinsesto = "Palinsesto non disponibile."
    return testo_palinsesto

# ==========================================
# RACCOLTA DATI (SOLO CORSE IMMINENTI + PARTENTI)
# ==========================================
def raccoglia_palinsesto_imminente(ore_finestra=5.5):
    oggi_str = DATA_OGGI.strftime('%Y-%m-%d')
    url = f"https://www.sportinglife.com/api/horse-racing/racing/racecards/{oggi_str}"
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    testo_palinsesto = ""
    ora_attuale_uk = DATA_OGGI + timedelta(hours=1) 
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
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
                        if 0 <= diff_ore <= ore_finestra:
                            corse_imminenti.append(r)
                    except: pass
                
                if corse_imminenti:
                    testo_palinsesto += f"\nIppodromo: {nome_ipp}\n"
                    for r in corse_imminenti:
                        ora = r.get('time', 'N/D')
                        titolo_c = r.get('race_name', r.get('name', 'Corsa'))
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
    except:
        testo_palinsesto = "Errore connessione palinsesto."
    return testo_palinsesto

def manda_messaggio_telegram(testo):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": testo, "parse_mode": "HTML"}
    risposta = requests.post(url, json=payload)
    
    # TRAPPOLA PER ERRORI: Se Telegram rifiuta, stampa il motivo esatto!
    if risposta.status_code != 200:
        print(f"❌ ERRORE TELEGRAM [{risposta.status_code}]: {risposta.text}")
        print(f"📝 IL TESTO CHE HA CAUSATO L'ERRORE ERA:\n{testo}")
        
    return risposta.status_code

def main():
# ==========================================
    # 1. MODALITÀ MATTINO: BRIEFING (SNAI STYLE)
    # ==========================================
    # MODALITÀ DEBUG: Forza l'esecuzione ignorando l'orario
    if True:
        print("È mattina (ore 7 UTC): Generazione Briefing in stile SNAI...")
        notizie = raccoglia_notizie_per_ia()
        palinsesto = raccoglia_palinsesto_completo()

        if len(palinsesto) > 15000: palinsesto = palinsesto[:15000] + "\n[...]"

        prompt_sistema = """You are the Senior Oddsmaker and Head Handicapper for a top tier EUROPEAN bookmaker. 
                Your style is cynical, highly technical, and engaging. 
                
                CRITICAL RULES:
                1. OUTPUT LANGUAGE: MUST be entirely in ITALIAN.
                2. NO MARKDOWN: NEVER use ** for bold. Use ONLY <b> and <i> HTML tags.
                3. GEOGRAPHICAL BALANCE: You MUST avoid being US-centric. If you select American news/races, you MUST actively balance it by selecting European (UK, France, Italy) or Asian/Middle Eastern news/races from the context.
                4. NO HORSE HALLUCINATIONS: Do not invent stats (e.g. "imbattuto in 5 partite"). Do not invent a horse's preferred running style if you don't know it. However, you CAN evaluate how their pedigree or the track layout might affect the race generically.
                5. CHAIN OF THOUGHT: Analyze facts in English inside <thought> ... </thought> first. Ensure geo-diversity.
                """
        
        prompt_utente = f"""
        TODAY'S NEWS: {notizie}
        TODAY'S SCHEDULE: {palinsesto}
        
        Write an engaging, technical "Briefing Mattutino".
        
        Structure:
        1) 📰 <b>Il punto della situazione:</b> 3-4 bullet points. Mix international news. Represent at least TWO different continents.
        
        2) 🏆 <b>Le Corse Imperdibili:</b> Select 2 prestigious races (mix the countries if possible). 
           Format: <b>Ore [Time]</b> — <i>[Race Name]</i>
           Comment: Write a dense paragraph of 4-5 lines for EACH race. Analyze the track profile, the ground, and the distance. DO NOT list all the runners. Select ONLY the top 3 most dangerous contenders from the [PARTENTI CHIAVE] list and write a cynical oddsmaker comment on their chances today based on the track.
           
        3) 🏇 <b>Da Tenere d'Occhio:</b> Select 3 real entities (horses, jockeys, or trainers) from the news. MUST include at least one European or Asian entity. 
           Write 2-3 lines of deep technical analysis for each. If a trainer, evaluate their stable form. If a yearling, evaluate the sire/dam market appeal.

        First, write your analysis inside <thought> tags. Then, output the Italian message.
        """
        risposta_groq = client.chat.completions.create(
            model=MODELLO_IA,
            temperature=0.3,
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_utente}
            ]
        )
        testo_grezzo = risposta_groq.choices[0].message.content
        messaggio_telegram = f"🏇 <b>IL TUO BRIEFING MATTUTINO</b> 🏇\n\n{pulisci_output_telegram(testo_grezzo)}"
        manda_messaggio_telegram(messaggio_telegram)
        print("Briefing mattutino consegnato!")

    # ==========================================
    # 2. RADAR G1 A FINESTRA (SNAI STYLE) - GIRA SEMPRE
    # ==========================================
    print("Ricerca G1 in partenza nelle prossime 5.5 ore...")
    palinsesto_imminente = raccoglia_palinsesto_imminente(ore_finestra=5.5)
    
    if not palinsesto_imminente.strip():
        print("Nessuna corsa rilevante nelle prossime ore.")
        return

    prompt_radar_sistema = """You are a highly precise autonomous tracker for Group 1 horse racing patterns.
    You analyze the schedule and extract ONLY top tier races (Group 1 / Grade 1 / G1).
    You execute conditional logic perfectly. You MUST output the final alert in ITALIAN."""
    
    prompt_radar_utente = f"""
    Analyze these upcoming races:
    
    {palinsesto_imminente}
    
    STRICT LOGIC:
    - If there is NO Group 1 (G1, Grade 1) race in the text, your ENTIRE output must be EXACTLY: NESSUN_ALLARME
    - Do NOT add a single word or thought tag if the answer is NESSUN_ALLARME.
    
    If you DO find a Group 1 race, think in English inside <thought> tags, then create an Italian technical alert:
    
    🚨 <b>ALLARME G1 IN PARTENZA</b> 🚨
    📍 <b>Ippodromo:</b> [Racecourse Name]
    ⏰ <b>Partenza:</b> Ore [Time]
    🏆 <b>Corsa:</b> [Race Name]
    
    📝 <b>Perizia Corsa:</b> [4-5 lines of SNAI oddsmaker analysis of the race scheme and context]
    
    📊 <b>I Protagonisti Principali:</b>
    [Select the top 3 horses from the PARTENTI CONFERMATI list]
    - <b>[Horse Name]:</b> [Technical assessment of chances, form, and distance aptitude]
    """

    risposta_groq = client.chat.completions.create(
        model=MODELLO_IA,
        temperature=0.1, 
        messages=[
            {"role": "system", "content": prompt_radar_sistema},
            {"role": "user", "content": prompt_radar_utente}
        ]
    )
    
    alert_grezzo = risposta_groq.choices[0].message.content.strip()
    alert = pulisci_output_telegram(alert_grezzo)
    
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
