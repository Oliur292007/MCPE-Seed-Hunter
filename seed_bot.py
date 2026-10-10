
import json
import os
import random
import time
import urllib.parse
import urllib.request
from pathlib import Path

API_URL = "https://mineseedfinder.vercel.app/scan/bedrock"
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
HISTORY_FILE = Path("posted_seeds.txt")

# Supported Bedrock structure IDs:
# 5 = Village, 11 = Ruined Portal,
# 14 = Buried Treasure, 24 = Trial Chambers,
# 13 = Ancient City, 7 = Shipwreck.
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
    return set(HISTORY_FILE.read_text().splitlines())


def scan_seed(seed):
    params = urllib.parse.urlencode({
        "seed": seed,
        "x": 0,
        "z": 0,
        "radius": 100,
        "max": 40,
        "types": ",".join(map(str, STRUCTURES)),
    })
    url = f"{API_URL}?{params}"
    request = urllib.request.Request(
        url, headers={"User-Agent": "BedrockSeedHunter/1.0"}
    )

    with urllib.request.urlopen(request, timeout=45) as response:
        data = json.loads(response.read().decode("utf-8"))

    if data.get("error"):
        raise RuntimeError(data["error"])

    return data.get("results", [])


def post_to_discord(message):
    import json
    import os
    import urllib.request
    import urllib.error

    webhook_url = os.environ["DISCORD_WEBHOOK_URL"]

    payload = json.dumps({
        "content": message,
        "allowed_mentions": {"parse": []},
    }).encode("utf-8")

    request = urllib.request.Request(
        webhook_url,
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
        # Print the response body, never the secret URL.
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"Discord webhook HTTP {exc.code}: {detail[:500]}")
        raise RuntimeError(
            f"Discord webhook failed with HTTP {exc.code}"
        ) from None

def main():
    history = read_history()
    best = None

    # Try several candidates and prefer seeds with more nearby
    # supported structures. This does not verify chest loot.
    for _ in range(12):
        seed = str(random.randint(0, 2**32 - 1))

        if seed in history:
            continue

        try:
            results = scan_seed(seed)
        except Exception as exc:
            print(f"Scan failed for {seed}: {exc}")
            time.sleep(2)
            continue

        found_types = {item.get("name", "").lower() for item in results}
        score = len(found_types)

        # Prefer seeds containing both a village and a ruined portal.
        if "village" in found_types:
            score += 2
        if "ruined_portal" in found_types or "ruined portal" in found_types:
            score += 2
        if "buried_treasure" in found_types or "buried treasure" in found_types:
            score += 1

        candidate = (score, seed, results)
        if best is None or candidate[0] > best[0]:
            best = candidate

        if score >= 5:
            break

        time.sleep(1)

    if best is None or not best[2]:
        raise RuntimeError(
            "No usable seed was found. The daily workflow can retry tomorrow."
        )

    _, seed, results = best
    lines = [
        "🌍 **MINECRAFT BEDROCK — SEED OF THE DAY**",
        "",
        f"🎲 **Seed:** `{seed}`",
        "📱 **Edition:** Minecraft PE / Bedrock",
        "📍 **Search area:** Up to 100 chunks from spawn",
        "",
        "**Nearby structure predictions:**",
    ]

    for item in results[:20]:
        name = item.get("name", "").lower()
        label = STRUCTURES.get(
            next(
                (key for key, value in STRUCTURES.items()
                 if value.split(" ", 1)[1].lower() == name),
                -1
            ),
            f"📌 {item.get('name', 'Structure').replace('_', ' ').title()}",
        )
        lines.append(
            f"• {label} — X: `{item['x']}`, Z: `{item['z']}`"
        )

    lines += [
        "",
        "🗺️ [Open Bedrock Seed Map](https://www.chunkbase.com/apps/seed-map)",
        "ℹ️ Coordinates are predictions. Chest loot and exact game-version "
        "compatibility are not verified by this bot.",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "🤖 *Automatically selected by Bedrock Seed Hunter*",
    ]

    post_to_discord("\n".join(lines))
    HISTORY_FILE.write_text("".join(sorted(history | {seed})) + "\n")
    print(f"Posted seed {seed} successfully.")


if __name__ == "__main__":
    main()
