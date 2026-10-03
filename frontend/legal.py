"""
Privacy / Terms / Disclaimer / Features text shown in the footer pop-ups.

NOTE: these are plain-language templates describing what Triavia actually does. They are not legal
advice — have them reviewed before using the app with real users or real data.
"""
UPDATED = "2 October 2026"
CONTACT = "sami757007@gmail.com"
_C = CONTACT.replace("@", "\u200b@")   # zero-width space: no auto-link, so the pop-up opens at the top

FEATURES = """
**Triage**
- Four urgency levels: Non-Urgent, Semi-Urgent, Urgent, Resuscitation
- Recommended action and target waiting time for each level
- 28 ready-made example patients (critical → minor), plus a 🎲 random patient generator

**Explainable**
- "Why this result?" chart — which vital signs pushed the result up or down
- Derived indicators: shock index, mean arterial pressure, pulse pressure, fever / hypoxia / tachycardia flags
- Clinical **safety net**: red-flag rules can raise — never lower — the AI result

**Insights**
- Analytics: accuracy, F1, ROC-AUC, per-class report, confusion matrix, feature importance
- Private assessment history with one-click delete

**Platform**
- Sign in with Google, mobile number (SMS code) or as a guest
- REST API with interactive docs (Swagger) for integrations
- In-app feedback form that reaches the author directly
- Open source (MIT), SQLite or PostgreSQL, Docker-ready
"""

PRIVACY = f"""
*Last updated: {UPDATED}*

**What we store**
- **Your account:** Google sign-in → your name and email · mobile sign-in → your phone number · guest → a random ID only.
- **Your assessments:** age, main complaint, vital signs entered, the result and a timestamp.
- **Feedback you send:** your message, an optional rating and an optional contact detail, so the author can read and answer it.
- We do **not** ask for patient names, ID numbers, addresses or medical records. Please don't enter any.

**What we don't do**
- No advertising, no tracking cookies, no selling or sharing of your data. Streamlit's usage statistics are switched off.

**How long we keep it**
- **Guest** accounts and their data are deleted automatically after 24 hours.
- Other accounts are kept until you delete them. Use **History → Danger zone** to erase your assessments or your whole account at any time.
- SMS codes are stored only as hashes and expire after 5 minutes.

**Who processes data for us**
- Hosting and database providers that run the app, Google (if you choose Google sign-in) and an SMS provider (if real SMS is enabled).

**Security**
- Encrypted connections (HTTPS) when deployed, signed session tokens, rate limiting, and every user can only see their own history.

**Your choices**
- Delete your data in the app, or email **{_C}** for any privacy request.

*This is a demonstration project — treat it accordingly and never enter real patient data.*
"""

TERMS = f"""
*Last updated: {UPDATED}*

1. **Educational use only.** Triavia is a demonstration and portfolio project. It is not a medical device and must not be used to make or delay real clinical decisions.
2. **No medical advice.** Results are model outputs trained on **synthetic** data. They are not a diagnosis or treatment recommendation.
3. **Your responsibilities.** Do not enter real patient information. Don't misuse the service: no attacks, scraping, or attempts to access other people's data.
4. **No warranty.** The service is provided "as is" without guarantees of accuracy, availability or fitness for a particular purpose. To the extent permitted by law, the author is not liable for any loss arising from its use.
5. **Availability & changes.** The service may be slow, unavailable or changed at any time, and accounts or data may be removed.
6. **Open source.** The code is released under the MIT licence.
7. **Contact.** Questions about these terms: **{_C}**.
"""

DISCLAIMER = f"""
**⚠️ This tool is not a substitute for professional medical care.**

- Triavia is **not** a medical device and has **not** been clinically validated.
- The model is trained on **synthetic** (computer-generated) data, so its accuracy figures do not describe real-world performance.
- Clinical safety rules can escalate a result, but they are a simple safeguard — not a replacement for trained staff, protocols or judgement.
- **In an emergency, contact your local emergency number immediately** (for example 112 in India, 911 in the US, 999 in the UK) or go to the nearest emergency department.

Questions? **{_C}**
"""
