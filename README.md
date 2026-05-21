# Baddy Mixer

Singles round-robin mixer for badminton coaching sessions. Pair players fairly by score, rotate sit-outs, and track standings round by round.

## Web app (local / same Wi‑Fi)

1. Install dependencies:

```bash
pip3 install -r requirements.txt
```

2. Start the server:

```bash
python3 app.py
```

3. Open on your Mac: `http://127.0.0.1:3333`

4. On your phone (same Wi‑Fi as your laptop): use the URL printed in the terminal, e.g. `http://192.168.1.42:3333`

Keep the terminal running while you coach. Your phone and laptop must be on the same network.

## Deploy to VPS (production)

Use Gunicorn behind Nginx so you can open `http://YOUR_VPS_IP` from your phone anywhere (no laptop required).

Config templates live in [`deploy/`](deploy/):
- [`deploy/baddy.service`](deploy/baddy.service) — systemd unit
- [`deploy/nginx-baddy.conf`](deploy/nginx-baddy.conf) — Nginx site
- [`deploy/.env.example`](deploy/.env.example) — `SECRET_KEY` reminder

### 1. VPS initial setup (Ubuntu)

SSH into the VPS:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip nginx git ufw
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw enable
```

Also allow inbound **TCP 80** in your VPS provider’s firewall / security group if it has one.

### 2. Deploy application code

```bash
sudo mkdir -p /var/www/baddy
sudo chown $USER:$USER /var/www/baddy
cd /var/www/baddy
git clone <your-repo-url> .
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Or copy from your Mac with `rsync` / `scp` if the repo is not on Git yet.

### 3. Secret key and systemd

Generate a secret:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Edit [`deploy/baddy.service`](deploy/baddy.service): set `User`, `Group`, and `Environment=SECRET_KEY=...` to your values, then install:

```bash
sudo cp deploy/baddy.service /etc/systemd/system/baddy.service
sudo systemctl daemon-reload
sudo systemctl enable baddy
sudo systemctl start baddy
sudo systemctl status baddy
```

Do **not** run `python3 app.py` on the VPS — that dev server is for local use only.

### 4. Nginx reverse proxy

```bash
sudo cp deploy/nginx-baddy.conf /etc/nginx/sites-available/baddy
sudo ln -sf /etc/nginx/sites-available/baddy /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

Open on your phone: `http://<VPS_PUBLIC_IP>`

### 5. Verify

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000   # expect 200
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1       # expect 200
```

Logs: `journalctl -u baddy -f` and `/var/log/nginx/error.log`

**Troubleshooting**

| Symptom | Fix |
|--------|-----|
| Connection refused from phone | Open port 80 in provider firewall + `ufw` |
| 502 Bad Gateway | `sudo systemctl restart baddy` |
| Sessions reset between visits | Keep `SECRET_KEY` stable in systemd |

### 6. Update after code changes

```bash
cd /var/www/baddy
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart baddy
```

## CLI (optional)

```bash
python3 badminton_mixer.py
```

## How it works

- Each court runs one **singles** match (2 players).
- Up to `courts × 2` players play per round; extras sit out (+6 points).
- Round 1 pairings are shuffled; later rounds match by current standings.
- Sit-outs rotate fairly (fewest previous sit-outs first).
