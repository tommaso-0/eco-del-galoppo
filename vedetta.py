"""
VEDETTA.PY — SEZIONI OTTIMIZZATE (Briefing Mattutino + Radar G1) — v2
======================================================================
Sostituisce SOLO le parti relative a briefing/allarmi. Le funzioni di
scraping non toccate (raccoglia_notizie_per_ia, raccoglia_palinsesto_completo,
esplora_json, contiene_asiatico, classe OggettoNotizia) restano identiche:
non copiarle da qui, lasciale dove sono nel file originale.

COSA CAMBIA RISPETTO ALLA PRIMA VERSIONE
------------------------------------------
1. Niente Supabase: stato su file locale (vedetta_state.json), MA la
   persistenza tra un'esecuzione e l'altra su GitHub Actions richiede un
   commit di quel file a fine workflow — vedi lo snippet YAML che ti ho
   dato in chat. Il codice qui presume solo che il file esista/sopravviva;
   non sa nulla di git.

2. Provider IA con fallback automatico: Gemini (Flash-Lite, quota gratuita
   più alta) come primario, Groq come riserva se Gemini non è configurato,
   fallisce o va in quota-exceeded (429). Serve un nuovo secret opzionale
   GEMINI_API_KEY — se non lo imposti, si usa direttamente Groq come prima.

3. Anti-allucinazione sugli allarmi G1: l'IA risponde in JSON e può citare
   SOLO cavalli presenti nella lista reale dei partenti che le passiamo.
   Il codice valida la risposta; se l'IA inventa un nome, quel nome viene
   scartato, e se non resta nulla di valido si manda comunque l'allarme ma
   coi soli dati certi (niente analisi IA), invece di rischiare di
   pubblicare un'invenzione.

4. Controllo "morbido" sul briefing mattutino: dato che qui i cavalli
   vengono da testo libero (notizie), non c'è una lista chiusa da validare.
   Lo script segnala nei log (senza bloccare l'invio) i nomi in grassetto
   che non compaiono da nessuna parte nei dati di partenza, così te ne
   accorgi quando l'IA sta divagando.
"""

import os
import re
import json
import time
import html as html_lib
from pathlib import Path
from zoneinfo import ZoneInfo

# (import esistenti da mantenere: requests, feedparser, datetime, timedelta, Groq)

FUSO_UK = ZoneInfo("Europe/London")
STATO_FILE = Path("vedetta_state.json")
LIMITE_TELEGRAM = 4096

PATTERN_G1 = re.compile(r'\b(GROUP\s*1\b|GR\.?\s*1\b|GRADE\s*(1|I)\b|G1\b)', re.IGNORECASE)

# Provider IA: Gemini (primario, se configurato) con fallback su Groq
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")  # nuovo secret opzionale su GitHub
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")  # alias sempre aggiornato
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


# ==========================================
# STATO PERSISTENTE (dedup briefing + allarmi)
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
# PROVIDER IA CON FALLBACK (Gemini → Groq)
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
# RICONOSCIMENTO G1 DETERMINISTICO
# ==========================================
def e_gruppo_1(titolo_corsa):
    """Copre le diciture UK/IRE/FRA ('Group 1'), USA ('Grade 1'/'Grade I') e Asia/Oceania ('G1')."""
    return bool(PATTERN_G1.search(str(titolo_corsa).upper()))


# ==========================================
# SANITIZZAZIONE OUTPUT IA PER TELEGRAM
# ==========================================
def sanitizza_html_telegram(testo):
    """Un `&` o `<` residuo non appartenente a un tag consentito manda in errore
    l'intera richiesta a Telegram: il messaggio viene perso, non solo il carattere."""
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
    i nomi in grassetto che non compaiono nei dati di partenza. Non blocca l'invio
    (troppe varianti di nome per farlo in automatico senza falsi positivi) — serve
    a farti notare quando l'IA sta divagando."""
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
# INVIO TELEGRAM ROBUSTO (retry + fallback + split)
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
# PALINSESTO IMMINENTE — STRUTTURATO
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
# GENERAZIONE ALLARME G1 CON VALIDAZIONE ANTI-ALLUCINAZIONE
# ==========================================
def genera_alert_g1(corsa):
    intestazione = (
        "🚨 <b>ALLARME G1 IN PARTENZA</b> 🚨\n"
        f"📍 <b>Ippodromo:</b> {corsa['ippodromo']}\n"
        f"⏰ <b>Partenza:</b> Ore {corsa['ora']}\n"
        f"🏆 <b>Corsa:</b> {corsa['titolo']}\n"
    )

    if not corsa["partenti"]:
        # Niente partenti confermati: niente nomi da inventare, solo i dati certi.
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
# MAIN
# ==========================================
def main():
    stato = carica_stato()

    # ------------------------------------------
    # 1. BRIEFING MATTUTINO — finestra larga + idempotente
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

[IL TUO TURNO]
Scrivi il VERO briefing usando SOLO i [DATI DI INPUT ODIERNI], stessa struttura dell'esempio originale.
Nessun tag <thought>.
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
    # 2. RADAR G1 — filtro deterministico + dedup, gira sempre
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
