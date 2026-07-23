import os
import requests
import google.generativeai as genai

# 1. Recupera i segreti dalla cassaforte di GitHub
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 2. Configura il modello IA (Gemini 1.5 Flash è velocissimo e gratuito)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

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
    # Qui andrà il tuo codice di scraping di Sporting Life per trovare la corsa del giorno.
    # Per ora simuliamo che la Vedetta abbia trovato un Gran Premio:
    gara_importante_trovata = True
    nome_gara = "King George VI and Queen Elizabeth Stakes"
    orario = "16:40"
    partenti = "1. Auguste Rodin, 2. Rebel's Romance, 3. Luxembourg, 4. Sunway, 5. Dubai Honour"

    if gara_importante_trovata:
        print("Gara G1 trovata! Chiedo all'Oracolo...")
        
        # 3. Interroghiamo Gemini con un prompt da esperto
        prompt = f"""
        Sei un esperto opinionista di ippica (galoppo). Oggi si corre la {nome_gara} alle {orario}.
        I partenti principali sono: {partenti}.
        Scrivi un resoconto di massimo 4 righe, in italiano.
        Evidenzia il favorito, un possibile outsider e usa un tono epico ma tecnico.
        """

        risposta_gemini = model.generate_content(prompt)
        resoconto = risposta_gemini.text

        # 4. Assembliamo la grafica del messaggio per Telegram
        messaggio = (
            f"🚨 <b>ALLERTA GRAN PREMIO!</b> 🚨\n\n"
            f"🏆 <b>Corsa:</b> {nome_gara}\n"
            f"🕒 <b>Orario:</b> {orario}\n"
            f"📺 <b>Diretta:</b> Equ TV / Streaming\n\n"
            f"🏇 <b>I Partenti:</b>\n{partenti}\n\n"
            f"🎙️ <b>L'Opinione dell'Oracolo:</b>\n{resoconto}"
        )

        # 5. Invio del messaggio
        status = manda_messaggio_telegram(messaggio)
        if status == 200:
            print("Bollettino consegnato con successo su Telegram!")
        else:
            print("Errore nell'invio del messaggio.")
    else:
        print("Nessun Gran Premio oggi. La vedetta riposa.")

if __name__ == "__main__":
    main()
