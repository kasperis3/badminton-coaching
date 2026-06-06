# Baddy Mixer

Doubles-first round-robin mixer for badminton coaching sessions. Pair players fairly by score, rotate sit-outs, and track standings round by round.

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
- [`deploy/nginx-baddy.conf`](deploy/nginx-baddy.conf) — Nginx on port 80 (only if nothing else uses it)
- [`deploy/nginx-baddy-port.conf`](deploy/nginx-baddy-port.conf) — Nginx on port 8080 (alongside another app on 80)
- [`deploy/nginx-baddy-nextcaltrain.conf`](deploy/nginx-baddy-nextcaltrain.conf) — **baddy.nextcaltrain.live** on same droplet as nextcaltrain.live
- [`deploy/baddy.nextcaltrain.live.md`](deploy/baddy.nextcaltrain.live.md) — step-by-step DNS + Nginx + HTTPS for that subdomain
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

### Running alongside another app on the same droplet

Your existing app and Baddy can coexist. They are separate processes:

| Piece | Baddy | Your existing app |
|-------|-------|-------------------|
| systemd | `baddy.service` | its own unit (e.g. `myapp.service`) |
| Gunicorn | `127.0.0.1:8000` | usually another port |
| Nginx | extra site or `location` | already configured |

**Do not** follow the step that removes `/etc/nginx/sites-enabled/default` if that would break your current site.

#### 1. Check what is already in use (on the VPS)

```bash
sudo ss -tlnp | grep -E ':80|:8000|:8080'
ls /etc/nginx/sites-enabled/
```

If port **8000** is taken, edit `deploy/baddy.service` to use another port, e.g. `127.0.0.1:8001`, and match it in the nginx `proxy_pass` below.

#### 2. Deploy Baddy only (same as above)

Install code under `/var/www/baddy`, venv, `pip install -r requirements.txt`, enable `baddy.service`. This does not stop your other app.

#### 3. Choose how to reach Baddy

**Option A — Subdomain (best if you have a domain)**  
e.g. `baddy.yourdomain.com` → Gunicorn, while `yourdomain.com` stays your current app.

**Production setup for this project:** [`deploy/baddy.nextcaltrain.live.md`](deploy/baddy.nextcaltrain.live.md)  
(DNS `baddy` → droplet IP, Nginx config [`deploy/nginx-baddy-nextcaltrain.conf`](deploy/nginx-baddy-nextcaltrain.conf), Certbot for HTTPS.)

```nginx
# /etc/nginx/sites-available/baddy
server {
    listen 80;
    server_name baddy.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Add a DNS **A record** for `baddy` pointing at the droplet IP. Open on your phone: `http://baddy.yourdomain.com`

**Option B — Separate port (simplest with IP only)**  
Leave your current app on port 80. Use [`deploy/nginx-baddy-port.conf`](deploy/nginx-baddy-port.conf):

```bash
sudo cp deploy/nginx-baddy-port.conf /etc/nginx/sites-available/baddy
sudo ln -sf /etc/nginx/sites-available/baddy /etc/nginx/sites-enabled/baddy
sudo ufw allow 8080/tcp
sudo nginx -t && sudo systemctl reload nginx
```

Open on your phone: `http://<VPS_PUBLIC_IP>:8080`  
Also allow **TCP 8080** in the DigitalOcean cloud firewall if you use it.

**Option C — Path on the same site** (`yourdomain.com/baddy/`)  
Possible but needs Flask `SCRIPT_NAME` / URL prefix changes. Prefer A or B unless you specifically need one hostname.

#### 4. Verify both apps

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000   # Baddy direct
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080  # if using port 8080
# your existing app URL as you use it today
```

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

**Manual** (replace the path with your clone, e.g. `/root/badminton-coaching`):

```bash
cd /root/badminton-coaching   # or /var/www/baddy
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart baddy
```

**CI deploy (GitHub Actions)** — [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) runs the full test suite on every push and PR; **deploy to the VPS only runs on push to `main` after tests pass**.

Add these repository secrets under **Settings → Secrets and variables → Actions**:

| Secret | Purpose |
|--------|---------|
| `SERVER_HOST` | VPS IP or hostname |
| `SERVER_USER` | SSH user (e.g. `root`) |
| `SSH_PRIVATE_KEY` | Deploy private key (full PEM) |
| `SERVER_PATH` | Absolute path to the repo clone (e.g. `/root/badminton-coaching`) — must contain `venv/` |

Use an **absolute** path for `SERVER_PATH` (not `~`). The systemd unit [`deploy/baddy.service`](deploy/baddy.service) must use the same directory for `WorkingDirectory` and `ExecStart` (edit paths before `systemctl enable` if you deploy under home instead of `/var/www/baddy`).

If `SERVER_USER` is not root, allow passwordless restart:

```bash
# /etc/sudoers.d/baddy-deploy
deploy ALL=(ALL) NOPASSWD: /bin/systemctl restart baddy
```

## Testing

Install dev dependencies and run tests:

```bash
pip install -r requirements-dev.txt
pytest                  # full suite
pytest -m smoke         # fast sanity check
pytest -m regression    # manual pairings, swap, score rules
```

GitHub Actions runs smoke tests then the full suite on every push and pull request. Deploy to the VPS is blocked if tests fail.

## CLI (optional)

```bash
python3 badminton_mixer.py
```

## How it works

### Competition mode

At setup, choose **Doubles** (default) or **Singles**:

- **Doubles** — courts are doubles when possible; if 2 players remain after doubles courts, one **singles** match uses a court. **0 or 1 sit-out** per round as needed.
- **Singles** — every court is one singles match (2 players). Odd player counts use **1 sit-out**; even counts use all players.

### Pairing phases

- **Rounds 1–3** — active players are shuffled; pairings are exploratory (matchup history still avoids repeats when possible).
- **Round 4+** — players are grouped by **score** (ranked tiers / similar-strength singles pairs).

### Scoring and rotation

- **Game to** — choose **7** (default), **11**, **15**, or **21** at session start. Match scores are 0 to that cap.
- **Sit-out points** — half the game cap + 1 (7→4, 11→6, 15→8, 21→11).
- In doubles mode, each player plays **singles at most twice** per session; lower scorers preferred for singles rotation.
- Each player **sits out at most once** per session (when a sit-out is needed).
- **Matchup memory**: partners and opponents tracked to avoid repeats when possible.
- Sit-outs rotate fairly when needed (fewest previous sit-outs first).

### Session history and resume (web)

- **Auto-save** — in-progress sessions are stored in the browser (`localStorage`) on each round page.
- **Resume** — after a refresh, use **Resume session** on the setup page to continue.
- **Past sessions** — when you **End session**, standings are archived locally (up to ~20 entries, newest first).
- History and resume are **per browser/device only** — not synced across phones or coaches.

Server-side Flask sessions still expire after about **7 days**; localStorage is independent and survives until you clear site data.

### Manual pairings and sit-out swap (web)

- **Round 1** — at setup, choose **Auto** or **Manual** pairings. Manual opens a court builder where you assign every player once.
- **Later rounds** — after each round, **Next round (auto)** or **Set pairings manually**.
- **Edit pairings** — on the round page before scores are saved, change assignments for the current round.
- **Swap with sit-out** — when one player sits out, each court has a **Swap** control to exchange one player on that court with the sit-out (bye points and games played update automatically).

Matchup history is recorded when scores are saved, so swaps and manual edits are reflected in what actually gets played.
