# WhatsApp Cloud API setup
Verificatie Business Manager kan weken duren.
Webhook GET hub.mode=subscribe + hub.verify_token, echo hub.challenge.
POST X-Hub-Signature-256 HMAC-SHA256 met App Secret.
Send: POST https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}/messages
Subscribe field: messages.
Testnummer: max 5 ontvangers tot App Live.
