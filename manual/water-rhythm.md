# How often you water (prototype)

Part of the Plant record manual. The README in the folder above has how to start, stop, update and back up the app, and the list of every manual page.

## How often you water (prototype)

The watering reminder guesses how often to check each plant from its soil moisture range and the weather. Your care log knows how often you really water. **Today → How often you water** puts the two side by side.

- **Watered sooner than the reminder**, **Watered later than the reminder**, **About right** and **Not enough logged yet** (folded). Each plant says "Watered about every 5 days since Aug 22", what the reminder says, and how many times it was found still moist.
- **About every** is the middle gap between waterings in the last 120 days, so one odd gap does not move it. A gap of more than 45 days is left out as a time nothing was logged. For a plant whose Location is Outdoors, a day with 0.25 in of rain or more counts as a watering, as it does for the reminder. A pattern needs at least 4 waterings.
- **Remind me every N days** changes the plant's **Check for water every (days)** so the reminder comes round at about that gap in weather like today's (indoors, the app stretches the gap by half, so a 3-day reminder is a setting of 2). The message has **Undo**, and the change is in the plant's history and the Audit log.
- **On a plant's page**, inside the Watering box: how often it was watered, the recent gaps, the same button, and **Let the app work out the gap** when the box has a number in it.
- People who can only view see the comparison but not the buttons.
- **Since November 15, 2026:** for an indoor plant, the number you pick is the number you get: choosing a gap here sets the reminder to exactly that many days, with no stretch for being indoors. Each list has **Make all of these match**, which asks first, sets every reminder in the list from that plant's own waterings, and can be undone in one press.
