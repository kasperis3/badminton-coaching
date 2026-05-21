# Baddy Mixer

Singles round-robin mixer for badminton coaching sessions. Pair players fairly by score, rotate sit-outs, and track standings round by round.

## Web app (phone-friendly)

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

## CLI (optional)

```bash
python3 badminton_mixer.py
```

## How it works

- Each court runs one **singles** match (2 players).
- Up to `courts × 2` players play per round; extras sit out (+6 points).
- Round 1 pairings are shuffled; later rounds match by current standings.
- Sit-outs rotate fairly (fewest previous sit-outs first).
# badminton-coaching
