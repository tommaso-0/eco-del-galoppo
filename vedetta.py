import os
import re
import json
import time
import html as html_lib
import requests
import feedparser
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from groq import Groq

# ==========================================
# 1. SETUP (INVARIATO RISPETTO ALL'ORIGINALE)
# ==========================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
MODELLO_IA = "openai/gpt-oss-120b"

DATA_OGGI = datetime.utcnow()

FUSO_UK = ZoneInfo("Europe/London")
STATO_FILE = Path("vedetta_state.json")
LIMITE_TELEGRAM = 4096
PATTERN_G1 = re.compile(r'\b(GROUP\s*1\b|GR\.?\s*1\b|GRADE\s*(1|I)\b|G1\b)', re.IGNORECASE)

# Provider IA: Gemini (primario, se configurato) con fallback su Groq
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")  # secret opzionale su GitHub
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")  # alias sempre aggiornato
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


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
                if risultato:
                    return risultato
    except Exception:
        pass
    return None


def contiene_asiatico(testo):
    try:
        return bool(re.search(r'[\u4e00-\u9FFF\u3040-\u309F\u30A0-\u30FF]', str(testo)))
    except Exception:
        return False


# ==========================================
# 2. RACCOLTA DATI (SCRAPING — INVARIATO)
# ==========================================
def raccoglia_notizie_per_ia():
    fonti = [
        {"nome": "ITALIAN POST RACING", "rss": "https://www.italianpostracing.it/feed/", "tipo": "diretto"},
        {"nome": "EUROPEAN RACING (UK/FR)", "rss": "https://news.google.com/rss/search?q=horse+racing+uk+OR+france+when:24h&hl=en-GB&gl=GB&ceid=GB:en", "tipo": "google"},
        {"nome": "ASIAN/AUS RACING", "rss": "https://news.google.com/rss/search?q=horse+racing+australia+OR+hong+kong+when:24h&hl=en-AU&gl=AU&ceid=AU:en", "tipo": "google"},
        {"nome": "BLOODHORSE (USA)", "rss": "https://news.google.com/rss/search?q=site:bloodhorse.com+when:48h&hl=en-US&gl=US&ceid=US:en", "tipo": "google"},
        {"nome": "PAULICK REPORT", "rss": "https://news.google.com/rss/search?q=site:paulickreport.com+when:48h&hl=en-US&gl=US&ceid=US:en", "tipo": "google"},
    ]

    testo_rss = ""
    headers = {"User-Agent": "Mozilla/5.0"}

    for f in fonti:
        try:
            res = requests.get(f['rss'], headers=headers, timeout=5)
            feed = feedparser.parse(res.content)
            valide = 0
            for entry in feed.entries:
                if valide >= 2:
                    break
                dt_pub = DATA_OGGI
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    dt_pub = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                if (DATA_OGGI - dt_pub).total_seconds() > (48 * 3600):
                    continue

                titolo = getattr(entry, 'title', '')
                if f["tipo"] == "google" and " - " in titolo:
                    titolo = titolo.rsplit(" - ", 1)[0]
                if contiene_asiatico(titolo):
                    continue

                descrizione = getattr(entry, 'description', getattr(entry, 'summary', 'Nessun dettaglio.'))
                descrizione = re.sub(r'<[^>]+>', '', descrizione).strip()[:250]
                testo_rss += f"- [{f['nome']}] TITOLO: {titolo}\n DETTAGLI: {descrizione}...\n"
                valide += 1
        except Exception:
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
                if not isinstance(m, dict):
                    continue
                races = m.get('races', [])
                nome_ipp = esplora_json(m, ['name', 'course_name', 'meeting_name', 'venue']) or "IPPODROMO"
                testo_palinsesto += f"\nIppodromo: {nome_ipp}\n"

                for r in races:
                    if not isinstance(r, dict):
                        continue
                    ora = r.get('time', 'N/D')
                    titolo_c = r.get('race_name', r.get('name', 'Corsa'))

                    partenti_str = ""
                    if any(kw in titolo_c.upper() for kw in ["GROUP ", "GRADE ", "LISTED", "CLASS 1", "STAKES"]):
                        ref = r.get('race_summary_reference')
                        race_id = ref.get('id') if isinstance(ref, dict) else None
                        if race_id:
                            try:
                                r_res = requests.get(f"https://www.sportinglife.com/api/horse-racing/race/{race_id}", headers=headers, timeout=5)
                                if r_res.status_code == 200:
                                    rides = r_res.json().get('rides', [])
                                    cavalli = [p.get('horse', {}).get('name', '') for p in rides if isinstance(p, dict) and isinstance(p.get('horse'), dict)]
                                    cavalli_validi = [c for c in cavalli if c][:12]
                                    if cavalli_validi:
                                        partenti_str = f" [PARTENTI CHIAVE: {', '.join(cavalli_validi)}]"
                            except Exception:
                                pass

                    testo_palinsesto += f" - Ore {ora}: {titolo_c}{partenti_str}\n"
    except Exception:
        testo_palinsesto = "Palinsesto non disponibile."

    return testo_palinsesto


