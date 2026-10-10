# 🌍 Minecraft Bedrock Seed Hunter

Automatically finds and posts a fresh Minecraft Bedrock/PE seed to Discord every hour.

## 🔄 How It Works
```

┌─────────────────────────────────────────────────────────────────────┐
│                    GITHUB ACTIONS (every hour at :17)               │
│                                                                     │
│   ⏰  cron: "17 * * * *"     ──or──     🖱️  manual dispatch         │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │  Spin up Ubuntu VM     │
                    │  (fresh, ephemeral)    │
                    └───────────┬────────────┘
                                │
                                ▼
        ┌───────────────────────────────────────────────┐
        │  1. Checkout repo                             │
        │  2. Setup Python 3.12                         │
        │  3. Inject secrets:                           │
        │       • DISCORD_WEBHOOK_URL                   │
        │       • MINECRAFT_ROLE_ID                     │
        └───────────────────┬───────────────────────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │  python seed_bot.py │
                 └──────────┬──────────┘
                            │
                            ▼
              ┌───────────────────────────┐
              │  Load posted_seeds.txt    │
              │  (skip already-posted)    │
              └─────────────┬─────────────┘
                            │
                            ▼
        ╔═══════════════════════════════════════════════╗
        ║   LOOP: up to 30 random candidates            ║
        ║                                               ║
        ║   🎲 random.randint(0, 2**32 - 1)             ║
        ║              │                                ║
        ║              ▼                                ║
        ║   🌐 Call Mineseedfinder API                  ║
        ║      /scan/bedrock?seed=...&radius=100        ║
        ║              │                                ║
        ║              ▼                                ║
        ║   📊 Score structures:                        ║
        ║        • Base = unique types found            ║
        ║        • Village       +2                     ║
        ║        • Ruined Portal +2                     ║
        ║        • Buried Treas. +1                     ║
        ║              │                                ║
        ║              ▼                                ║
        ║   🏆 Keep best  ──►  score ≥ 5 ? EXIT EARLY   ║
        ╚═══════════════════════════════════════════════╝
                            │
                            ▼
              ┌───────────────────────────┐
              │  Format Discord message   │
              │  🌍 Seed of the Hour      │
              │  🎲 seed, 📱 edition      │
              │  📍 structure list w/xyz  │
              └─────────────┬─────────────┘
                            │
                            ▼
              ┌───────────────────────────┐
              │  POST to Discord webhook  │
              │  with <@&ROLE_ID> ping    │
              └─────────────┬─────────────┘
                            │
                     ┌──────┴──────┐
                     │             │
                  ✅ OK         ❌ FAIL
                     │             │
                     ▼             ▼
        ┌─────────────────┐   ┌──────────────────┐
        │ Append seed to  │   │ Job fails red ❌ │
        │ posted_seeds.txt│   │ Seed NOT saved   │
        └────────┬────────┘   │ (retried later)  │
                 │            └──────────────────┘
                 ▼
        ┌───────────────────────────┐
        │  git add + commit + push  │
        │  history file back to repo│
        └─────────────┬─────────────┘
                      │
                      ▼
              ┌───────────────┐
              │  VM shuts down│
              │  See you :17  │
              └───────────────┘
```

## 🧩 Components

| Component | Role |
|---|---|
| `seed_bot.py` | Finds seeds and posts to Discord |
| `posted_seeds.txt` | Deduplication history (committed to repo) |
| `.github/workflows/*.yml` | Scheduler + runner |
| Discord Webhook | Delivery channel |
| Mineseedfinder API | Structure lookup |

## ⚠️ Failure Modes

| Problem | Effect |
|---|---|
| API down | 30 attempts fail → job raises error |
| Webhook revoked | Posts fail, history never updates |
| Branch protection on `main` | `git push` fails → seed re-posted every hour |
| Missing secrets | Python crashes on `os.environ[...]` |

## 🔑 Required Secrets

Set these in **Settings → Secrets and variables → Actions**:

- `DISCORD_WEBHOOK_URL`
- `MINECRAFT_ROLE_ID`# MCPE-Seed-Hunter
