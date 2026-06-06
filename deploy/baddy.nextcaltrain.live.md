# Baddy at baddy.nextcaltrain.live (same droplet as nextcaltrain.live)

Baddy runs on Gunicorn (`127.0.0.1:8000`). Nginx on the droplet routes
`baddy.nextcaltrain.live` to that port. **nextcaltrain.live** keeps its existing
Nginx config — add a separate site file for Baddy only.

## 1. DNS

Wherever **nextcaltrain.live** DNS is managed (Cloudflare, Namecheap, etc.):

| Type | Name  | Value              | TTL  |
|------|-------|--------------------|------|
| A    | baddy | YOUR_DROPLET_IP    | Auto |

Same IP as `nextcaltrain.live`. Wait a few minutes, then check:

```bash
dig +short baddy.nextcaltrain.live
# should print your droplet IP
```

**Cloudflare:** orange-cloud (proxy) is OK. HTTPS can be via Cloudflare or Certbot on the server (pick one; Certbot below is simplest if DNS is DNS-only or you use Full SSL).

## 2. Baddy app on the VPS

Confirm Gunicorn is up (paths may differ on your server):

```bash
sudo systemctl status baddy
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000
# expect 200
```

If `baddy` is not running, use the main [README](../README.md) deploy steps and
[`baddy.service`](baddy.service).

## 3. Nginx site for the subdomain

On the **droplet**, from your Baddy repo clone (or copy the file from GitHub):

```bash
sudo cp deploy/nginx-baddy-nextcaltrain.conf /etc/nginx/sites-available/baddy-nextcaltrain
sudo ln -sf /etc/nginx/sites-available/baddy-nextcaltrain /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

Do **not** remove or replace the existing nextcaltrain Nginx site.

Test HTTP:

```bash
curl -s -o /dev/null -w "%{http_code}\n" -H "Host: baddy.nextcaltrain.live" http://127.0.0.1
# expect 200
```

From your phone/laptop: `http://baddy.nextcaltrain.live`

## 4. HTTPS (recommended)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d baddy.nextcaltrain.live
```

Follow prompts. Certbot updates the Nginx config for SSL and auto-renewal.

Then use: **https://baddy.nextcaltrain.live**

If Certbot fails because Cloudflare proxy hides the origin, either:

- Temporarily set the `baddy` record to **DNS only** (grey cloud) during Certbot, or  
- Use Cloudflare’s SSL for that subdomain and skip Certbot on the server.

## 5. GitHub Actions deploy

In the **badminton-coaching** repo → Settings → Secrets:

| Secret            | Value example              |
|-------------------|----------------------------|
| `SERVER_HOST`     | droplet IP                 |
| `SERVER_USER`     | `root`                     |
| `SSH_PRIVATE_KEY` | deploy key PEM             |
| `SERVER_PATH`     | `/root/badminton-coaching` |

Empty `SERVER_PATH` causes deploy `cd` to fail. Use `pwd` inside the repo on the VPS.

## 6. Verify both sites

| URL                         | App        |
|-----------------------------|------------|
| https://nextcaltrain.live   | NextCalTrain |
| https://baddy.nextcaltrain.live | Baddy  |

```bash
journalctl -u baddy -f          # Baddy logs
sudo tail -f /var/log/nginx/error.log
```

## Troubleshooting

| Symptom | Fix |
|--------|-----|
| NXDOMAIN / DNS not found | Wait for DNS; check A record name is `baddy` |
| 502 on subdomain | `sudo systemctl restart baddy`; check `curl 127.0.0.1:8000` |
| nextcaltrain broken | You edited the wrong Nginx file — Baddy uses its own `sites-available` entry |
| Wrong site on subdomain | Check `server_name baddy.nextcaltrain.live` in the Baddy config |
