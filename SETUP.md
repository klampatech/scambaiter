# Setup

## 1. Get Telegram API credentials
Go to [my.telegram.org](https://my.telegram.org), log in, create an app, and copy your `api_id` and `api_hash` into `config.py`.

## 2. Get your own Telegram user ID
You can get this by messaging `@userinfobot` on Telegram. Put the ID in `YOUR_USER_ID` in `config.py`.

## 3. Configure LLM
Set `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` in `config.py` to point at your remote server.

## 4. Install and authenticate
```bash
cd ~/scambaiter
pip install -r requirements.txt
python main.py   # First run: prompts for phone number + Telegram auth code
                 # Creates scambaiter_session.session — back this file up!
```

## 5. Install as a service
```bash
sudo cp scambaiter.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now scambaiter
sudo journalctl -u scambaiter -f   # Watch live logs
```
