# Prototype: your own reminders

## What it does and why
The app already reminds you about watering, feeding, cold nights, turning the pots and repotting, because it can work those out. What it cannot work out is everything else you think of while standing next to a plant: "check this cutting for roots in two weeks", "spray again for mealybugs in 5 days", "this one looked droopy, look again on Friday", "buy potting mix". Today those go on paper or in your head. This lets you write them into Plant record, so they turn up on Today on the right day, next to everything else.

The ideas list had nothing left that was not done or in progress, so this one is suggested by Claude.

- **A new page, Reminders** (Today → Reminders, after Repotting). It has:
  - one line saying how many are due (and how many of those are late), with **Add a reminder**;
  - **Due now**: today's and any late ones, each with **Done**, **A week later** and **Change**;
  - **Coming up**: the ones set for later;
  - **Done lately**: the last 30 days, with **Not done yet** to put one back.
- **Add a reminder** opens a window with:
  - **What to do** (a short sentence, up to 200 letters);
  - **For which plant** (from the Reminders page or Today: any plant at this home, or **Not for a particular plant**; from a plant's page it is for that plant);
  - **When**: Tomorrow, In 3 days, In a week (chosen to start with), In 2 weeks, In a month, In 3 months, each with its date, or **On this date**;
  - **Repeat**: does not repeat, or every week, 2 weeks, month, 2 months, 3 months, 6 months or year.
- **Repeating** reminders come back that long after the day you press **Done**, not after the day they were due. So "Spray again every week" done two days late still waits a full week before the next spray.
- **On Today:** a **Reminders** section and a **Reminders (N)** jump button, only when something is due. A reminder stays on Today from its day until you press Done; once its day has passed it says **Late:** and how many days, in words (not only in red).
- **On a plant's page:** a line under the care buttons, "Reminders: none set." or "Reminders: 2 set.", with **Add a reminder** for that plant and the plant's reminders listed under it.
- **Change** lets you edit the words, move the date, change the repeat, or **Remove it** (after asking).
- Every reminder added, moved, done, put back or removed goes in the **Audit log**, against the plant it is for, so a plant's reminders also show in its Timeline. People who can only view see the reminders but not the buttons. Reminders follow the home you are looking at: a plant's reminder goes with the plant, and one for no plant stays with the home it was written at.
- Search finds the page ("Reminders").

## How it looks
Laptop, the Reminders page (one late reminder for a plant, one for no plant coming up tomorrow):

![The Reminders page](reminders/laptop-page.png)

The Add a reminder window:

![Add a reminder](reminders/laptop-window.png)

On Today:

![Reminders on Today](reminders/laptop-today.png)

On a plant's page, under the care buttons:

![Reminders on a plant's page](reminders/laptop-plant.png)

Phone, light, the page and a plant's page:

![Phone: the Reminders page](reminders/phone-page.png) ![Phone: a plant's page](reminders/phone-plant.png)

Phone, dark mode, largest text: Today and the window (nothing scrolls sideways):

![Phone, dark, large text: Today](reminders/phone-dark-big-today.png) ![Phone, dark, large text: the window](reminders/phone-dark-big-window.png)

## How to try it
- Windows cmd.exe: `set "DATA_DIR=dev\tmp\data" && python dev\test\mock_server.py`
- PowerShell: `$env:DATA_DIR='dev\tmp\data'; python dev\test\mock_server.py`
- bash: `DATA_DIR=dev/tmp/data python3 dev/test/mock_server.py`

Then open http://127.0.0.1:8080/#/reminders. The focused check is `python3 dev/test/reminders_check.py` (or `python3 dev/test/run_checks.py reminders`), and the unit tests are in `dev/test/unit/test_reminders.py`.

## What it changes in the database
- **One new table, `plant_reminders`**, created the first time the app needs it (`CREATE TABLE IF NOT EXISTS`). Nothing else in the database changes, no existing table gets a column, and nothing happens to your plants when you upgrade. If you never add a reminder, the table stays empty.
- Done and removed reminders are kept in the table (marked, not deleted), so **Not done yet** and the Audit log work. The one exception: "Not done yet" on a repeating reminder deletes the next one it made, as long as nobody has changed it.
- New Audit log entries, under "Feeding, watering and care".
- Backups include it like any other table. It is not yet in **Download all data (JSON)** (see the questions).

## Open questions for Ethan
Answered on November 15, 2026 and built:
- **A phone notification (1).** At 8 in the morning at each home, one message with the reminders due that day or still waiting ("Reminder for today at Round Rock: Look for roots (Pothos)"). "Your own reminders" is a kind each person can turn off under Notifications. Nothing is sent on a day with none.
- **Done with no connection (2).** Done waits in the outbox and is sent when the server answers again, dated the day it was pressed; the reminder leaves Today and the Reminders page at once. The lists are the ones the device saved when Today or Reminders was last open while connected ("Keep a copy on this device" does not fetch them ahead). Tomorrow, A week later, Change and Add still need a connection.
- **The calendar file and the download (5).** Each open reminder is an all-day entry on its day in the calendar file (a late one on today), with the same alert time as feeding days. The JSON download has a `reminders` list.
1. **Phone notifications.** Should a reminder also send a notification to your phone on its morning (like the cold-night ones), or is Today enough? It would be a new choice under Notifications.
2. **Offline.** Right now a reminder can only be added or ticked off while the app can reach your PC. Should Done work offline from the garden, like Watered does, and be sent later?
3. **Plant-sitter sheet.** Answered November 15: no, reminders are yours and stay off the sitter sheet.
4. Answered November 15: both. A reminder has **Tomorrow** and **A week later**.
5. **Download all data (JSON)** and the calendar file: should reminders go in them too?
6. Answered November 15: near the top. The Today block is before Water (after a cold night and sensor alerts).

Reply on this pull request with changes, or say "merge" when you are happy.
