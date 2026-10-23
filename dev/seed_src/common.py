# Shared building blocks for the seed records (Round Rock, TX).
FIRST_FROST = "Round Rock averages: first frost ~Nov 13-30, last frost ~Feb 21-Mar 19 (sources differ); about 1 freezing night in Nov, 5 in Dec, 8 in Jan, 4 in Feb. Plan for a ~20 F design low (strong El Nino winter forecast: cool, damp, cloudy stretches)."

def moveindoors(by="Nov 1", threshold="50 F"):
    return [
        f"Target: indoors by about {by}, before the first night forecast under {threshold}.",
        "Pre-move: rinse the leaves with a hose, check undersides and stem nodes for spider mites, mealybugs, scale and fungus gnats, treat with insecticidal soap or neem, then quarantine 2 weeks away from other houseplants.",
        "Acclimate in two steps to limit leaf drop: about a week on the covered porch or in the garage, then inside.",
        "Do not repot or fertilize for the move; trim only dead tissue.",
    ]

EMERGENCY = "If a plant cannot be moved on a freeze night: group pots against the house wall under the roof, water the day before, drape frost cloth or a sheet to the ground over a frame (never plastic touching leaves), add a string of incandescent C9 lights under the cover, and remove the cover once it is above 35 F."

def protect_outside(extra=None, cover_at="32 F", bring_in_at="25 F"):
    s = [
        f"Cover at {cover_at} or below (frost cloth/sheet draped to the ground over a frame; frost cloth buys roughly 6-8 F). Bring in or move into the garage at {bring_in_at} or in a multi-day freeze.",
        "Water the day before a freeze (moist soil holds heat) but keep the plant dry the rest of winter; skip watering when it is below 40 F.",
        "Cluster pots against a south/east wall under the roof, away from north wind, and pile mulch or leaves around the pots.",
        "Stop nitrogen fertilizer now; new tender growth freezes first.",
    ]
    return s + (extra or [])

INDOOR_LIGHT = "Indoors: within 3 ft of an east or south window, or under a full-spectrum grow light 12-14 h/day at 6-12 in. Winter sun in Round Rock is only ~4.5-6 hours of real sunshine per day in Dec-Jan, so supplement."
INDOOR_HUMID = "Indoor winter air is typically 20-35% RH; raise it with a humidifier (target 50-60%), grouping plants, or a pebble tray, and keep plants away from heater vents."
