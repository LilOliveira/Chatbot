# Chatbot

## Promoções Mercado Livre + Amazon (Telegram)

Este projeto coleta 50 promoções (25 de cada plataforma) e envia os links para um bot do Telegram.

### Requisitos

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Uso

1. Envie uma mensagem para o bot no Telegram para que ele tenha um `chat_id` registrado.
2. Execute o script:

```bash
python promo_bot.py
```

Opcionalmente, defina as variáveis de ambiente:

```bash
export TELEGRAM_BOT_TOKEN="seu_token"
export TELEGRAM_CHAT_ID="seu_chat_id"
```

Se `TELEGRAM_CHAT_ID` não for informado, o script tenta obter o último chat_id via `getUpdates`.

### Observações

- Mercado Livre utiliza a API pública de busca para identificar itens com preço promocional.
- Amazon é coletada via HTML da página de busca; caso não haja promoções detectadas, tente novamente.
