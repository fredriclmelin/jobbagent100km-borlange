
import json
import os
import smtplib
import ssl
from pathlib import Path
from email.message import EmailMessage

MATCHES = Path("matches.json")
HISTORY = Path("sent_ads.json")

def main():
    username = os.environ["MAIL_USERNAME"]
    password = os.environ["MAIL_APP_PASSWORD"]

    matches = json.loads(MATCHES.read_text(encoding="utf-8"))

    if HISTORY.exists():
        sent = set(json.loads(HISTORY.read_text(encoding="utf-8")))
    else:
        sent = set()

    new_ads = [
        ad for ad in matches
        if str(ad.get("id", "")).strip()
        and str(ad["id"]) not in sent
        and ad.get("url")
    ]

    message = EmailMessage()
    message["Subject"] = (
        f"Jobbagent Borlänge – {len(new_ads)} nya jobb"
    )
    message["From"] = username
    message["To"] = username

    if new_ads:
        lines = [
            f"Jobbagenten hittade {len(new_ads)} nya matchande annonser.",
            "",
        ]

        for ad in new_ads:
            lines.extend([
                f'{ad.get("score", 0)} poäng – {ad.get("title", "Okänd titel")}',
                f'Arbetsgivare: {ad.get("employer", "Okänd")}',
                f'Plats: {ad.get("location", "Ej angiven")}',
                f'Publicerad: {ad.get("published", "Ej angivet")}',
                f'Länk: {ad["url"]}',
                "",
            ])

        lines.append(
            "Obs: Matchningspoängen är en automatisk "
            "sökordsbedömning och behöver kontrolleras."
        )
        message.set_content("\n".join(lines))
    else:
        message.set_content(
            "Ingen ny annons passerade matchningsfiltret "
            "sedan föregående lyckade rapport."
        )

    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(
        "smtp.gmail.com", 465, context=context, timeout=30
    ) as server:
        server.login(username, password)
        server.send_message(message)

    # Spara historiken först efter att mejlet skickats.
    sent.update(str(ad["id"]) for ad in new_ads)
    HISTORY.write_text(
        json.dumps(sorted(sent), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Mejl skickat. Nya annonser: {len(new_ads)}")

if __name__ == "__main__":
    main()