# ==========================================
# 3. STATO PERSISTENTE (dedup briefing + allarmi)
# ==========================================
def carica_stato():
    oggi_str = DATA_OGGI.strftime("%Y-%m-%d")
    default = {"data": oggi_str, "briefing_inviato": False, "allarmi_inviati": []}
    if not STATO_FILE.exists():
        return default
    try:
        with open(STATO_FILE, "r", encoding="utf-8") as f:
            stato = json.load(f)
    except Exception:
        return default
    if stato.get("data") != oggi_str:
        return default  # nuovo giorno: si riparte da zero
    stato.setdefault("briefing_inviato", False)
    stato.setdefault("allarmi_inviati", [])
    return stato


def salva_stato(stato):
    try:
        with open(STATO_FILE, "w", encoding="utf-8") as f:
            json.dump(stato, f)
    except Exception as e:
        print(f"⚠️ Impossibile salvare lo stato locale: {e}")


# ==========================================
# 4. PROVIDER IA CON FALLBACK (Gemini → Groq)
# ==========================================
def _chiama_gemini(system, user, temperature):
    if not GEMINI_API_KEY:
        return None
    try:
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": temperature},
        }
        res = requests.post(f"{GEMINI_URL}?key={GEMINI_API_KEY}", json=payload, timeout=30)
        if res.status_code == 200:
            parti = res.json()["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parti).strip()
        if res.status_code == 429:
            print("⚠️ Gemini: quota esaurita per ora, passo a Groq.")
        else:
            print(f"⚠️ Gemini ha risposto {res.status_code}: {res.text[:300]}")
    except Exception as e:
        print(f"⚠️ Errore chiamata Gemini: {e}")
    return None


def _chiama_groq(system, user, temperature):
    try:
        risposta = client.chat.completions.create(
            model=MODELLO_IA,
            temperature=temperature,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        return risposta.choices[0].message.content
    except Exception as e:
        print(f"⚠️ Errore chiamata Groq: {e}")
        return None


def genera_testo_ia(system, user, temperature):
    """Prova Gemini (se configurato), ripiega su Groq se manca/fallisce/è in quota."""
    testo = _chiama_gemini(system, user, temperature)
    if testo:
        return testo
    if GEMINI_API_KEY:
        print("↪️ Fallback su Groq...")
    return _chiama_groq(system, user, temperature)


# ==========================================
# 5. RICONOSCIMENTO G1 DETERMINISTICO
# ==========================================
def e_gruppo_1(titolo_corsa):
    """Copre le diciture UK/IRE/FRA ('Group 1'), USA ('Grade 1'/'Grade I') e Asia/Oceania ('G1')."""
    return bool(PATTERN_G1.search(str(titolo_corsa).upper()))


# ==========================================
# 6. SANITIZZAZIONE OUTPUT IA PER TELEGRAM
# ==========================================
def sanitizza_html_telegram(testo):
    """Sostituisce pulisci_output_telegram: un `&` o `<` residuo non appartenente a un
    tag consentito manda in errore l'intera richiesta a Telegram (messaggio perso)."""
    if not testo:
        return ""
    testo = re.sub(r'<thought>.*?</thought>', '', testo, flags=re.DOTALL)
    testo = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', testo)
    testo = testo.replace('<br>', '\n').replace('<br/>', '\n').replace('</br>', '')
    testo = html_lib.escape(testo)
    for tag in ("b", "i", "u", "s", "code", "pre"):
        testo = testo.replace(f"&lt;{tag}&gt;", f"<{tag}>").replace(f"&lt;/{tag}&gt;", f"</{tag}>")
    return testo.strip()


def verifica_grounding(testo_grezzo, fonte_dati):
    """Controllo 'morbido' anti-allucinazione per il briefing: segnala SOLO nei log
    i nomi in grassetto che non compaiono nei dati di partenza. Non blocca l'invio."""
    nomi = re.findall(r'<b>(.*?)</b>', testo_grezzo)
    fonte_upper = fonte_dati.upper()
    sospetti = [n for n in nomi if len(n) > 3 and n.upper() not in fonte_upper]
    if sospetti:
        print(f"⚠️ Nomi in grassetto non trovati nei dati di origine (controllo manuale consigliato): {sospetti}")


def _spezza_messaggio(testo, limite=LIMITE_TELEGRAM):
    if len(testo) <= limite:
        return [testo]
    parti = []
    while len(testo) > limite:
        taglio = testo.rfind("\n", 0, limite)
        if taglio == -1:
            taglio = limite
        parti.append(testo[:taglio])
        testo = testo[taglio:].lstrip("\n")
    if testo:
        parti.append(testo)
    return parti


# ==========================================
# 7. INVIO TELEGRAM ROBUSTO (retry + fallback + split)
# ==========================================
def manda_messaggio_telegram(testo, tentativi=3):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    ultimo_status = None

    for parte in _spezza_messaggio(testo):
        inviato = False
        for tentativo in range(1, tentativi + 1):
            try:
                risposta = requests.post(
                    url, json={"chat_id": CHAT_ID, "text": parte, "parse_mode": "HTML"}, timeout=10,
                )
                ultimo_status = risposta.status_code
                if risposta.status_code == 200:
                    inviato = True
                    break

                print(f"❌ ERRORE TELEGRAM [{risposta.status_code}] (tentativo {tentativo}/{tentativi}): {risposta.text}")

                if risposta.status_code == 400:
                    risposta_plain = requests.post(
                        url, json={"chat_id": CHAT_ID, "text": re.sub('<[^<]+?>', '', parte)}, timeout=10,
                    )
                    ultimo_status = risposta_plain.status_code
                    inviato = risposta_plain.status_code == 200
                    break
            except requests.exceptions.RequestException as e:
                print(f"⚠️ Errore di rete verso Telegram (tentativo {tentativo}/{tentativi}): {e}")
                time.sleep(2 * tentativo)

        if not inviato:
            print(f"📝 IMPOSSIBILE CONSEGNARE QUESTA PARTE DEL MESSAGGIO:\n{parte}")

    return ultimo_status


# ==========================================
# 8. PALINSESTO IMMINENTE — STRUTTURATO (per il radar G1)
# ==========================================
def raccoglia_palinsesto_imminente(ore_finestra=5.5):
    oggi_str = DATA_OGGI.strftime('%Y-%m-%d')
    url = f"https://www.sportinglife.com/api/horse-racing/racing/racecards/{oggi_str}"
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    corse_trovate = []

    ora_attuale_uk = DATA_OGGI.replace(tzinfo=ZoneInfo("UTC")).astimezone(FUSO_UK)

    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            meetings = res.json() if isinstance(res.json(), list) else res.json().get('meetings', [])
            for m in meetings:
                if not isinstance(m, dict):
                    continue
                nome_ipp = esplora_json(m, ['name', 'course_name', 'meeting_name', 'venue']) or "IPPODROMO"

                for r in m.get('races', []):
                    if not isinstance(r, dict):
                        continue
                    ora_str = r.get('time', '')
                    if not ora_str:
                        continue
                    try:
                        ore, minuti = map(int, ora_str.split(':'))
                        race_time = ora_attuale_uk.replace(hour=ore, minute=minuti, second=0, microsecond=0)
                        diff_ore = (race_time - ora_attuale_uk).total_seconds() / 3600
                        if not (0 <= diff_ore <= ore_finestra):
                            continue
                    except Exception:
                        continue

                    titolo_c = r.get('race_name', r.get('name', 'Corsa'))
                    partenti_validi = []
                    ref = r.get('race_summary_reference')
                    race_id = ref.get('id') if isinstance(ref, dict) else None

                    if race_id:
                        try:
                            r_res = requests.get(
                                f"https://www.sportinglife.com/api/horse-racing/race/{race_id}",
                                headers=headers, timeout=5,
                            )
                            if r_res.status_code == 200:
                                rides = r_res.json().get('rides', [])
                                partenti_validi = [
                                    p.get('horse', {}).get('name', '')
                                    for p in rides
                                    if isinstance(p, dict) and isinstance(p.get('horse'), dict)
                                ]
                                partenti_validi = [c for c in partenti_validi if c]
                        except Exception:
                            pass

                    corse_trovate.append({
                        "id": f"{nome_ipp}|{ora_str}|{titolo_c}",  # chiave stabile per la deduplica
                        "ippodromo": nome_ipp,
                        "ora": ora_str,
                        "titolo": titolo_c,
                        "partenti": partenti_validi,
                        "e_g1": e_gruppo_1(titolo_c),
                    })
    except Exception:
        print("Errore connessione palinsesto imminente.")

    return corse_trovate


# ==========================================
# 9. GENERAZIONE ALLARME G1 CON VALIDAZIONE ANTI-ALLUCINAZIONE
# ==========================================
def genera_alert_g1(corsa):
    intestazione = (
        "🚨 <b>ALLARME G1 IN PARTENZA</b> 🚨\n"
        f"📍 <b>Ippodromo:</b> {corsa['ippodromo']}\n"
        f"⏰ <b>Partenza:</b> Ore {corsa['ora']}\n"
        f"🏆 <b>Corsa:</b> {corsa['titolo']}\n"
    )

    if not corsa["partenti"]:
        return intestazione + "📝 Partenti non ancora confermati dai dati ufficiali: nessuna analisi automatica per evitare invenzioni."

    prompt_sistema = (
        "Sei un analista tecnico di ippica per un bookmaker europeo. "
        "Rispondi ESCLUSIVAMENTE con un oggetto JSON valido, nessun altro testo, nessun markdown. "
        "REGOLA ASSOLUTA: puoi citare SOLO nomi presenti nella lista 'partenti' fornita. "
        "Non inventare cavalli, fantini o fatti non presenti nei dati forniti."
    )
    prompt_utente = json.dumps({
        "istruzioni": "Scrivi un'analisi tecnica di 2-3 righe della corsa, poi scegli esattamente 3 cavalli DALLA LISTA partenti con una valutazione tecnica di 1-2 righe ciascuno, in italiano.",
        "ippodromo": corsa["ippodromo"],
        "ora": corsa["ora"],
        "corsa": corsa["titolo"],
        "partenti": corsa["partenti"],
        "formato_risposta_json": {
            "analisi_corsa": "string",
            "protagonisti": [{"nome": "deve essere ESATTAMENTE uno dei partenti forniti", "valutazione": "string"}],
        },
    }, ensure_ascii=False)

    grezzo = genera_testo_ia(prompt_sistema, prompt_utente, 0.1)
    if not grezzo:
        elenco = ", ".join(corsa["partenti"][:12])
        return intestazione + f"📋 <b>Partenti confermati:</b> {elenco}"

    try:
        grezzo_pulito = re.sub(r'^```json|```$', '', grezzo.strip(), flags=re.MULTILINE).strip()
        dati = json.loads(grezzo_pulito)
        nomi_reali = [n.upper() for n in corsa["partenti"]]
        protagonisti_validi = [
            p for p in dati.get("protagonisti", [])
            if isinstance(p, dict) and p.get("nome", "").strip().upper() in nomi_reali
        ]
        if not protagonisti_validi:
            raise ValueError("Nessun protagonista valido tra i partenti reali.")

        corpo = f"📝 <b>Perizia Corsa:</b> {dati.get('analisi_corsa', '').strip()}\n\n📊 <b>I Protagonisti Principali:</b>\n"
        for p in protagonisti_validi[:3]:
            corpo += f"- <b>{p['nome']}:</b> {p.get('valutazione', '').strip()}\n"
        return intestazione + corpo
    except Exception as e:
        print(f"⚠️ Risposta IA non valida o con cavalli inventati, uso fallback senza analisi IA: {e}")
        elenco = ", ".join(corsa["partenti"][:12])
        return intestazione + f"📋 <b>Partenti confermati:</b> {elenco}"


# ==========================================
# 10. MAIN
# ==========================================
def main():
    stato = carica_stato()

    # ------------------------------------------
    # BRIEFING MATTUTINO — finestra larga + idempotente
    # ------------------------------------------
    if 5 <= DATA_OGGI.hour <= 8 and not stato["briefing_inviato"]:
        print(f"Finestra briefing attiva (ore {DATA_OGGI.hour} UTC): generazione in corso...")
        notizie = raccoglia_notizie_per_ia()
        palinsesto = raccoglia_palinsesto_completo()
        if len(palinsesto) > 15000:
            palinsesto = palinsesto[:15000] + "\n[...]"

        prompt_sistema = """You are the Senior Oddsmaker and Head Handicapper for a European bookmaker.
Your style is cynical, highly technical, and detailed.

CRITICAL RULES:
1. OUTPUT LANGUAGE: MUST be entirely in ITALIAN.
2. NO MARKDOWN: NEVER use ** for bold. Use ONLY <b> and <i> HTML tags.
3. MAX 3 HORSES: When analyzing a race, you are FORBIDDEN from listing all runners. You must pick exactly 3.
4. ACTIVE HORSES ONLY: For the "Da Tenere d'Occhio" section, you MUST select ACTIVE RACING HORSES. You are STRICTLY FORBIDDEN from selecting yearlings, foals, trainers, jockeys, or owners.
5. NEVER invent facts, horses, results, or quotes not present in the input data. If the input data is insufficient for a section, write "Dati insufficienti" instead of making something up.
6. COPY THE EXAMPLE STYLE: You must strictly copy the formatting, length, and depth of the example provided.
"""
        prompt_utente = f"""
[DATI DI INPUT ODIERNI]
NOTIZIE:
{notizie}

PALINSESTO:
{palinsesto}

[ESEMPIO DI OUTPUT PERFETTO CHE DEVI IMITARE]
📰 <b>Il punto della situazione:</b>
- Il galoppo europeo si infiamma con l'annuncio del rientro di City Of Troy a York; leggendo i dettagli, il team punta tutto sulle Juddmonte International su un terreno che si preannuncia compatto, ideale per le sue lunghe leve.
- Sul fronte americano, l'asta in Texas ha visto cifre da capogiro per i figli di Gunite, confermando che il mercato d'oltreoceano cerca disperatamente precocità e stalloni affermati.
- In Australia, il mercato dei fantini subisce uno scossone con la squalifica di J. McDonald. Le motivazioni fornite indicano un cambio di rotta severo da parte dei commissari, che rimescola le carte per le prossime corse a Randwick.

🏆 <b>Le Corse Imperdibili:</b>
<b>Ore 15:30</b> — <i>Prix Jacques Le Marois (Deauville)</i>
<b>Analisi del tracciato:</b> Il miglio in pista dritta di Deauville è un test spietato per i polmoni. Il terreno pesante di oggi annullerà i velocisti puri, favorendo chi ha stamina da vendere negli ultimi 200 metri e sangue freddo.
<b>I 3 Protagonisti:</b>
1. <b>Inspiral</b>: La regina del miglio. Se trova il varco ai 400 finali, la sua progressione è letale.
2. <b>Big Rock</b>: Un front-runner spietato. Proverà a stroncare tutti sul passo fin dall'apertura delle gabbie.
3. <b>Charyn</b>: Regolarissimo quest'anno, ha la solidità perfetta per raccogliere i cocci se i primi due si scannano.

<b>Ore 20:40</b> — <i>Bolton Landing Stakes (Saratoga)</i>
<b>Analisi del tracciato:</b> Pista in erba americana, dove lo scatto dal gabbione è tutto. I front-runner puri rischiano di cuocersi, ma chi resta troppo indietro nel traffico non recupera. Serve posizione tattica e un cambio di marcia violento.
<b>I 3 Protagonisti:</b>
1. <b>More Champagne</b>: Sulla carta ha i parziali migliori, ma il numero di steccato potrebbe costringerla agli straordinari.
2. <b>Side Quest</b>: Incognita legata al terreno, ma i rating recenti la mettono un gradino sopra le rivali se trova varchi.
3. <b>Extravaganzoo</b>: Outsider di lusso, da non sottovalutare se le favorite impostano un ritmo suicida.

🏇 <b>Da Tenere d'Occhio:</b>
- <b>Rosallion</b>: Il tre anni di Hannon ha dimostrato di avere un motore fuori dal comune nelle St James's Palace Stakes. Il suo target principale resta il miglio autunnale; se mantiene questa condizione, sarà il cavallo da battere in Europa.
- <b>Romantic Warrior</b>: L'asso di Hong Kong continua a macinare lavori impressionanti in pista mattutina. Con un rating ormai consolidato a livello globale, il suo rientro sui 2000 metri a Sha Tin è atteso per confermare la sua supremazia.
- <b>Fierceness</b>: Dopo i recenti alti e bassi, il team americano sembra aver trovato la quadra. Ha bisogno di condurre la corsa senza troppa pressione per rendere al meglio; il prossimo impegno in un Grade 1 ci dirà se è tornato il vero dominatore.

[IL TUO TURNO]
Ora, scrivi il VERO briefing utilizzando SOLO i [DATI DI INPUT ODIERNI].
Usa ESATTAMENTE la stessa struttura. Nel punto della situazione, usa i DETTAGLI delle notizie per scrivere 3 righe corpose. In "Da Tenere d'Occhio", scegli SOLO 3 CAVALLI DA CORSA ATTIVI (ignora umani o puledri d'asta). Nessun tag <thought>.
"""
        testo_grezzo = genera_testo_ia(prompt_sistema, prompt_utente, 0.3)
        if testo_grezzo:
            verifica_grounding(testo_grezzo, notizie + palinsesto)
            messaggio = f"🏇 <b>IL TUO BRIEFING MATTUTINO</b> 🏇\n\n{sanitizza_html_telegram(testo_grezzo)}"
            status = manda_messaggio_telegram(messaggio)
            if status == 200:
                stato["briefing_inviato"] = True
                salva_stato(stato)
                print("Briefing mattutino consegnato!")
            else:
                print(f"Briefing non consegnato (status {status}); si ritenta al prossimo run in finestra.")
        else:
            print("Nessun provider IA disponibile per il briefing; si ritenta al prossimo run in finestra.")

    # ------------------------------------------
    # RADAR G1 — filtro deterministico + dedup, gira sempre
    # ------------------------------------------
    print("Ricerca G1 in partenza nelle prossime 5.5 ore...")
    corse_imminenti = raccoglia_palinsesto_imminente(ore_finestra=5.5)
    corse_g1_nuove = [
        c for c in corse_imminenti
        if c["e_g1"] and c["id"] not in stato["allarmi_inviati"]
    ]

    if not corse_g1_nuove:
        print("Nessun nuovo G1 da segnalare (già avvisato in precedenza o nessuna corsa in finestra).")
        return

    for corsa in corse_g1_nuove:
        alert = sanitizza_html_telegram(genera_alert_g1(corsa))
        status = manda_messaggio_telegram(alert)
        if status == 200:
            stato["allarmi_inviati"].append(corsa["id"])
            salva_stato(stato)
            print(f"🚨 Allarme G1 consegnato: {corsa['titolo']} ({corsa['ippodromo']})")
        else:
            print(f"Allarme non consegnato per {corsa['titolo']}: si ritenta al prossimo run.")


if __name__ == "__main__":
    main()
