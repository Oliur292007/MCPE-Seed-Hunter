
import json
import os
import random
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

API_URL = "https://mineseedfinder.vercel.app/scan/bedrock"
HISTORY_FILE = Path("posted_seeds.txt")

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
ROLE_ID = os.environ["MINECRAFT_ROLE_ID"]

STRUCTURES = {
    5: "🏘️ Village",
    11: "🌀 Ruined Portal",
    14: "💎 Buried Treasure",
    24: "⚔️ Trial Chambers",
    13: "🏚️ Ancient City",
    7: "🚢 Shipwreck",
}


def read_history():
    if not HISTORY_FILE.exists():
        return set()
    return {
        line.strip()
        for line in HISTORY_FILE.read_text().splitlines()
        if line.strip()
    }


def scan_seed(seed):
    params = urllib.parse.urlencode({
        "seed": seed,
        "x": 0,
        "z": 0,
        "radius": 100,
        "max": 40,
        "types": ",".join(map(str, STRUCTURES)),
    })

    request = urllib.request.Request(
        f"{API_URL}?{params}",
        headers={"User-Agent": "BedrockSeedHunter/1.0"},
    )

    with urllib.request.urlopen(request, timeout=45) as response:
        data = json.loads(response.read().decode("utf-8"))

    if data.get("error"):
        raise RuntimeError(data["error"])

    return data.get("results", [])


def post_to_discord(message):
    payload = json.dumps({
        "content": f"<@&{ROLE_ID}>\n{message}",
        "allowed_mentions": {
            "parse": [],
            "roles": [ROLE_ID],
        },
    }).encode("utf-8")

    request = urllib.request.Request(
        WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status not in (200, 204):
                raise RuntimeError(
                    f"Discord returned HTTP {response.status}"
                )
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"Discord HTTP {exc.code}: {detail[:300]}")
        raise RuntimeError(
            f"Discord posting failed: HTTP {exc.code}"
        ) from None


def main():
    history = read_history()
    best = None

    # Try unique candidates; never intentionally select a posted seed.
    for _ in range(30):
        seed = str(random.randint(0, 2**32 - 1))

        if seed in history:
            continue

        try:
            results = scan_seed(seed)
        except Exception as exc:
            print(f"Scan failed for candidate: {exc}")
            time.sleep(2)
            continue

        if not results:
            continue

        found_types = {
            item.get("name", "").lower().replace(" ", "_")
            for item in results
        }

        score = len(found_types)
        if "village" in found_types:
            score += 2
        if "ruined_portal" in found_types:
            score += 2
        if "buried_treasure" in found_types:
            score += 1

        candidate = (score, seed, results)
        if best is None or score > best[0]:
            best = candidate

        if score >= 5:
            break

        time.sleep(1)

    if best is None:
        raise RuntimeError(
            "No usable unposted seed found. Will retry at the next schedule."
        )

    _, seed, results = best

    lines = [
        "🌍 **MINECRAFT BEDROCK — SEED OF THE DAY**",
        "",
        f"🎲 **Seed:** `{seed}`",
        "📱 **Edition:** Minecraft PE / Bedrock",
        "📍 **Search area:** API-reported structures near spawn",
        "",
        "**Nearby structure predictions:**",
    ]

    for item in results[:20]:
        name = item.get("name", "Structure").lower().replace(" ", "_")
        label = next(
            (
                label for label in STRUCTURES.values()
                if label.split(" ", 1)[1].lower().replace(" ", "_") == name
            ),
            f"📌 {name.replace('_', ' ').title()}",
        )

        if "x" in item and "z" in item:
            lines.append(
                f"• {label} — X: `{item['x']}`, Z: `{item['z']}`"
            )

    lines += [
        "",
        "🗺️ [Open Bedrock Seed Map](https://www.chunkbase.com/apps/seed-map)",
        "ℹ️ Structure predictions and chest loot have not been independently verified.",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "🤖 *Automatically selected by Bedrock Seed Hunter*",
    ]

    # Post first; save history only after the post succeeds.
    post_to_discord("\n".join(lines))

    history.add(seed)
    HISTORY_FILE.write_text("\n".join(sorted(history)) + "\n")
    print(f"Posted new seed {seed} successfully.")


if __name__ == "__main__":
    main()
