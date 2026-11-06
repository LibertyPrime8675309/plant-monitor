# Plant database

A web app for your outdoor plants: one page per plant with photos, names, temperature / humidity / sunlight ranges, winter care, ID confidence, health notes, and a full change history. It runs in Docker on your PC and is opened in a browser. Phones on your Wi-Fi can use it too.

77 plants and 108 photos are pre-loaded from the pictures you sent. Claude wrote the first version of every page (the history shows "Claude (initial analysis from photos)" for P-001 to P-040, "Claude (batch 2, from photos)" for P-041 to P-066 and "Claude (batch 6, from photos)" for P-067 to P-077).

## Start it

You need Docker Desktop running. Open a terminal in this folder (the one containing `docker-compose.yml`).

Windows (cmd.exe):

```
docker compose up -d --build
```

Windows (PowerShell):

```
docker compose up -d --build
```

macOS / Linux (bash):

```
docker compose up -d --build
```

Then open <http://localhost:8080>.

The first build takes a few minutes. The first start loads the plants into `data\plants.db` and copies the photos into `data\photos`.

## Stop, restart, update

Windows (cmd.exe):

```
docker compose stop
docker compose start
docker compose up -d --build
docker compose logs --tail 50
```

Windows (PowerShell) and macOS / Linux (bash): the same commands.

`up -d --build` rebuilds after you change anything in `app\`. Your data is not touched.

### Upgrading from an earlier version

Replace the old folder's contents with this one, but **keep your existing `data\` folder** (it holds your database and photos). Then, in the folder:

Windows (cmd.exe):

```
docker compose up -d --build
```

Windows (PowerShell):

```
docker compose up -d --build
```

macOS / Linux (bash):

```
docker compose up -d --build
```

On the first start the app adds anything new (from the first version: 26 plants, P-041 to P-066, and their photos; from 1.6.0: 11 plants, P-067 to P-077, and new photos for three existing pages; from 1.2.0: the new environment fields filled in on every plant page, see below) and each upgrade batch runs once. Version 1.2.0 also adds a new table for weather and sensor readings; the app creates it by itself. Version 1.3.0 adds a database index (the first start after upgrading takes a few seconds longer while it is built, more if you loaded many years of history) and two tables for daily weather and the update log. If you had already loaded years of history, press **Load history** once more with the same start date to fill in the extra measurements and the daily summaries; it only fetches what is missing. Anything you edited on P-040 stays as you left it: if the upgrade wants to change a field you already changed, it leaves that field alone and records a note in the change log. Back up `data\` first if you want a safety copy (see "Your data and backups").

### The updater (from 1.7.0)

The updater lives in the folder that holds `plant-database` (for example `C:\Users\Ethan\Documents\Claude\Plants`): `Update Plant Database.cmd` and `update-plant-database.ps1`.

From 1.12.2, release zips and photo packs are kept in a folder of their own beside it, **`versions_plant-database`**, so they don't clutter the Plants folder. Save new zips there. If you save one straight into the Plants folder instead, the updater moves it there for you. That's also how your older zips got moved.

Double-click **Update Plant Database.cmd**. It:

1. moves any `plant-database-….zip` files from the Plants folder into `versions_plant-database`. It finds the newest `plant-database-vX.Y.Z-YYYYMMDD-HHMM.zip` there and says which version is installed and which is running. If that version is already installed and running, it stops and changes nothing.
2. asks "Update to X? Type Y" (type `Y`, press Enter).
3. makes sure Docker Desktop is running, and starts it if not.
4. makes a backup through the app (it appears on the Backups page as "Before update"). If the running app is older than 1.7.0, it stops the app and copies `data\plants.db` into `backups\` instead.
5. unzips the release and copies it over the `plant-database` folder. **`data` and `backups` are never touched.**
6. adds plant photos from any photo packs the release needs (see below).
7. runs `docker compose up -d --build` and waits until the new version answers.
8. lists the Docker images that older versions left behind (the app's and, from 1.18.0, the picture checker's, about 2 GB each) and offers to delete them to free disk space. With `-RemoveOldImage` it deletes them without asking.

#### Photo packs (from 1.8.0)

From 1.8.0, plant photos travel separately from the app, in **photo packs**. The release zip itself stays well under a megabyte.

- Each photo pack holds the photos from one plant update, for example `plant-database-photos-batch9.zip`.
- A pack never changes once it is made.
- A release only comes with the packs for the plant updates that are new in it.

Save any photo packs in `versions_plant-database` too (or in the Plants folder; the updater moves them). The updater adds the photos your `plant-database` folder does not have yet. Packs you already have are skipped.

If a release needs a pack that is not in the folder, the updater lists it and stops before changing anything. If photos arrive after you have updated (because you used `-Force`), run the updater again; it adds them even though the version is already up to date. You can delete a pack once it has been added.

Everything it does is written to `update-log.txt` in the Plants folder. Each new release carries the newest updater in `plant-database\tools`, and the updater copies it into the Plants folder, so it keeps itself current.

To run it from a terminal in the Plants folder instead:

Windows (cmd.exe):

```
"Update Plant Database.cmd"
powershell -NoProfile -ExecutionPolicy Bypass -File update-plant-database.ps1 -Yes
```

Windows (PowerShell):

```
.\update-plant-database.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\update-plant-database.ps1 -Yes -RemoveOldImage
```

macOS / Linux (bash), with PowerShell 7 (`pwsh`) installed:

```
pwsh -File ./update-plant-database.ps1
```

Options: `-Yes` (do not ask), `-Force` (re-apply the newest zip anyway), `-RemoveOldImage`, `-SkipBackup` (not recommended), `-Password <text>` (only if you set `PLANTDB_PASSWORD`), `-Url http://localhost:8080`.

## Version

The `VERSION` file holds this package's version, and `CHANGELOG.md` lists what changed in each one. Keep each zip you receive (the file name carries the version and build time) as your archive; they all collect in `versions_plant-database`.

### Which version is running?

- **In the app**: the version shows next to "Plant record" at the top of every page (for example `v1.6.2`), and at the top of the **Display** settings.
- **In Docker Desktop**: open **Containers**; the **Image** column for `plant-database` shows `plant-database:1.6.2`. The **Images** list shows one entry per version you have built.
- **From a terminal** (in the project folder):

Windows (cmd.exe):

```
docker ps --filter name=plant-database --format "{{.Image}}"
curl http://localhost:8080/api/version
```

Windows (PowerShell):

```
docker ps --filter name=plant-database --format "{{.Image}}"
Invoke-RestMethod http://localhost:8080/api/version
```

macOS / Linux (bash):

```
docker ps --filter name=plant-database --format '{{.Image}}'
curl http://localhost:8080/api/version
```

If the version in the app is older than the newest zip in your folder, that update has not been applied yet.

Each update leaves the previous version's images behind until the updater deletes them (it asks at the end). To see them yourself, and to delete one by its name and version:

Windows (cmd.exe):

```
docker image ls --filter "reference=plant-database*"
docker image rm plant-database:1.18.1 plant-database-vision:1.18.1
```

Windows (PowerShell) and bash: the same commands. Never delete the images for the version that is running.

## Using the app away from home (from 1.12.0)

From version 1.12.0 the app has its own Tailscale device, called **plants**. You open it at an address like `https://plants.your-tailnet.ts.net` from any phone or computer that has Tailscale on, at home or away. It's encrypted all the way, with a real certificate, so browsers no longer say "Not secure". Nothing on your router is opened, and you can share just the app (not your whole computer) with someone else.

What changed:
- **Your home network can't reach the app any more.** Before 1.12.0, anyone on the house Wi-Fi could open `http://<your PC>:8080` and change things. Now only this computer can open `http://localhost:8080`, which the updater and backups use. Everyone else, including you on your phone, uses the `https://plants…ts.net` address with Tailscale on.
- **Your old Tailscale address for the desktop (port 8080) stops working too.** Use the new address instead.
- **People who come in through Tailscale are signed in by Tailscale.** The app knows who they are without a password. It names them in the audit log, and they can only do what you allow (see below).

### One-time setup

1. Update to 1.12.0 with the updater as usual.
2. Run **Set Up Remote Access**: double-click `Set Up Remote Access.cmd` in the `plant-database\tools` folder, or from the Plants folder run:
   - Windows (cmd.exe): `"plant-database\tools\Set Up Remote Access.cmd"`
   - Windows (PowerShell): `powershell -ExecutionPolicy Bypass -File .\plant-database\tools\setup-remote-access.ps1`
   - bash: `pwsh -File ./plant-database/tools/setup-remote-access.ps1`

   It opens Tailscale's sign-in page. Sign in with your usual Tailscale account. If it says HTTPS is off, it opens the DNS page of the Tailscale admin console: turn on **MagicDNS** if it is off, press **Enable HTTPS**, and go back to the script. It then makes you the owner, prints the app's address, and offers to point the QR codes on labels at it. You can run it again any time to check everything; it changes nothing that is already right.
3. In the [Tailscale admin console](https://login.tailscale.com/admin/machines), open **Machines**, then **plants**, then the **…** menu, and choose **Disable key expiry**. Otherwise Tailscale asks you to sign the device in again after a few months.
4. On your phone: install the Tailscale app, sign in with the same account and switch it on. Open the `https://plants…ts.net` address and add it to your home screen.

### Sharing it with someone (for example your girlfriend)

1. In the Tailscale admin console, go to **Machines**, then **plants**, then the **…** menu, then **Share**. Copy the invite link (or invite by email) and send it.
2. She installs Tailscale on her phone or computer and signs in with her own account (Google, Microsoft, Apple and others work). Then she opens the invite link and accepts it.
3. With Tailscale on, she opens the same `https://plants…ts.net` address. She can reach the plant app and nothing else of yours: not your computer, its files or games.
4. The first time she opens it, she appears in the app's people list as **Can view only**. Press your name at the top right to see the list, and change her to **Can edit** if she should make changes.
5. To stop sharing: **Machines**, then **plants**, then **Share**, and remove her there. Then press **Remove** next to her in the app's list.

### Who can do what

- **Can view only**: sees everything (plants, photos, weather, the audit log) and changes nothing. A "View only" note sits at the top of each page, and buttons that would change something are hidden.
- **Can edit**: also changes plant pages, care, feedings, photos, answers and the photo list.
- **Owner**: also backups, settings (label address, weather places, the sensor token) and the people list. The setup script makes you the owner; if it couldn't, the first person to open the app through Tailscale is. There is always at least one owner.
- On this computer (`http://localhost:8080`) everything stays open, as before, and your name is typed in.

The app itself checks every request, so hiding a button is only a convenience: a change someone isn't allowed to make is refused even if they try it another way. The audit log shows each change under the Tailscale name of the person who made it. You can change the name shown for you in the same window.

### Security, in short

- **Encrypted all the way.** Traffic travels inside Tailscale's encryption, and the app adds HTTPS with a real certificate on top. Tailscale's servers never see your plant data.
- **No open router ports.** Nothing is opened to the internet (Tailscale Funnel is switched off in `tailscale\config\serve.json`), and the router needs no changes.
- **Only signed-in people get in.** That means your devices and people you have shared the plants device with, each with the role you chose.
- **A tighter container:**
  - Its program files are read-only, and it has almost no Linux privileges and can't gain any.
  - It runs as an ordinary user when Docker allows that, and otherwise as root inside its container, as before (see "Which user the app runs as" below).
  - Each update rebuilds it on a freshly downloaded base image and fetches the newest Tailscale container, so security fixes keep arriving.
- **Private files stay private.** The Tailscale sign-in is in `tailscale\state`. It never goes into a release or a backup zip, so keep that folder to yourself.

### Which user the app runs as (from 1.12.1)

Each time it starts, the app checks whether an ordinary user (called `plants`) may write to the `data` and `backups` folders.
- **If it may,** the app runs as that user, with no special privileges at all. This is the safer way, and the usual one on a new install.
- **If it may not,** the app runs as root inside its container, the way every version before 1.12.0 did. Nothing needs doing. This is normal on Windows for folders an older version wrote to: Docker Desktop doesn't let the new user write there and can't hand those folders over.

Either way the program files stay read-only and only a few privileges are allowed. The first line of the app's log says which way it runs, and so does the **Debug** window (for the owner). To see the log line:
- Windows (cmd.exe): `docker logs plant-database 2>&1 | findstr /C:"Plant record runs"`
- Windows (PowerShell): `docker logs plant-database 2>&1 | Select-String 'Plant record runs'`
- bash: `docker logs plant-database 2>&1 | grep 'Plant record runs'`

Version 1.12.0 needed a `docker-compose.override.yml` file for the second case. The updater removes that file, because the app now decides by itself. To always run as root, put the line `PLANTDB_RUN_AS=root` in the `.env` file and run `docker compose up -d`.

### Opening it to your home network again (less safe)

If you need the old `http://<your PC>:8080` address on your home Wi-Fi (for example for a device that can't run Tailscale), put a line in a file named `.env` next to `docker-compose.yml`, then restart. Anyone on the Wi-Fi can then change things, unless you also set `PLANTDB_PASSWORD` in `docker-compose.yml`. From the `plant-database` folder:

- Windows (cmd.exe): `(echo PLANTDB_BIND=0.0.0.0)>>.env` then `docker compose up -d`
- Windows (PowerShell): `Add-Content .env 'PLANTDB_BIND=0.0.0.0'; docker compose up -d`
- bash: `echo 'PLANTDB_BIND=0.0.0.0' >> .env && docker compose up -d`

Then find your PC's address on the Wi-Fi:
- Windows (cmd.exe): `ipconfig` (look for "IPv4 Address", for example `192.168.1.20`)
- Windows (PowerShell): `Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '169.*' -and $_.IPAddress -ne '127.0.0.1' } | Select-Object InterfaceAlias, IPAddress`
- bash: `hostname -I`

If it doesn't load from the phone, Windows Firewall may be blocking port 8080. Allow Docker Desktop on private networks when Windows asks, or add a rule:
- Windows (cmd.exe, run as administrator): `netsh advfirewall firewall add rule name="Plant database" dir=in action=allow protocol=TCP localport=8080 profile=private`
- Windows (PowerShell, run as administrator): `New-NetFirewallRule -DisplayName "Plant database" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8080 -Profile Private`
- bash (Linux with ufw): `sudo ufw allow 8080/tcp`

Remove the line from `.env` and run `docker compose up -d` to close it again.

### If something doesn't work

- **The address doesn't open:** check that Tailscale is on for that phone or computer. Run Set Up Remote Access again: it says what is missing.
- **"Open Plant record from a device that is signed in to Tailscale as a person":** the device uses a Tailscale tag or isn't signed in as a person. Sign it in with a personal account.
- **The updater says port 8080 is busy** ("ports are not available" or "Only one usage of each socket address"): close any browser tabs that have Plant record open, at `http://localhost:8080` or the old address. They can hold on to the port while the app restarts. The updater says so, waits and tries again for about a minute. If the port is still busy after that, it names the program that holds it and moves the app to a free port such as `http://localhost:8090`, saved as `PLANTDB_PORT` in the `.env` file. The Tailscale address doesn't change. To move it back later, close the program holding port 8080, delete the `PLANTDB_PORT` line from `.env`, and from the `plant-database` folder run:
  - Windows (cmd.exe): `docker compose up -d`
  - Windows (PowerShell): `docker compose up -d`
  - bash: `docker compose up -d`
- **If the app does not start after updating:** in Docker Desktop, open **Containers**, then **plant-database**, then **Logs**.
  - A line starting with `PLANTDB_NOT_WRITABLE` means the app can't write to its data folder, even as root. Check that the `plant-database` folder isn't read-only (in File Explorer, right-click it, then **Properties**), then run the updater again.
  - If that doesn't help, send the log to Claude. Your plants and photos aren't changed.

## Display settings and low vision

Press the **Display** button (bottom right of every page; it stays on screen) to change how everything looks. The **Debug** button beside it is described under "Audit log" below. Changes apply at once and are remembered in that browser (each computer or phone keeps its own).

- **Text and button size**: Standard, Comfortable (the new default, a little bigger than before), Large, Larger, Largest. Buttons, bars, charts and spacing scale together.
- **Spacing**: Normal or Roomy (more space between lines, letters and words).
- **Contrast**: Normal or High (black and white with heavier outlines).
- **Colours**: match your device, light or dark.
- **Plant pages**: photos and details side by side, or one column.
- **Line length** (from 1.26.0): **Use the full width** (the usual choice: paragraphs and lists run across the whole page, so more fits on screen) or **Shorter lines** (about 70 letters per line, which some people find easier to follow).

On a plant page in side-by-side view, the photos (left) and details (right) each scroll on their own: put the pointer over the half you want to move and scroll. A "Switch to one column" button at the top of the page does the same as the Display setting. With very large text or a narrow window the page switches to one column automatically. The row of section buttons (Now, Temperature, Humidity, Light, Water and soil, ...) jumps straight to a section; in side-by-side view it steps aside while the On this page menu is open, because the menu lists the same sections. All parts of the page can also be reached with the Tab key.

On a computer (from 1.26.1) the menu bar at the top uses the whole width of the window: the name and version on the left, Online, Location and Editing on the right, and the page links in one row underneath, spread across the window. If the window is wide enough, everything sits on one line.

On a phone the menu bar at the top scrolls away with the page (scroll back to the top to reach it), and every page fits the width of the screen at every text size. From 1.26.0:
- The list of pages folds behind one **Pages** button, which names the page you're on (for example "Pages: Groups"). Press it to show every page; choosing one, or pressing Escape, folds the list again.
- **Sections**, **Debug** and **Display** share one bar along the bottom of the screen. With the largest text there isn't room for all three in one row, so Sections takes the top row and Debug and Display share the second.
- On a computer with large text (or a small window such as a tablet held sideways), the page links fold behind the same **Pages** button once they would take more than two rows, or the top bar more than a fifth of the window. If the top bar is still that tall, it scrolls away with the page, as on a phone.
- Tables too wide for the screen become one box per row: the row's name (a day, a plant, a backup) at the top, then each value next to its column's name, two or more to a line when they fit. The long table on the Weather page still scrolls sideways.
- The same happens on a tablet or a small window whenever the text is large enough that the page switches to one column.

### Pop-up windows (from 1.25.0)

- **Display settings** is divided into parts: Text and colours, Page layout, Reading aloud, Photos and touch, and Keyboard.
  - On a computer, the parts are listed on the left. Press one to jump to it; the part you're looking at is highlighted.
  - On a phone, or an upright tablet, the window covers the screen and the parts are a row of buttons above the settings.
  - **Done** and **Reset to defaults** are at the top and stay there while you scroll. Reset to defaults keeps the window open.
- **Every pop-up window:**
  - uses more of the screen;
  - keeps its buttons (Save, Cancel, Done…) in view at the bottom while you scroll;
  - closes when you click or tap outside it, the same as Cancel or Done (a drag that only ends outside doesn't close it). Escape still closes it too.
- Confirmations ("Remove this photo?") stay small. On a phone, windows rise from the bottom of the screen and use its full width.

### Read aloud and keyboard shortcuts (from 1.8.0)

Every section has a **Read aloud** button. Your browser reads that section in its own voice, the section gets a dashed outline while it is read, and a big **Stop reading** button stays at the bottom of the screen. **Read this page aloud**, under the page title, reads the whole page. In **Display** you can hide the buttons, pick the **Reading speed** (slower to fastest) and the **Voice**, with **Try this voice**. In Microsoft Edge the "Natural" voices sound the most human.

Keyboard shortcuts work on every page, except while you are typing in a box. **Display** can turn them off.

| Key | What it does |
|---|---|
| **R** | Read this page aloud |
| **Escape** | Stop reading |
| **[** and **]** | Previous and next plant |
| **E** | Edit this plant |
| **/** | Search plants |
| **H** | Go to the Plants page |
| **M** | Open or fold the section menu |
| **L** | Choose the location for the weather |
| **?** | List the shortcuts |

### Section menu ("On this page")

Every page has a menu down the side listing its sections (for example on the Weather page: Tracked history, All logged weather data, Location and updates). Choose one to jump straight to it; the section you are reading is highlighted. On plant pages it scrolls the details half, like the section buttons. From 1.27.3 the section you choose stays highlighted until you scroll yourself (even a short last section that cannot reach the top of the window), and it gets a thick outline for a couple of seconds so you can find it.

- **Hide** folds the menu away; the **Sections** button at the edge of the screen brings it back.
- **Move to the right / Move to the left** swaps its side.
- The same choices, plus **Page width: Use the full width of the window** (more room for charts and tables on a wide screen), are in **Display**. They are remembered on that computer.
- On phones, narrow windows and very large text the menu starts folded, the Sections button sits at the bottom left, and the menu closes after you choose a section.
- On plant pages (from 1.14.1) it lists every part of the page: **Photos**, **Name and details** (the card at the top), and each section below. The row of section buttons has the same sections with shorter names. Both are made from the page itself, so new sections join them by themselves.

## Photos on the Plants page, and the main photo (from 1.20.0)

- **On the Plants page,** a plant with more than one photo has **‹** and **›** buttons on its photo, with "2 of 5" between them. They step through all its photos without opening the plant. On a phone or tablet you can also swipe left or right on the photo. With the keyboard, move to a photo button with Tab, then use the Left and Right arrow keys. Click anywhere else on the card to open the plant, as before.
- **The main photo** is the one the Plants page shows first, and the one on care cards and in plant link previews. On a plant page, the photo panel says "★ This is the main photo" under it, and its thumbnail is marked **★ Main**. To change it, pick another photo and press **Make this the main photo**.

- **Wide photos** (from 1.21.0): a photo taken sideways used to be cut down to a tall slice of its middle and stretched, so it looked blurry. Now the Plants page shows wide photos whole, with a plain band above and below, and every card photo is sharper. To change this, open **Display** and choose **Photos on the Plants page**: show wide photos whole (the usual choice), always fill the card, or always show the whole photo.

## Plants page filters

The filter row on the Plants page narrows the list. Every filter is remembered in this browser, and **Clear filters** resets them.

- **Search:** name, code, location or plant type.
- **Health** and **winter plan** (the coloured buttons above the filters).
- **Location (from 1.16.2):** outdoors, covered porch, indoors, or garage or shed.
- **Group (from 1.16.0):** only the plants in one group.
- **Show (from 1.16.2):** active plants only (the usual), active and archived together, or archived only. Archived plants say "Archived" on their card. Archiving hides a plant without deleting anything; **Move back to the main list** on its page undoes it.
- **More filters (from 1.17.0),** in the fold-out under the filter row:
  - **Light needs:** low light, bright indirect light, some direct sun, or full sun, from each plant's daily light range.
  - **Pets:** safe for pets (only where the ASPCA lists the plant as non-toxic), not known to be toxic, mildly toxic, or toxic. This comes from the plant's "Safety for pets" field (Edit, "About this plant").
  - **Winter here:** hardy here, not hardy here, or annual / no zone set. It compares the plant's coldest zone with yours.
  - **Care today:** water or feeding due, the same as the Today page.
  - **Grow light:** under a grow light spot, or not.
  - **Leaf type** and **pot size.**
  - **Photos:** no photo yet, or the newest photo is over a month old.
- **Sort by:** code, health, ID confidence, recently updated, name, or group.
- **Needs something from you** and **ID confidence under 70%.**

## Previous and next plant (from 1.7.5)

Every plant page has **Previous Plant** and **Next Plant** buttons, each showing the name and code of the plant it leads to. On a wide screen they sit in the margins either side of the page; on smaller screens and phones they sit at the top of the page.

**Swipe (from 1.14.1).** On a phone or tablet, swipe left anywhere on a plant page for the next plant, or right for the previous one. While you swipe, a label names the plant that is coming; once it says "Let go to open it", lifting your finger opens it. Start the swipe away from the very edge of the screen, because your phone uses edge swipes for Back. Swipes that start on a menu, a form field or the photo are left alone, and so is scrolling up and down. To turn it off, open **Display** and set **Swipe between plants** to Off.

They follow the Plants page filters and sort order. The fold-out **Filters for Previous / Next** panel at the top of each plant page has the same filters (search, winter plan, health, location, group, show, sort, "needs something from you", ID under 70%) and shows where the plant falls in the list. Changing a filter in either place changes it in both, and this browser remembers it.

## Location: outdoors or indoors (from 1.7.0)

The label at the top of every plant page now starts with **Location**: Outdoors, Covered porch, Indoors, or Garage or shed. It is a menu. Click it (or Tab to it and use the arrow keys) and pick another place, and the change is saved straight away and recorded in the page history. The old free-text "Location" field, for example "Covered porch pallet shelf", is now called **Spot**.

On the **Winter plan** page each plant in "Plant by plant" has a **Moved indoors** button. Pressing it sets the plant's Location to Indoors and takes it off those lists. It is also left out of the frost warnings in "The next 7 days". Plants already inside are listed under **Already inside**, each with a **Moved back outside** button. After upgrading to 1.7.0, every plant started as Outdoors; 1.8.0 set the plants whose Spot is on the covered porch to Covered porch, unless you had already changed them.

## Today page, watering and care (from 1.8.0)

The **Today** page (the page the app opens on, from 1.34.0) lists what to do today, most urgent first:

- **Water:** plants due or overdue for a check, each with **Watered** and **Still moist**, and **Watered all** for a whole round. "Check tomorrow" lists the next day's plants. "No watering logged yet" has one button, **I watered all today**, to start the reminders for all of them.
- **Feed:** plants due for fertilizer today, with **Log feeding** (the same schedule as the Fertilizer page).
- **Needed from you:** the open requests, with links to answer them.

Every plant page has **quick care buttons** under its label, big enough to use on a phone in the garden after scanning the plant's label: **Watered today**, **Checked: still moist**, **Log feeding**, **Add a photo** (opens the phone's camera) and **Log other care** (repotted, pruned, treated for pests, or a note, with a date). The line above them says when the plant was last watered and when to check it next. The plant's **Water and soil** section explains the reminder and has its **care log**, with a **Remove** button on each entry.

How the reminders work:

1. The starting gap comes from how dry the plant likes to be: 14 days for plants that dry out completely (cacti, aloes), 10 for plants that dry out between waterings, 7 when the top of the mix should dry, 5 for evenly moist, and 4 for constantly moist (ferns, calatheas).
2. Hot weather (highs of 85°F or more) shortens it; cool weather and being indoors lengthen it.
3. Rain of 0.25 in or more on one day counts as a watering, but only for plants whose Location is Outdoors (not the covered porch).
4. **Checked: still moist** moves the next check a third of the gap later.
5. To set the gap yourself, fill in **Check for water every (days)** on the plant's Edit page.

**Once a day** (from 1.21.0): after you press **Watered today** on a plant page, the button changes to **✓ Watered today** and is switched off until tomorrow, so a second press can't log it twice. Undo, or Remove in the care log, switches it back on. The app never logs two waterings for the same plant on the same day.

**Water all** (from 1.21.0): on the Plants page, **Water all … shown** marks every plant the filters show as watered today, after asking. Plants already watered today are skipped, and the message has **Undo**. For example, choose Location: Covered porch, then **Water all**.

## Frost alert and cold-night checklist (from 1.8.0)

When a night in the 7-day forecast would hurt a plant that is outside, a banner at the top of the page says how cold it will get and on which night, how many plants could die, would be damaged or are close calls, and when to act ("before dark today"). It is called "Frost warning" at 36°F or below and "Cold warning" above that, because the tropical plants are hurt at 50 to 60°F. **Hide until the forecast changes** hides it until the forecast gets colder or more plants are at risk. Plant pages show their own **Frost risk** note instead of the banner.

**Open the cold-night checklist** (on the banner, or on the Winter plan page) shows the next 7 nights, then each plant once, most urgent first, in three groups: **Bring inside**, **Cover or move to shelter**, and **Close calls** (within 3°F of the damage point). Each plant has **Moved indoors** (sets its Location to Indoors, so it leaves every list and warning) and **Covered for tonight** (ticks it off for its next cold night only, since covers go back on each night), with **Undo**. Each group also has a button for all its plants, which asks first. Tips for a cold night are at the bottom.

Plants set to Indoors or Garage or shed are never counted. Plants on the Covered porch are.

## Plant timeline (from 1.8.0)

Each plant page has a **Timeline** section, just above Page history (also in the On this page menu):

- how the plant is doing over time, for example "Health: Critical until Oct 22, Poor now (getting better)"
- **Compare two photos:** the oldest and newest photo side by side. Pick others with the **Left photo** and **Right photo** menus, or press **Compare** under any photo in the list.
- **Everything that has happened**, newest first and grouped by day: photos, changes to the page (the important ones in words, such as "Health rating: from Fair to Poor"), feeding and care, answered requests, and when the page was created. Tick boxes under **Show** hide any kind.

## Getting plants ready to come inside (from 1.9.0)

Outdoor plants often carry ants, spider mites, mealybugs and other pests. Each plant page has a **Getting ready to come inside** section, after Winter in Round Rock, that helps keep them out of the house.

1. Under **About this plant**, check the **Leaf type** and choose the **Pot size**. Claude filled in the leaf type for every plant; change it if it is wrong.
2. Inspect the plant (the first method explains how) and tick any **Pests you found**. Leave them all unticked if you found nothing.
3. The ten methods are listed in the order to do them, each rated for this plant: **Best**, **Good**, **Use with care**, **Not needed** or **Not for this plant**, with the reason. Open **How to do it** for the steps. Methods that are not needed or not suitable are folded away under one line.
4. Press **Done today** after each one. It goes into the care log, the timeline and "Copy my answers for Claude". **Undo the last one** takes it back. To record a step done on an earlier day, use **Log other care**.
5. If a spray needs a second round, the **Today** page reminds you 5 days later.
6. When the plant comes inside, change its Location to Indoors (or press **Moved indoors**). The section then says until when to keep it apart from your other houseplants: 3 weeks, or 2 weeks after its last treatment if you found pests.

The page **Getting plants ready to come inside** (button on the Winter plan page, and links on the cold-night checklist and the Today page) lists every plant coming in, grouped as Not started, In progress, Ready to come inside, and Inside. Each one shows its next step and best methods, and **Open its plan** goes straight to that plant's section. The page also has the steps for all ten methods and advice on keeping plants apart.

Pots are never cleaned with bleach: use hot soapy water, a brush and a day in the sun, or for extra cleaning 10 minutes in 3% hydrogen peroxide (never mixed with vinegar or other cleaners), then rinse. A new pot works too.

## Back outside in spring (from 1.15.0)

In spring, open **Winter plan** and press **Which can go back outside?** (or go to the **Back outside** page). It checks every plant whose Location is Indoors, or Garage or shed, against its own temperatures and the 7-day forecast:

- **Ready:** every night in the forecast is at or above the low it likes.
- **Safe, but cool:** no night comes within 3°F of its damage point, but some nights are cooler than it likes.
- **Too early:** this week is fine, but in most years colder nights still come after this date.
- **Not yet:** a night in the forecast is too cold. The page says which night and how cold.

Each label is a word in a box, not just a colour. With 3 or more years of weather history, each plant also gets the date the nights usually stay warm enough. **Moved to the porch** and **Moved outside** change its Location, like the Moved indoors button. From late autumn to winter the page says plants should stay in until spring, and in spring the Today page says how many can go back out.

## Photo check (from 1.8.0)

When you add photos, each one is checked in your browser first. Photos that look fine are added straight away. If any look **blurry**, **too dark**, **too bright (washed out)** or are a **very small picture**, a box shows them with what to do, and these buttons: **Take a new one** (opens the camera or file picker again), **Add only the good ones**, **Add it anyway** and **Cancel**. Nothing extra is sent anywhere.

## What Claude needs from you

When Claude needs something to finish a plant's page (a check, a question, a photo or ID details), it is listed at the top of that plant's page under **Needed from you**, with **Answer** and **Mark done** buttons. Answers are kept on the page and in the change log. To send them to Claude, use **Copy my answers for Claude** (below). On the **Plants** page, **Show plants that need something from you** filters to just those plants; plants whose identification is under 70% sure are included, with what would help. Things to photograph that are not in the database yet are on the **Photos** page.

### Copy my answers for Claude (from 1.8.0)

**Copy my answers for Claude** is on the Plants page (it says how many answers are new, for example "(2 new)") and in "Needed from you" on each plant page. It puts everything you have done since you last copied into one message: your answers first, then changes to plant pages, photos added, feeding and care, and the "Still to photograph" list. Press **Copy message**, then paste it into your chat with Claude (Ctrl+V). **Save as a text file** puts the same message in your Downloads folder instead.

Next time it starts from where the last copy ended, so nothing is sent twice. **What to include** can also be "The last 7 days", "The last 30 days" or "Everything", and **Also list what is still open** adds the open requests and photos, which helps when you start a new chat. Photos themselves can't go in the message, so attach any you want Claude to look at.

## Current conditions and the "Now" marker

Each plant page has a **Current conditions** box. Press **Set current conditions** (or **Change**) and choose where the numbers come from:

- **I will type them in**: temperature (F), humidity (%), and light as PAR or lux. The dialog lists rough light values to use if you have no meter (full midday sun 1,500 to 2,000 PAR, open shade 200 to 600, under a porch roof 100 to 400, bright window 100 to 300, lamp-lit room 5 to 30).
- **My sensor**: the newest reading your sensor sent (see below).
- **Online weather**: the latest hour from Open-Meteo for your location. This is open sky, so plants under a roof or in shade get less light than it says.

The setting is shared by all plant pages. Every gauge (temperature, humidity, light, soil moisture, soil temperature, soil pH) then shows a labelled **Now** marker. When a value is outside the plant's range, the page gets a **Getting this plant back in range** section with numbered steps for that plant and that situation (for example how to protect it from a cold night, or how to raise humidity). Readings that are old are flagged as out of date.

## Location (from 1.11.0)

Nothing in the app is tied to Round Rock any more. The **Location** button at the top right of every page (on a phone, at the top of the page) shows the place in use, for example "Location: Round Rock, TX". Press it, or press **L**, to choose another.

- **Everything weather-related follows it:**
  - the frost banner and the cold-night checklist ("Frost warning for Baraboo: …")
  - current conditions and the "Now" marker on plant pages
  - the marks on the temperature and humidity strips: the coldest night of a usual winter there, and its usual coldest-month night, worked out from that place's own weather history
  - "Winter in …" on plant pages
  - the Winter plan, the Today page's watering reminders and rain
  - the Weather page
  - what "today" means
- **This browser remembers the choice.** Each computer or phone keeps its own, so someone else using the app somewhere else can pick their own place without changing yours.
- **Add a place** in the same window: type a town or city, press **Search** (or Enter) and choose **Add and use** next to the right one. Its last 3 months of weather and its forecast arrive within a minute.
- **Make … the home place for everyone**: the home place is what a computer or phone uses until it chooses its own location, and what the hourly updates and backups use.
- The Winter plan's written notes, sources and expected-weather table are for Round Rock, so they show only when the place in use is Round Rock. For other places the expected columns come from that place's own weather history, once it has 3 years or more (use **Load history** on the Weather page).

## Weather and sensors

The **Weather** page replaces the fixed weather table. It has:

- a 7-day forecast for your location, with freezing nights marked and a count (and list) of plants that would be damaged at each night's low;
- charts of temperature, humidity and light over the last day, 3, 7, 14, 30 or 90 days, or a year, from online weather and from your sensor, with a table of the numbers under each chart and an option to overlay one plant's comfortable range;
- an Expected-and-tracked table for October to March: the 30-year averages next to what was actually recorded;
- sensor connection details and location settings.

The Winter plan page uses the same data for its forecast and its season table.

Online weather comes from [Open-Meteo](https://open-meteo.com/) (free, no account). The app fetches it every hour, loads the last 3 months the first time, and keeps everything in your database, so the history keeps growing. The computer running Docker needs internet access for this. If an update fails the Weather page shows the reason. Location is Round Rock, TX by default; change it under **Location and updates**. To bring in older history (for example last winter), use "Load older weather history from this date". Light is estimated from solar radiation (about 2.1 PAR per W/m2).

### More than one place

The Weather page can track as many places as you like, for example Round Rock, TX and Baraboo, WI. Each place keeps its own hourly readings, daily summaries, forecast, Load history and update log.

- **Add a place**: Weather page, **Places** section. Type a town or city, press **Search**, and pick the right one from the list (it shows the state or country, coordinates, time zone and elevation). You can also type the name, latitude, longitude and time zone yourself. A new place fetches its last 3 months and forecast straight away, then updates every hour like the others.
- **Location**: the menu at the top of the Weather page is the same choice as the **Location** button at the top of every page (see "Location" below). It picks which place the page shows: forecast, charts, the table of logged data, the season table, Load history and the update log.
- **Compare places**: in Tracked history, open **Choose what to chart and compare places** and tick other places. Every chart then has one line per place (up to 6 places). For daily, weekly or monthly steps there are also charts of each place's lowest and highest temperature.
- **Home place**: the place a computer or phone uses until it chooses its own location, and the one the hourly updates and backups use. Round Rock is home after upgrading; **Make home** changes it.
- **Stop hourly updates** keeps a place and its weather but stops fetching. **Remove** deletes the place and all its weather (it asks first). The home place cannot be removed.
- **Update every place now** updates them one after another; the progress box names the place it is on.

Upgrading keeps every reading you already have: they become Round Rock's.

### Everything Open-Meteo offers is now collected

Version 1.3.0 asks Open-Meteo for every measurement it publishes for your location, not just temperature, humidity and sunlight: feels-like temperature, dew point, wet-bulb temperature, air dryness (VPD), temperature at 80, 120 and 180 m, rain, showers, snowfall, snow depth, chance of precipitation, weather code, cloud cover (total, low, middle, high), visibility, day or night, sunshine, solar radiation (total, direct, diffuse, direct normal, top of atmosphere), UV index, wind speed, direction and gusts (at several heights), air pressure, water loss from plants and soil (evapotranspiration), soil temperature and soil moisture at several depths, and upper-air values such as CAPE. There are also daily summaries (highest, lowest and average of most of these, plus sunrise, sunset, day length, rain and snow totals and growing degree days). Units are Fahrenheit, mph and inches.

Not every measurement exists for every period. If Open-Meteo does not offer one for old dates, the app notes it (the update log lists them), skips it, and tries again in two weeks.

**Disk use.** Every measurement every hour is about 10 MB per year. So that going back to 1940 does not make the database huge, the app keeps *every* hourly measurement only for the most recent years (3 by default; change "Years of full hourly detail to keep" under Location and updates), keeps temperature, humidity and plant light hourly for all older years, and keeps the full set as daily summaries for all years. Everything from now on is kept in full.

### Tracked history charts

Under **Tracked history** on the Weather page:

- **Period**: the last 24 hours up to the last 10 years, **Everything logged** (back to 1940 if you loaded it), or **Pick dates** for any From and To date.
- **Choose what to chart**: tick Temperature, Humidity and Light, and as many other measurements as you like (any hourly measurement, plus daily summary values such as UV index highest or growing degree days). Each group has Tick all and Untick all, and two buttons tick every hourly measurement or every daily value. Charting everything over all years can take several seconds. Measurements with the same unit share a chart, up to three per chart. Your choices are remembered on that computer.
- **Use the dates and columns from the table below**: copies the table's From and To dates and its shown columns into the charts.
- The time step grows with the period so long charts stay readable: one point per hour up to 10 days, per day up to 3 years, per week up to 15 years, per month beyond that. Rain, snow, sunshine and water loss are added up over each step; gusts and UV use the highest value; everything else is averaged. For years older than your "full hourly detail" setting, extra measurements come from the daily summaries, and the page says so.

**Section titles stay in view.** On wide screens the title of the section you are scrolling through stays at the top of the screen. **Chart settings stay in view.** The settings bar (period, dates, source, plant range, charts per row, Go to chart, Choose what to chart) sticks to the top of the screen while you scroll through the charts, so you can change it while looking at any chart. **Hide chart settings** folds it to one line (it starts folded on narrow windows and with very large text). **Charts per row** shows 1, 2 or 3 charts side by side, and **Go to chart** jumps to any chart by name.

### The table of everything logged

**All logged weather data** (Weather page) is a table of what is stored: hourly weather, daily summaries, or your own sensor readings. Pick dates and order, set how many rows load at a time (any number from 10 to 1,000; remembered on that computer), jump straight to a page by typing its number and pressing Go (or First page / Last page), choose which columns to show (your choice is remembered on that computer), and download everything for the chosen dates as a spreadsheet (CSV, all columns). "Also chart" under Tracked history draws any one extra measurement.

### Update log

Under **Location and updates** the page says when the last **Load history** ran and what it brought in (dates covered, hourly readings and daily summaries, and which measurements Open-Meteo did not offer), and the same for the last automatic update. "Every update that has run" is the full log, including the hourly automatic ones. Readings collected before this version are shown as "Before logging began".

**Load history** now runs in the background. While it runs, the Weather page shows a progress bar with the percentage, which year it is fetching, how many readings it has saved so far, how long it has been running, an estimate of the time left, and when it last heard from Open-Meteo (so you can tell it is still going; it also says when it is pausing for Open-Meteo's per-minute limit). A small box at the bottom left of every page shows the percentage and time left until it finishes. It takes about half a minute per year of history; 1940 to now takes roughly 40 minutes. It keeps going if you leave the page or close the browser. Pressing it again skips whatever is already stored, so you can stop and resume. If the connection to Open-Meteo drops part-way (an error such as `UNEXPECTED_EOF_WHILE_READING`, a timeout, or the service being busy), the app now waits and tries again by itself, up to 4 more times over about 3 minutes, and the progress box shows it. Only if all of those fail does the load stop, keeping everything fetched so far. If Open-Meteo's free daily limit is reached it says so; press the button again the next day. If you restart Docker during a load, press it again.

To stop all online lookups, add `PLANTDB_WEATHER: "0"` under `environment:` in `docker-compose.yml` and run `docker compose up -d`.

### Connecting your own sensor

Open **Weather**, then **Connect your sensor**. It shows the address and a private token. Your sensor (or a small script on the device) sends a POST with the header `X-Ingest-Token: <token>` and a JSON body. All fields are optional except that you need at least one measurement:

- `device`: a name for the sensor (for example `porch`)
- `ts`: UTC time like `2026-10-20T14:00:00Z` (default: now)
- `temp_f` or `temp_c`; `humidity` (%)
- `par` (umol/m2/s) or `lux` (converted at 54 lux per PAR)
- `soil_moisture` (%), `soil_temp_f` or `soil_temp_c`, `soil_ph`
- `weight_g`: the weight of the pot on a weighing cell (from 1.35.0; the app shows how it changes as the pot dries)

Send up to 500 readings at once as `{"readings":[ ... ]}`. A reading with an impossible value is refused with an explanation.

From 1.12.0 sensors send to their own port, **8082**. It only takes readings with the token; nothing else of the app answers there. It is shut until you open it to your home network. Put the line `PLANTDB_SENSOR_BIND=0.0.0.0` in the `.env` file next to `docker-compose.yml` and run `docker compose up -d` (from the `plant-database` folder):

- Windows (cmd.exe): `(echo PLANTDB_SENSOR_BIND=0.0.0.0)>>.env` then `docker compose up -d`
- Windows (PowerShell): `Add-Content .env 'PLANTDB_SENSOR_BIND=0.0.0.0'; docker compose up -d`
- bash: `echo 'PLANTDB_SENSOR_BIND=0.0.0.0' >> .env && docker compose up -d`

The sensor then sends to `http://<your PC's Wi-Fi address>:8082/api/readings` ("Opening it to your home network again" shows how to find that address). Try it from the PC (replace `YOURTOKEN`):

Windows (cmd.exe):

```
curl -X POST http://localhost:8082/api/readings -H "X-Ingest-Token: YOURTOKEN" -H "Content-Type: application/json" -d "{\"device\":\"porch\",\"temp_f\":71.2,\"humidity\":58,\"par\":240}"
```

Windows (PowerShell):

```
Invoke-RestMethod -Method Post -Uri http://localhost:8082/api/readings -Headers @{"X-Ingest-Token"="YOURTOKEN"} -ContentType "application/json" -Body '{"device":"porch","temp_f":71.2,"humidity":58,"par":240}'
```

macOS / Linux (bash):

```
curl -X POST http://localhost:8082/api/readings -H "X-Ingest-Token: YOURTOKEN" -H "Content-Type: application/json" -d '{"device":"porch","temp_f":71.2,"humidity":58,"par":240}'
```

The token is the only thing protecting this address (the password option does not apply to it), so keep it private and use **Make a new token** if it leaks. When your sensor is working, choose "My sensor" in Current conditions.

## Environment fields on every plant page

Besides the temperature, humidity and light ranges, each plant now has: a feeding season and interval (months and days), heat-damage temperature, comfortable air dryness (VPD, in kPa), comfortable light as PAR and as daily light (DLI, mol/m2/day), soil mix, soil pH, soil moisture and soil temperature ranges, fertilizer and nutrients, pests and diseases to watch, what to do about them, and current pest problems. Claude filled these in as a first guess for every plant from its type; they are guesses to check against your own experience, and everything is editable (Edit this page) with the usual version history.

## Fertilizer calendar and log

Open **Fertilizer** (top menu) for the whole collection, or look at the **Nutrients** section of any plant page.

- **Should I feed today?** Every plant has a feeding season (first and last month it is fed) and a number of days between feedings, set by plant type. Each day is then one of: **Time to fertilize**, **Hold off** (a cold night is forecast at or below that plant's damage temperature, or its health is Poor or Critical), **Fed recently** (with the next date), **Resting** (out of season: do not fertilize), or **No feeding season set**. The Fertilizer page groups all plants this way, and each plant page shows the verdict for today and for any date you pick.
- **Calendar:** shaded days are in the plant's feeding season, hatched days are its resting season. "Fed" marks feedings you logged and "Due" the next suggested feeding. On the Fertilizer page the calendar covers all plants (how many were fed, how many are due). Click a day, or move with the arrow keys (PageUp and PageDown change month), for the details. "Show as a list" gives a plain list of days; with large text or a narrow screen it switches to the list by itself.
- **Log a feeding:** press **Log fertilizer** (or **Log a feeding for this plant**). Choose the date, the plants (one, or many at once: "All that are due", "All in season"), the fertilizer name, its type, and the N-P-K numbers printed on the package, then the amount and how much water it was mixed into (for example 1 tsp in 1 gal) and how it was applied. The form shows an estimate of how strong the mix is: parts per million of nitrogen, phosphate and potash, and the N : P : K ratio. Spoon measures are converted at 4 g per teaspoon and 12 g per tablespoon for dry products and 4.9 ml and 14.8 ml for liquids, so treat the numbers as estimates. Most potted plants do well at 50 to 200 ppm nitrogen. Logging in a resting season asks you to confirm.
- **Remembered fertilizers:** names you have used appear in a list and fill in the rest of the form next time. Entries can be changed or removed; the change log records each one.
- **What each plant needs (from 1.11.0):** every plant on the Fertilizer page has a line under its code and "last fed" line, for example "Needs N-P-K ratio 2-7-7, at half strength". The same box, **What to feed it**, is in each plant page's Nutrients section.
  - **Best match you have:** the fertilizer of yours whose N-P-K ratio is closest to what the plant needs, with its numbers and how close it is: **✔ Matches**, **✔ Close**, **▲ Usable** or **■ Not a good match** (it then says what to look for). It also says what is different, for example "It has more nitrogen (N) and less potash (K) than this plant needs".
  - **How much:** for a liquid or powder, how much to mix into how much water, for example "Mix ⅝ tsp into 1 gallon of water (0.8 ml per liter)", and about how many ppm of nitrogen that gives. Full strength aims for about 150 ppm of the strongest of N, P and K, half strength 75 and a quarter 40, which is a usual rate for plants in pots. If the label says to use less, use the label. Granular, slow-release, spikes and organic solids go on or into the mix, so it says what share of the label amount to use.
  - **Your fertilizers** (Fertilizer page): every fertilizer you have logged, plus any you add with **Add a fertilizer you have** (name, type and the N-P-K numbers from the package), even before you use it. **Change** corrects one; **Remove** takes off one you added.
  - **Log** next to a plant starts the feeding form with its best match and the amount already filled in.
  - Each plant's ratio and strength (None needed, Quarter strength, Quarter to half strength, Half strength or Full strength) are on its Edit page, under Nutrients. Claude filled them in for every plant from its fertilizer note (upgrade batch `batchA2`).
- **Change a plant's season:** Edit this page, Nutrients group: "Feed from month", "Feed through month" (a season like October to April is fine) and "Feed every (days)". The starting values are Claude's guesses from the plant type.

## Your plant calendar (from 1.15.0)

Feeding days and cold nights can go into Google, Outlook, Samsung or Apple calendars, with reminders. Open **Today**, **Fertilizer** or the **Cold-night checklist**, go to **Add to your calendar** at the bottom, and press **Set up your calendar**.

- **Choices** (saved as you make them):
  - feeding days, cold nights and close calls
  - one feeding day a week on the day you choose, or each day a plant is due. A plant is never moved earlier than it is due.
  - how far ahead (1 to 12 months)
  - your own reminder times: one on feeding days, one on the day before a cold night
- **Subscribe** with the calendar link, so the calendar updates by itself. The link works without your password. Keep it private; **Make a new link** stops the old one working.
- Google Calendar uses its own reminder settings for subscribed calendars: in Google Calendar's Settings, choose Plant record under "Other calendars" and set its notifications.
- **Save calendar file** adds the events once instead, without updates.

### Reaching the calendar from the internet with Tailscale Funnel

Google Calendar, Outlook.com and iCloud fetch the link from the internet. Tailscale Funnel lets them reach the calendar link only (the `/cal/` path on port 8443), not the rest of Plant record. Anything you share in your tailnet on port 443 with Tailscale Serve stays private.

1. Turn on Funnel for the calendar, on the PC that runs Plant record. If Tailscale says Funnel or HTTPS is not turned on for your tailnet, open the link it shows, turn it on, and run the command again.

   Windows (cmd.exe):

   ```
   tailscale funnel --bg --https=8443 --set-path=/cal http://127.0.0.1:8080/cal
   ```

   Windows (PowerShell):

   ```
   tailscale funnel --bg --https=8443 --set-path=/cal http://127.0.0.1:8080/cal
   ```

   macOS / Linux (bash):

   ```
   tailscale funnel --bg --https=8443 --set-path=/cal http://127.0.0.1:8080/cal
   ```

   If Windows says `tailscale` is not recognized, use the full path: `"C:\Program Files\Tailscale\tailscale.exe"` in cmd.exe, or `& "C:\Program Files\Tailscale\tailscale.exe"` in PowerShell, followed by the same words from `funnel` on.

2. See the address it made. The command is the same in cmd.exe, PowerShell and bash:

   ```
   tailscale funnel status
   ```

   It looks like `https://your-pc.tail1234.ts.net:8443`. Type it into **Internet address of this PC** in the calendar window and press **Save address**. The calendar link then starts with it.
3. Check it: on your phone, turn Wi-Fi off and open the calendar link in the browser. It should show or download a calendar file.
4. Subscribe with that link. The window's "How to subscribe in each calendar" has the steps.

Funnel keeps running after a restart. To turn it off (the same in cmd.exe, PowerShell and bash):

```
tailscale funnel --https=8443 --set-path=/cal off
```

## Past days: what the values were on a date

Temperature, Humidity (and air dryness), Light, and Water and soil (soil moisture, root-zone temperature, pH) each have a **Past days** box. Open it, pick the date on the calendar (or use the arrow keys), and you see that day's lowest, average and highest value, how many hours were in range, a chart of the day, and the plant's comfortable range **as it was recorded on that date** (if you changed the range later, both are shown). Each day on the calendar is marked in range, a little out, out of range or danger, and "Fed" where fertilizer was applied. Pick where the readings come from: your sensor, numbers you typed into Current conditions, or the online weather (outdoors, so for plants kept inside it only shows what the weather was). Days before any data was stored are blank; the online weather loads about 3 months back the first time, and more from the Weather page.

## Where the data is stored

Everything, including weather, sensor readings and the fertilizer log, is in `data\plants.db` in this folder (the `data` folder next to `docker-compose.yml`). The tables are `readings` (every weather, sensor and typed-in reading), `fertilizer_log`, and `settings` (forecast, location, sensor token) beside the plant tables. To look inside, copy the file first and open the copy with a free viewer such as DB Browser for SQLite.

Windows (cmd.exe):

```
copy data\plants.db plants-copy.db
```

Windows (PowerShell):

```
Copy-Item data\plants.db plants-copy.db
```

macOS / Linux (bash):

```
cp data/plants.db plants-copy.db
```

The weather tables are `locations` (your places), `readings` (hourly; sensors and weather, with the place in the `device` column: `open-meteo` for the original home place, `place-2` and so on for places you add), `weather_daily` (daily summaries, by place) and `weather_runs` (the update log, by place). To see how big the database is:

Windows (cmd.exe):

```
dir data\plants.db
```

Windows (PowerShell):

```
Get-Item data\plants.db | Select-Object Name, @{n="MB";e={[math]::Round($_.Length/1MB,1)}}
```

macOS / Linux (bash):

```
ls -lh data/plants.db
```

For a spreadsheet, use the **Weather** page's table (any columns, any dates) or the **Audit log** page: "Download weather and sensor readings (CSV)".

## Plant links and previews

Plant codes such as P-012 written anywhere in the Still to photograph list, in requests, or in a plant page's text link to that plant. Point at a link (or Tab to it) to see a small preview with the plant's photo, name and health; Escape closes it. On the **Photos** page you can add your own entries with a note and a **Related plant**, and **Edit** any entry; codes you type are linked too.

## Plant labels

Each plant page also has a **Label** section with the same label and a **Print this label** button (it prints only the label). On the **Labels** page every label has an **Open plant page** button. The plant ID (P-001 and so on) is now large, bold and black on the white label in every theme, including dark.

Open **Labels**, type the address from step 1 into "Address the codes should open", save, and print. Each label has a QR code that opens that plant's page. Codes made with `localhost` only work on the PC itself.

## Who made a change

People who open the app through Tailscale (from 1.12.0) are named by Tailscale: the top right says "Signed in as …", and their changes show under that name. Press it to change the name shown for you, and (owner) to see who can use the app.

On this computer (`http://localhost:8080`), the first time you save something the app asks for your name. It goes into the audit log with the date and time. It is typed in, not a login, so it records who says they made the change. Click your name at the top right to change it.

If you open the app to your home network again (see "Using the app away from home"), you can also require a password there: uncomment `PLANTDB_PASSWORD` in `docker-compose.yml` and run `docker compose up -d`. The browser then asks for it (leave the username blank or put anything). Never open port 8080 to the internet.

## Groups of plants (from 1.16.0)

The **Groups** page (in the top menu) gathers plants that are alike or kept together, so you can see what suits all of them and look after them in one go. A plant can be in several groups.

- **Smart groups** have a rule. For example "Genus is Philodendron", "Location is Covered porch", or "Name contains palm". A rule can have several parts, and plants join when every part fits, or when any part fits. Plants that fit join by themselves, and leave when they stop fitting. While you make or change the rule, the window lists the plants that fit.
- **Hand-picked groups** hold the plants you tick. Add or take out plants on the group's page, or from a plant's own page with **Change groups**.
- **Suggested groups** are listed under your own. They cover plants of the same genus, families whose plants share care (such as the Aroids, which use the same chunky potting mix), and plants under the same grow light. Press **Add this group**, or **Add all suggested groups**.
- **On the Plants page,** choose a group under **Group** to show only its plants, or choose **Sort by: Group A to Z**. Previous and Next Plant on plant pages follow the same choice.
- **On a plant page,** the card at the top lists the plant's groups, with links.

Each group's page has:

- **Plants in this group**, with where each one is.
- **What suits all of them**: the temperature, humidity, light, soil pH and soil moisture that suit the most plants, with the odd ones out named. It also shows how warm to keep the group, and because of which plants, and their winter plans, fertilizer ratios and potting mixes.
- **Do something to all of them** (for people who can edit):
  - **Log care for all of them:** what you did, the date, an optional note, and which plants (all are ticked to start with).
  - **Move them:** a new Location, a Spot such as "Tall Black Shelf", or a grow light spot (or take them out of their grow light spots).
  - **Change a setting for all of them:** choose the setting and the new value, and the next window shows each plant's current value. Plants already set to it are not ticked. Plants with a value different from the rest are marked, so you can leave them out. Only the ticked plants change. If someone changed a plant in the meantime, it is skipped so nothing is overwritten unseen.
- **Recent changes to the whole group,** each with **Undo this change**. Undo puts each plant back as it was, unless it was changed again since.

Removing a group never changes the plants in it. Group changes appear in the audit log under "Groups and changes to a whole group", and each plant's page history shows its own changes.

## Identify a plant and the plant library (from 1.18.0)

**Identify** (in the top menu) tells you which of your plants the camera is pointing at, and how sure it is. If the plant isn't one of yours, it suggests what it could be. **Library** looks up any plant species by name.

Everything is worked out on this computer, by a second container called `plant-vision`. It runs **BioCLIP 2.5 Huge**, a free AI model (MIT licence) trained on over 200 million pictures of living things. It runs on the processor and doesn't need the graphics card. Only the app can talk to it; it has no address of its own on this computer, your network or Tailscale. It can read your database and photos but can't change them.

### The first start

The first update to 1.18.0 takes longer than usual:

1. **Building the container** downloads about 1 GB of Python packages (PyTorch). The updater waits for this.
2. **Its first start** downloads about 5 GB into `data\vision`:
   - the BioCLIP 2.5 model (3.9 GB);
   - its fingerprints for 349,000 plant species (0.7 GB), from the Tree of Life list;
   - the USDA PLANTS lists of which plants grow wild in each state (9 MB).

   It then fingerprints your photos, well under a second each on your processor. The Identify page shows how far it has got. Plan on 20 to 40 minutes in all, mostly downloading. After that it starts in under a minute and needs no internet.

`data\vision` is safe to delete; it downloads everything again on the next start. Backups leave it out.

**From 1.22.0** it also knows about 49,000 fungi (mushrooms, lichens, moulds). The first start after that update downloads their fingerprints, about 100 MB, which takes a few minutes. Until then Identify and the Library still work for plants.

### Using the camera

- Open **Identify** and press **Start camera**. It checks about once a second.
- When it has seen the same plant twice and is at least 80% sure, a window names it: for example "Very likely P-020: Fiddle-leaf fig, 93% sure". It shows your picture next to that plant's closest photo. From there you can:
  - press **Open its page**;
  - press **Add this picture to its photos**;
  - press **Not this one** to keep looking.
- **Check this picture** holds the picture still and shows everything it found:
  - **Which one is it?** with three photos when it is unsure between plants;
  - **Probably not one of your plants** with species suggestions when it doesn't recognise the plant.
- **Use a photo instead** checks a photo you already have. On a phone it can also open the camera app.
- **Plant labels:** the QR codes on labels from the Labels page are read too, and open the plant straight away.

**How sure is "sure"?** The percentage comes from tests on your own 213 photos, each checked against all the others. It said 80% or more for a third of them, and was right 92% of those times. Over all your photos, the right plant came first 70% of the time and was in the top three 80% of the time. If a picture looks unlike all your photos, it says it is probably not one of yours. Similar plants are the hard cases, such as your Monsteras or two plants of the same kind. A clear daylight photo of the leaves, from about the distance of your other photos, works best.

**The browser only allows the camera on a secure address:** `http://localhost:8080` on this computer, or the Tailscale address `https://plants...` on your phone. On any other address, use **Use a photo instead**.

### Names for plants that aren't yours

Under **When it is not one of your plants, suggest names from**, choose:

- **Your state's plants**, such as **Texas plants** (about 4,750 species) or **California plants**, from the USDA lists. It follows the Location button (from 1.28.0), and is only offered for places in the US. Best for wild plants and weeds in your yard.
- **Plants with a common name, and all US plants** (about 34,000; the usual choice). Good for houseplants and garden plants.
- **US plants** (about 19,000).
- **All plants worldwide** (about 349,000).

Names guessed from a picture are often wrong at the species level; the genus is right more often. In tests on your photos with the usual list, the right species came first 43% of the time and was in the top five 65% of the time. The right genus came first 56% of the time. With the Texas list, for plants that grow wild in Texas, the right species came first 74% of the time. So treat the names as leads, and check them with the links (USDA PLANTS, Kew's Plants of the World Online and Wikipedia) or a second opinion.

**Add as a new plant** opens the Add a plant form with the names filled in and the picture attached when you save.

### Second opinions: Pl@ntNet and Claude

When this computer is unsure, the results have **Ask Pl@ntNet** and **Ask Claude** buttons. Ask Pl@ntNet first: it is free and very good with plants. They only see a picture when you press their button. You set them up once, as the owner, under **Second opinions** at the bottom of the Identify page:

- **Pl@ntNet:** a free account at my.plantnet.org gives an API key for 500 pictures a day. Pl@ntNet doesn't keep the pictures.
- **Claude:** an Anthropic API key from console.anthropic.com. It is billed to that account, about a cent or two per picture. Claude also says what it based its answer on, and what photo would make it surer.

The keys are kept in the database on this computer, and so in its backups. The app never shows them again, only their last 4 characters. People who can only view can use Identify and the library, but not the second opinions.

### The plant library

**Library** lists every species in the list chosen under **Look in**, straight away, with no search needed: about 34,000 in the usual list, up to 349,000 worldwide. From 1.21.0 it works like the Plants page:

- **Search** narrows the list as you type, by scientific or common name.
- **Filters:**
  - **Kind of plant:** broadleaf flowering plants, monocots (grasses, lilies, palms, orchids), ferns, conifers, cycads, mosses, algae and so on.
  - **Family:** type it, or pick from the list, which shows how many species each family has.
  - **Grows wild in:** the US, Texas, or any state.
  - **Show:** only the ones you have, or the ones you have plus others of the same genus.
  - **Only plants with a common name.**
- **Sort by:** best known first (common name, then how widespread in the US), common name, scientific name, or family.
- **Show as** cards with photos, or a table. **Show more** adds the next 48.
- The filters are remembered in this browser, and **Clear search and filters** starts over.

**Each species has its own page.** Click a card to open it. It has:

- Photos: yours first if you have the plant, then up to six from iNaturalist, each naming its photographer and licence.
- A short description from Wikipedia, and how often iNaturalist members have recorded it.
- Its common names.
- Its classification. Each order, family and genus is a link to the library filtered to it.
- The US states and territories where it grows wild.
- Your plants of that species or genus.
- **Looks like:** the species the BioCLIP model finds closest. They are the easiest to mix up with it, though not always close relatives.
- Links to USDA PLANTS, Kew, iNaturalist and Wikipedia, and **Add to my plants**.

**Where the photos come from.** Library photos and descriptions come from iNaturalist, whose members share their photos under Creative Commons licences. Only the species name is sent. The app fetches about one species a second, as iNaturalist asks, so a page of cards fills in over a minute the first time. Each photo is kept in `data\library`, so it is only fetched once. The owner can turn this off at the bottom of the Library page, and the library then works fully offline, without photos.

The names come from the Tree of Life list that BioCLIP was trained with (Imageomics Institute, free to use), and the states from the USDA PLANTS state lists (public domain).

#### Fungi in the library (from 1.22.0)

Choose **Fungi worldwide: mushrooms, lichens and moulds** under **Look in** (on the Library or the Identify page). **Kind of fungus** then filters to mushrooms (with brackets, puffballs and jelly fungi), cup fungi, lichens, rusts and smuts, or moulds and mildews. The USDA state lists include lichens but no other fungi, so **Grows wild in** only works for lichens.

A fungus page has a safety note at the top, your finds of that species, and **Record a find of this** instead of **Add to my plants**. Nothing in the app ever says a mushroom is safe to eat.

#### Your notes and tags (from 1.22.0)

Every species page has **Your notes and tags**. Press **Add notes and tags**, write anything, and add tags separated by commas (for example `shade, gift idea`). Tags are saved in lower case. Each tag is a link that lists every species with that tag, and the tags show on the library cards. Everyone you have given access to the app can read them; people who can only view can't change them.

#### Your wishlist (from 1.22.0)

On any species page, press **Add to my wishlist**. The Library page has a **Your wishlist** button, which opens the list:

- **Got it** moves a plant to "Got them" (and **Move back to wanted** undoes that).
- **Edit** adds where to find it (a nursery, a website) and notes.
- **Take it off the list** asks first.

In the library, **Show** can be set to **On my wishlist**, **Ones with notes or tags**, or any one of your tags.

#### Prices, stock and alerts (from 1.27.0)

From 1.30.0 this is on the **Shopping** page, with the stores on the **Stores** page (see "Shopping, stores, and quicker pages"). The plant record checks the stores for everything you still want: every 12 hours, or when you press **Check the stores now**.
- **On each wanted plant:** the cheapest listing now (with a link to it), how many shops have it, and **Every listing found, with past prices**.
- **Edit, and set alerts** sets:
  - **Search the shops for**: one search per line, such as a variety ("Monstera Thai Constellation"). If it's left empty, the common and scientific names are used.
  - **Alert me when the price is at or under** $X, shipping not included.
  - **Alert me when a shop has it in stock**.
- **Alerts** appear at the top of the Wishlist page and on Today, and the top bar shows how many beside **Library**. Each check makes at most one alert per plant. A price alert comes again only if the price drops further, and a stock alert comes again only if it sold out and came back. **Dismiss** clears an alert.
- **Shops checked** (at the bottom of the Wishlist page) lists every shop, how it is read, and its last check, or what went wrong. The owner can turn shops on and off, change an address, add a shop, and choose how often:
  - **Online stores** (Steve's Leaves, Logee's, North Spore and others) are read for names, prices and stock. The kind of store is worked out on the first check.
  - **Local nurseries with no online store** (Round Rock Garden Center, Snooper's, Cantu Imports, Barry Hill) have their plant pages read for the names on your wishlist, with the price if it's on the same line. Call them to be sure.
  - **eBay and Etsy** are searched through their official services, which need free keys from developer.ebay.com and etsy.com/developers. The owner pastes them under **eBay and Etsy keys**. They're kept on your computer and never shown again.
- Walmart, Home Depot, Lowe's, Amazon and Facebook Marketplace are left out on purpose.
- Each shop gets at most one request every 2 seconds, a few times a day, and the requests say they come from a home plant record.

#### Your area, pets and care sheets (from 1.23.0; from 1.28.0 for any place)

From 1.28.0 everything here is about the place chosen with the **Location** button (Round Rock or Nevada City, or any other place), not always Texas. Each place's state (or, outside the US, its country) is looked up on iNaturalist once. Below, "Texas" means that state or country.


Each plant's page in the library now has three more sections:

- **Here at home:**
  - whether it is native or introduced in Texas;
  - how often people have recorded it growing wild within 31 miles of home, and whether it is flowering there this month;
  - a warning if it is on the Texas noxious and invasive plant list (Texas law says those may not be sold, distributed or brought into Texas).
- **Will it survive outside here all year?** "Likely" if it grows wild near home, or if its care sheet's hardiness zones include yours (worked out from your own weather history; 9a for Round Rock). Otherwise it says it doesn't know.
- **Pets:** what the ASPCA's lists say for dogs, cats and horses. A plant not on their lists is not called safe.
- **Care sheet:** press **Write a care sheet with Claude**. Claude writes one for your place and zone in about half a minute, using the owner's Anthropic key (the one on the Identify page; a cent or two each). It covers light, water, soil, temperature, feeding, pruning, propagation, pests, pots, hardiness and growing it outdoors here. It is kept, everyone with access can read it, and it is marked "not checked by a person". People who can only view can read care sheets but not ask for them.

The cards show the same things as tags (for example "Native to Texas", "Flowering near home now", "⚠ Toxic to dogs and cats", "⚠ Texas invasive list"). The filter **Your area** (called "Texas and home" before 1.28.0) lists only:
- the ones native to or introduced in Texas;
- the ones on the invasive list;
- the ones that grow wild near home, or are flowering there this month (or, for fungi, found there this month);
- the ones likely to survive outside here;
- the ones safe for, or toxic to, dogs and cats.

**Around home** (a button at the top of the Library page, and on the Mushrooms page) shows three lists, with photos:
- what is flowering near home this month;
- the mushrooms and other fungi found there this month;
- the plants and fungi recorded wild there most often.

**Where this comes from.** These lists are fetched in the background, about one request a second, and kept in `data\library\local`. **Lists about your area**, at the bottom of the Library page, shows each one, when it was fetched, and **Fetch the lists again now**. The lists are fetched again by themselves when they get old (Texas lists and pets every 3 months, near home every month, this month's flowers and fungi every 2 weeks).

- **iNaturalist:** what is native or introduced in Texas, and what people have recorded wild near home (only species names and the home place's position are sent).
- **The ASPCA's** toxic and non-toxic plant lists, read from their web pages.
- **The Texas Department of Agriculture's** noxious and invasive list, which is built in. It is only used for places in Texas: the app has no such list for other states or countries yet, and says so.

When the owner turns library lookups off, none of this is fetched.

#### Photos for offline use (from 1.22.0; by area from 1.28.0)

At the bottom of the Library page, **Photos for offline use** has a table of areas. An area is any country, state, county, city or park that iNaturalist knows. For each area the app gets the list of every plant species recorded there, then downloads each one's photo and short facts, so the library shows them without the internet.

The table shows, for each area:
- **Photos downloaded**, out of how many species there are (and how many have no photo on iNaturalist);
- **Percent** downloaded, as a number and a bar;
- **Last updated**: when its list was last fetched;
- while it runs, how many are left and about how long it will take.

The owner can:
- **Add an area:** type a name (for example "California"), press **Search**, then **Add and download** beside the right place;
- **Check for updates:** fetch the area's list again and download only what is new;
- **Remove** an area: it leaves the table, but its photos stay (another area may use them);
- **Stop all downloads.**

Downloads go at about one species a second, after anything someone is looking at, so a state with 5,000 species takes about an hour and a half and uses about 350 MB in `data\library`. Species already kept are skipped. You can leave the page while it runs. If the app restarts part way through, press **Check for updates** to carry on.

### Stopping the picture checker

The rest of the app works without it. Identify and Library then say it isn't running. It uses about 6 GB of memory while running, and no processor time when idle. From the `plant-database` folder:

Windows (cmd.exe):

```
docker compose stop vision
docker compose start vision
docker compose logs --tail 30 vision
```

Windows (PowerShell) and bash: the same commands.

`docker compose up -d` (and the updater) starts it again. To keep it stopped for good, put the line `PLANTDB_VISION=0` in the `.env` file:

- Windows (cmd.exe): `(echo PLANTDB_VISION=0)>>.env` then `docker compose up -d`
- Windows (PowerShell): `Add-Content .env 'PLANTDB_VISION=0'; docker compose up -d`
- bash: `echo 'PLANTDB_VISION=0' >> .env && docker compose up -d`

### A smaller, faster model

If the computer is busy or short of memory, BioCLIP 2 is about half the size. It recognises your own plants nearly as well, but is much weaker at naming plants that aren't yours: with the usual list, the right species came first 17% of the time instead of 43%. To use it, put `PLANTDB_VISION_MODEL=bioclip-2` in the `.env` file and restart. It downloads its own 2.2 GB the first time.

- Windows (cmd.exe): `(echo PLANTDB_VISION_MODEL=bioclip-2)>>.env` then `docker compose up -d`
- Windows (PowerShell): `Add-Content .env 'PLANTDB_VISION_MODEL=bioclip-2'; docker compose up -d`
- bash: `echo 'PLANTDB_VISION_MODEL=bioclip-2' >> .env && docker compose up -d`

To go back, delete that line from `.env` and run `docker compose up -d` again.

## One identifier (from 1.40.0)

Identify, **Add a plant** and **Several plants from photos** now share one identification path, so they give the same answer for the same photos:

1. All the photos of the plant go to the picture checker on this computer together (it compares them with your own plants' photos and names the species, weighted as in 1.39.0).
2. **Pl@ntNet** is asked as well whenever its key is saved: always when "Ask Pl@ntNet on its own" is ticked on the Identify page, otherwise only when this computer is unsure. Its answer is merged into the same list — a name both agree on moves up, and each name says who said so (**This computer**, **Pl@ntNet 96%**).
3. The likeliest **genus** and **family** are worked out over the whole list. When no species fits, those are the safer answers (Pl@ntNet named Ethan's split rocks *Pleiospilos nelii* at 96% where the computer alone had six wrong names; this is why the key matters).
4. **Not this** / **Not this genus** on every name: the name (or the whole genus) leaves the list, the photos are checked again without it, and the choice is logged in the audit log.

On a plant's page, **Check the name from its photos** (under Plant identification) runs all its photos through the same identifier; **Use this name** renames the plant and a "Not this" there sticks to that plant. On **Several plants from photos**, each plant's photos are checked together as soon as you have sorted them (and again whenever you change the sorting); each plant has **Check the photos again** and **Ask Pl@ntNet about this plant**. On **Add a plant**, "Fill in the names from the first photo" uses all the photos on the form and shows the list with **Use this name** on each.

## Room for the content (from 1.39.1)

List pages put the content first. Each keeps one row of controls (Search, the one or two that matter most on that page, Sort) and folds the rest under **More filters**, which opens by itself while one of its filters is on and remembers your choice for the visit:

| Page | On the row | Folded |
|---|---|---|
| Plants | Search, Home, Location, Sort by | Health, Group, Show (active or archived), ID confidence under 70%, Light needs, Pets, Winter here, Care today, and the rest |
| Identify → Your plant photos | Search, Sort by, Only plants with no photos | Health, Home, Location, Group, Show, and the rest |
| Library | Search, Look in, Sort by | Kind, Family, Grows wild in, Show, Your area, Show as, Only with a common name |
| Audit log | (the whole box is folded until a filter is on) | |

**Read this page aloud** sits beside the page title on a computer. A page with no sections has no "On this page" menu. On Grow lights, a light's name, count, model and place are shown as text; **Edit the name, count, model and where it is** opens the fields.

## Better names from Identify (from 1.39.0)

The picture checker (BioCLIP, on this computer) used to rank every species by the picture alone, which put three wrong names on the screen often enough. From 1.39.0 it weighs the names toward what you are likely to be looking at:

- **Your record:** a species already named in your plants, or its genus, is lifted. A new pot of a plant you have gets its name.
- **Your photos:** when one of your named plants' photos looks like the picture, that species is lifted (the closer, the more).
- **Houseplants** (about 150 genera grown indoors) and **the plants of your state** (with the state list chosen) are lifted a little.
- Each lifted name says why on its card ("Lifted: a houseplant", "Lifted: looks like your photos"). The line under the result says the names are weighted. To turn the weighting off, put `VISION_PRIOR=0` in `.env` and restart.
- **Ten names** come back, five shown; **Show 5 more names** unfolds the rest. The three likeliest **genera** are on the line above: when no species fits, the genus is the safer answer.
- **Several pictures of one plant:** after a result, **Add another photo of the same plant** (or **Add a camera shot of it**) checks them all together. Each picture is also looked at three ways (as it is, the whole picture letterboxed, and its middle).
- **Pl@ntNet first when unsure:** under Second opinions, tick **Ask Pl@ntNet on its own whenever this computer is unsure**. With the Pl@ntNet key saved, a picture the computer is not sure about (no sure match among your plants, best name under 50%) goes to Pl@ntNet at once and its answer shows above the computer's own. Each costs one of Pl@ntNet's 500 free pictures a day.

The weights were set by judgment, not measured on your photos. `dev/vision/prior_test.py` (run on the PC, where the model and photos are) says how often the right name comes first with and without them, so they can be tuned.

## On the phone and offline (from 1.38.0)

### Watering offline

On the Today page without a connection, **Watered** and **Still moist** now take the plant off the list at once, and the plant's care log shows the entry as "not sent yet". The plant server gets it when it can be reached again (the entry then loses its "not sent yet" and gains its Remove button).

The same goes for the other everyday changes: "Log other care" and Remove on a care entry, Moved indoors and Covered on the cold-night list, Fed, answers to Claude's requests, the Still-to-photograph ticks, photo captions, main photo and photo removal, the porch reminder, the wishlist and species notes. Each shows on its page at once and goes to the server later; a photo added offline shows as a thumbnail in the "Not sent yet" line on the plant's page. Settings, rooms and spots, lights, groups, stores, backups and sensors still need a connection (they are things you do at the PC).

### When Tailscale comes back

The app now tells apart "this phone has no network" from "the plant server cannot be reached" (Tailscale off, or the computer asleep): both show as **Offline** at the top. While the server is out of reach the app tries again every 30 seconds, whenever you bring it to the front, and when the network comes back; the offline note on every page and the Offline use page have a **Try to connect now** button as well. When the server answers, the waiting changes are sent and the page is drawn again from the server (unless you are in the middle of a form). No relaunch needed.

### Back goes back to where you were

Going back to a page (the phone's Back button, or a "Back to…" link) returns to the same place on it. A link to a new page starts at the top. Photo boxes have their size before the photo arrives, so pages no longer jump as photos load.

### Photos on the Add a plant form

**Add a plant** (one plant) has a **Photos** field: take them now or choose them from the phone's photos. The first becomes the main photo. **Fill in the names from the first photo** asks the picture checker and fills in the empty name fields. On Identify and on the plant page, "Choose a photo" / "Add photos" no longer forces the camera open: the phone offers its photos too.

### Adding a plant without a connection

Without a connection, saving the Add a plant form keeps the plant on this device (with a NEW- code) and sends it when the server can be reached. With a photo, the common name may stay empty: a stand-in name ("New plant, date") is used. Once the plant is sent, its first photo is checked by the picture checker and the Offline use page shows what it looks like, with a button to **put the first name on** the plant. The Plants page says how many new plants are waiting.

### Several plants from photos, on a phone

The review screen makes small previews of the photos on the phone itself (about 800 px), so it no longer shows white patches while scrolling. See "Add several plants at once" below for the new per-photo questions and the wide shot that goes on every plant.

## Photos from your phone, the year in review, and the mirror (from 1.37.0)

### Share a photo from your phone

On an Android phone with the app added to the Home Screen (Chrome or Edge: menu → Add to Home screen), **Plants** appears in the phone's share sheet. Share a photo (or several) from the camera or gallery and choose Plants: the app opens on **Photos shared with Plant record**, with the pictures shown, a plant to choose (recently changed ones first) and a caption. **Add** puts them on that plant, or under Photos to assign later. iPhones do not offer this for web apps; there, use the camera button on the plant's page as before. The Photos page has a link to the shared-photos page too.

### The year in review

**Plants → Year in review** (`#/review`): one card per plant for a year, from everything the app logged: new this year or archived, how its health went, moves between places, waterings and feedings, how many cold nights it sat outside below its damage point and how many days at or above its heat-damage temperature, requests answered, and its first and last photo of the year. The plants with the hardest year come first (■), those that got better are marked ✓. Choose the year, narrow the list (hard year, got better, new, quiet) and print it. Good for deciding what to keep, what to move and what to let go.

### The mirror: a read-only copy on another machine

The `mirror` folder in the app folder sets up a second copy of the app on another machine (the spare hardware, or your girlfriend's PC): it runs the same app with the backup receiver, takes the newest backup every 5 minutes and shows that, read-only, at `https://plants-mirror.<your tailnet>.ts.net`. Every page on the mirror says which backup it shows and links to the main app; changes are refused. `mirror/README.md` has the steps (cmd.exe, PowerShell and bash). Photos on the mirror come from the last backup made with photos, so set the Backups page to include photos now and then.

## Finding your way, summer heat for each plant, probe calibration and the health of the app (from 1.36.0)

### Every page in its section's row

The pages of each section are listed in the row under the top bar, and the Pages menu and the search window list the same pages. From 1.36.0 that includes the ones that used to hide behind a button: in **Care**, the **Cold-night checklist**, **Coming inside** (getting plants ready to come inside) and **Back outside** sit next to Winter plan, Fertilizer, Grow lights and Pots; **Discover** has **Around home**; **Settings** has **Offline decisions**. The features are also reachable from where you would think of them: a plant's page has an **Every plant coming inside** button in its "Getting ready to come inside" section, a plant card on the Plants page links to that plant's pest check when its winter plan is to move indoors, and Today's "Getting ready to come inside" section opens the Coming inside page. A page can open at one of its sections with `?sec=` after its address (`#/plant/P-001?sec=inside`).

Where everything lives, one line per page:

| Section | Page | What it is for | Also reached from |
|---|---|---|---|
| Today | Today (`#/`) | What needs you today: cold nights, sensors, water, feed, Shopping alerts, requests | The app opens here |
| Plants | All plants (`#/plants`) | Every plant, with filters; the cards | `H` key, labels, the Weather page's summer counts |
| Plants | Groups | Smart and hand-picked groups | Plant pages, the Group filter |
| Plants | Add plants | One plant, or several from photos | The Plants page's Add a plant |
| Plants | Mushrooms | Finds and their safety notes | |
| Plants | Rooms and spots | Rooms, areas and spots; their labels | Plant pages (Where), labels |
| Plants | Photos | Unassigned photos and the list to photograph | Plant cards, Today |
| Plants | Labels | QR labels for plants, rooms and spots | Plant pages (Label) |
| Care | Winter plan | The plan for the season, plant by plant | |
| Care | Cold-night checklist | Which plants to bring in or cover tonight | The cold-night banner, Today, notifications |
| Care | Coming inside | Pest checks before plants come in, with each plant's status | Plant pages, plant cards, Today |
| Care | Back outside | Which plants can go back out in spring | The Winter plan |
| Care | Fertilizer | Your fertilizers, the calendar and the log | Plant pages (Nutrients), Today |
| Care | Grow lights | Lights, spots and the layout | Plant pages (Sunlight) |
| Care | Pots and trays | Your containers | Plant pages |
| Weather | Weather | Forecast, history, charts, your climate | Plant pages (Current conditions) |
| Weather | Sensors | Your sensors, calibration, set-up | Plant pages (Water and soil), Today |
| Weather | Homes and places | The places whose weather is tracked | Settings, the Location button |
| Discover | Identify | Name a plant from a photo | Plant pages (Plant identification) |
| Discover | Library | Species, facts and photos | Plant pages, Identify |
| Discover | Around home | What is flowering, fruiting or found near home this month | The Library |
| Discover | Wishlist | Plants you want | Library species pages |
| Discover | Shopping | Supplies and plants you are watching, stores, the shopping list | Today's alerts, Pots and Fertilizer ("watch for it") |
| Settings | Settings | People, display, notifications, health of the app, debug | The Display button |
| Settings | Offline use | The copy on this device, changes waiting, saved pages | The Offline banner |
| Settings | Offline decisions | Changes that clashed while offline | The Offline page |
| Settings | Backups | Backups, restore, the second copy | Health of the app |
| Settings | Audit log | Every change | Plant pages (History) |

### Summer heat for each plant

Under **About this plant**, after the hardiness zones: how many days a usual year reach the plant's "Heat damage above" temperature and in which months, with a verdict in words and a mark: **✓ Summer heat is fine for it here**, **▲ A few days a summer are too hot for it**, or **■ Summer heat is hard on it here**; and, when the plant has a published AHS heat zone range (batch B6 adds ranges with sources for 20 of your plants; add others with Edit, under About this plant), whether your place is **within**, **hotter than** or **cooler than** its range. The Plants page gets a **Summer here** filter under More filters, and the Weather page's "Your climate" section counts your plants by verdict, each count a link to the filtered list.

### Calibrating a soil probe

If a sensor sends its probe's raw volts (`soil_raw`; the ESPHome file does), its card has **Calibrate the soil probe**: hold the probe in dry air and press **This is dry air**, then put it in a glass of water and press **This is water**. From then on the app works out the percentage itself from the volts, so the numbers in the ESPHome file no longer matter. **Start over** clears both.

### Soil moisture on the plant's page

With a sensor in its pot, a plant's **Timeline** starts with the soil moisture over the last 60 days, the waterings marked (pressed, or seen by the sensor) and the plant's range shaded; its fertilizer calendar shows each day's average ("Soil 43%") and the waterings.

### Health of the app

The first card on **Settings**: the version, counts, the last backup and its second copy, the last weather update and store check, open problems, and the data folder's size with the free space on its disk, each line with a ✓ or a !. The Jobs and Problems windows open from the same card.

### Clear the saved pages

Pages you have opened show straight away from what was saved last time and are checked again just after. If something looks stale, the Offline page's **Clear the saved pages** empties that store.

### Buttons that say what they do

Every Remove, Change, Delete and Download button in a list now names the thing it acts on for screen readers ("Remove the device iPhone"), and the smoke test refuses bare names from now on.

## Your sensors (from 1.35.0)

**Weather → Sensors** (`#/sensors`) shows every sensor that sends readings, one card each, the ones that need a look first: its newest values in large type (soil moisture, air temperature, humidity, light now, root-zone temperature, soil pH, pot weight), a small line of the last 24 hours for each, the lowest and highest of the day, and how much the soil moisture and weight changed since a day before. Daily light is worked out once a day of light readings is in.

Press **Change name, spot or plant** to give a sensor a name you will recognise, say where it sits (a room, area or spot from Rooms and spots) and which plant's pot it is in. Once it is in a plant, each value is compared with that plant's ranges, in words with a mark: **✓ In range**, **↓ Dry**, **↑ Wet**, **Cool**, **Warm**, **Dry air**, **Humid**, **Too dim**, **Too bright**, and **! Too cold** when the air is below the plant's damage point. The same card shows under **Water and soil** on the plant's page. A sensor that has sent nothing for longer than its quiet hours (3 to start with) says **Quiet** with a dashed border. The owner can **Forget this sensor** (its readings go too).

- **Today** lists the sensors that need a look or have gone quiet, with a jump button; "Quiet today" says when all are in range.
- **Watering from the sensor:** when a sensor in a plant's pot sees the soil moisture jump by 15 points or more within 3 hours, the app logs a watering for that plant for the day (once a day, signed "Sensor"), so the Today page stops asking. Turn it off per sensor in its window.
- **Notifications:** a new kind, **Sensor alerts**: a dry pot, dangerous cold at a sensor, or a sensor gone quiet, once a day each (Settings → Notifications).

### An ESP32 sensor node with ESPHome

The easiest build is an ESP32 running [ESPHome](https://esphome.io): no code, a short text file. `sensors/esphome-plant-sensor.yaml` in the app folder is ready for a capacitive soil moisture probe, an SHT31 air temperature and humidity sensor, a BH1750 light sensor, a DS18B20 soil temperature probe and an HX711 weighing cell under the pot; delete the sensors you do not have. It posts one reading every 10 minutes to port 8082.

1. Open port 8082 to your home network (see "Connecting your own sensor" above) and copy the token from Weather → Connect your sensor.
2. Install ESPHome on the PC and start its dashboard (it runs in Docker, like the app):
   - Windows (cmd.exe): `docker run -d --name esphome -p 6052:6052 -v %USERPROFILE%\esphome:/config ghcr.io/esphome/esphome`
   - Windows (PowerShell): `docker run -d --name esphome -p 6052:6052 -v $env:USERPROFILE\esphome:/config ghcr.io/esphome/esphome`
   - bash: `docker run -d --name esphome -p 6052:6052 -v ~/esphome:/config ghcr.io/esphome/esphome`
3. Copy `sensors/esphome-plant-sensor.yaml` into that `esphome` folder, and make `secrets.yaml` next to it with your Wi-Fi name and password, `plantdb_url` (`http://<your PC's Wi-Fi address>:8082/api/readings`) and `plantdb_token`. Change `device` at the top of the file to the name you want to see in the app.
4. Open `http://localhost:6052`, plug the ESP32 into the PC by USB, and press **Install** → **Plug into this computer** (the first flash is over USB; after that, updates go over Wi-Fi).
5. The sensor appears on the Sensors page with its first reading. Name it and put it in its plant.

Calibrate the soil probe once: note its raw voltage in dry air and in a glass of water and put those two numbers in the `calibrate_linear` lines (the file says where).

## Today as the home page, the shopping list, speaking a note, room labels and summer heat (from 1.34.0)

### Today is the page the app opens on

The app now opens on **Today**: one line says what needs you (a cold night, plants to water and feed, Shopping alerts, my requests), with a button to jump to each part. The cold-night warning is a section of the page here, not a banner, so the sections menu lists it. **Quiet today** at the bottom says what is not due: pest rounds, when the stores were last checked, the last backup, and whether there are problems to look at. **All plants** is one click away in the Plants section (its address is now `#/plants`; the old `#/today` address still opens Today). The `H` shortcut still goes to the Plants page.

### The shopping list for a store visit

On **Shopping**, press **Shopping list for a store visit** (`#/shopping/list`). Choose a store: the items it carries (from what you set under Stores, and listings found there) come first with what you are watching for; the rest are under "Not carried here, as far as the app knows". Add anything else you need (twine, a trowel), tick what you bought, and press **Done shopping**: the ticked items are marked **got it** on Shopping and the extra lines are crossed off. **Large print** makes the list bigger for the store; **Print** prints it. Ticks are kept on this device until you are done; the extra lines follow your sign-in like the other settings.

### Speak a note

Every box that takes several lines of text (notes, change notes, answers) has a **Speak** button that appears when you are in the box. Press it, say what you want, and the words are written after what is already there; press it again to stop. It uses the browser's own voice typing (Chrome, Edge and Safari have it; the first time, the browser asks to use the microphone). Firefox has no voice typing, so the button does not appear there.

### Room, area and shelf labels

The **Labels** page now also has a label for every room or area and every spot under **Rooms and spots**. Stick one on the shelf or by the door: scanning it opens the Plants page showing just the plants that live there, with a **Show every place** button to clear it.

### Summer heat next to winter cold

The **Weather** page has a **Your climate** section: the USDA hardiness zone (how cold a usual winter gets) and, from the same weather history, the **AHS heat zone**: how many days a usual year go above 86°F (zone 1 has less than one, zone 12 more than 210), the hottest day, which months the hot days fall in, and a table of each year's count. Plant pages say the heat zone next to the winter zone under "About this plant". It appears once the app has 3 whole years of weather for the place.

## Notifications, a second copy of backups, and search (from 1.33.0)

### Notifications

**Settings, Notifications.** Press **Turn on for this device** on each phone or computer that should get messages (the browser asks for permission once). On an iPhone or iPad, add the app to the Home Screen first (Share, then Add to Home Screen) and open it from there. Then tick which kinds reach you; the choices are your own, saved for your sign-in, and apply to every device you turned on:

- **Cold nights:** when a cold night comes into the forecast, and a reminder at about 3 pm the day before it.
- **Shopping alerts:** a price at or under your limit, or something back in stock.
- **Watering and feeding due:** one message at about 8 am with what is due today.
- **Requests from Claude:** when a release adds a request (a photo or an answer Claude needs).

Cold nights and what is due are for the home you start on (People, Starts on). **Send a test** checks a device. Messages go through the browser's own push service (Google's for Chrome, Apple's for Safari); only the title and a line of text are sent, encrypted for that device. Notifications need the app's Tailscale address (https) or this computer itself.

### Second copy of backups

**Backups, Second copy.** Each new backup is copied as soon as it is made:

- **Another drive:** to the folder named by `PLANTDB_COPY_DIR` in the `.env` file next to `docker-compose.yml` (for example `PLANTDB_COPY_DIR=D:\PlantBackups`), after `docker compose up -d`. Until that is set, copies go to `backups-copy` next to the data folder, which is the same drive. The newest 10 are kept.
- **Another computer:** run the receiver from the `receiver` folder of the release on it (its README has the steps: Docker, a token, Tailscale), then type its address and token on the Backups page. The newest 20 are kept there.

**Copy the newest backup now** tries both. What happened last shows under the form, and failures go on the Problems list.

### Search everywhere

The **Search** button in the top bar, or the `/` key anywhere, opens a search over plants (code, names, where they are, notes), pages, groups, rooms and spots, stores, mushroom finds, Shopping items and species in the library. Results are grouped; the arrow keys move through them and Enter opens one.

## Jobs (from 1.32.0)

**Settings, Jobs** shows what the app is doing in the background: what is running now (with how far it has got), what runs on a schedule (the hourly weather update, the store check, the automatic backup) with when each is next due and when it last ran, and what has finished since the app started, with how long each took. The owner has a **Run now** button for the weather update, the store check and a backup. The window keeps itself up to date while it is open.

## High Contrast, Problems, Restore, and a home per person (from 1.31.0)

- **Windows High Contrast mode** is supported: turn it on in Windows (Settings, Accessibility, Contrast themes) and the app follows it, with an outline on the page you are on, the chosen filter and keyboard focus.
- **Settings, Problems** lists anything that went wrong in the background, newest first, with how many times it happened. Open **Details** for the error's own words, or press **Copy the list for Claude** and paste it into the chat. The owner can clear problems one at a time or all at once; **Show cleared ones too** brings them back.
- **Backups, Restore** on any backup puts its database back. Before it does, a backup named "Before restoring…" is made, so the restore itself can be undone. Photos are never deleted. A backup from an older version is upgraded on the way in; one from a newer version is refused until that version is installed.
- **People, Starts on:** the owner picks the home each person starts on. It applies the first time they open the app after it is set; whatever home they choose with the Home button after that is kept.
- If an older release is ever installed over a newer one, every page says "Plant record will not run on this database" and which version to install. Nothing is changed. (`PLANTDB_ALLOW_OLDER=1` in `.env` overrides this, for emergencies only.)

## Shopping, stores, and quicker pages (from 1.30.0)

**Shopping** (under Discover) is where the stores are checked: for the plants on your wishlist, and for garden supplies.

- **Show** picks one kind: Wishlist plants, Pots and trays, Potting mixes, Amendments, Fertilizers, Pest control, Frost cloth and covers, Grow lights and timers, Tools and labels. On a phone it is a dropdown.
- **Stores near** picks a home: online stores count for every home, and stores you can visit count only for the home they are near.
- **Add something to watch** adds a supply: what it is, its kind, what to search the stores for, and alerts.
- **Cheapest now** shows the price per quart (potting mixes and amendments), per pound (fertilizers) or per square foot (frost cloth) when a listing says its size, so an 8 qt bag and a 2 cu ft bag can be compared. A price alert can be for the whole listing or per unit.
- **Stores near you that carry it** lists the stores you can visit for that kind, with their phone numbers.
- Buttons elsewhere start watching for you: **Watch for more on Shopping** on each pot or tray, **Watch for it on Shopping** for each N-P-K ratio on the Fertilizer page, and **Watch the stores for frost cloth** on the cold-night checklist.
- The Wishlist page keeps the plants you want, and points to Shopping for the stores, prices and alerts.

**Stores** (the button on Shopping, or Settings, Stores and keys) lists every store: near Round Rock, near Nevada City, and online. Choose one to open its page:

- its address with a map link and the distance from home, its phone numbers (tap to call on a phone), its hours, email and website, and where those details came from;
- what it carries, how it is checked, and its last check;
- **What you are watching that it has**, with each price, the price before, and the price per unit;
- **What they had**: notes after you call or visit, which everyone sees.

**Edit details** changes the address, phone, hours, what it carries and the home it is near. **Look them up on OpenStreetMap** fills in what is still empty (hours, phone, website and its map position). The owner turns stores on and off, adds stores, chooses how often they are checked, and keeps the eBay and Etsy keys, all at the bottom of the Stores page.

The details for the stores near Round Rock and six stores near Nevada City (Peaceful Valley, B&C Ace, Weiss Brothers, Prospector's, Nevada City Blooms and Double Dogwood) came from their own websites in November 2026. Hours change, so call before a long drive.

**Quicker pages:**

- The page you choose shows at once: its name and "Loading" if it takes more than a moment.
- A page you have opened before shows what this device had from last time straight away, then quietly checks for anything newer and redraws if something changed (not while you are typing on it).
- Pointing at a link, or moving to it with the keyboard, starts loading that page, and once a page is open the other pages in its section are fetched in the background.
- Answers from the plant server are sent squeezed (about five times smaller).
- **Settings, Debug, Page timings** shows how long each of the last pages took: waiting for the server, drawing the page, and the slowest answers. If pages are slow on your computer, these numbers show where the time goes.

## The top bar, rooms and spots, pots and trays, editing on the page, and settings that follow you (from 1.29.0)

### The top bar

Six sections: **Today**, **Plants**, **Care**, **Weather**, **Discover** and **Settings**. Choose one, and its pages appear on a second row under it:

| Section | Its pages |
|---|---|
| Today | Today |
| Plants | All plants, Groups, Add plants, Mushrooms, Rooms and spots, Photos, Labels |
| Care | Winter plan, Fertilizer, Grow lights, Pots and trays |
| Weather | Weather, Homes and places |
| Discover | Identify, Library, Wishlist |
| Settings | Settings, Offline use, Backups, Audit log |

The version number is always beside "Plant record". The **Home** button (it said Location before) chooses which home or place the weather, frost warnings and watering are for. The **Settings** page gathers people and names, Display, Offline use, Backups, the Audit log, Homes and places, shops and keys, and **Debug** (which used to be at the bottom of the screen). On a phone the sections fold into the **Pages** button, and the row of pages stays under it.

### Rooms and spots

Where a plant is has three parts: **outside or inside**, the **area or room**, and the **spot**. For example: Outside, Yard, Pallet shelf; or Inside, Downstairs Living Room, Large Brown Hutch.

- **Rooms and spots** (under Plants) lists each home's areas outside and rooms inside, with their spots. Type over a name to rename it; it saves when you leave the box. **Add area**, **Add room** and **Add spot** are under each list, and **Remove** beside each one. An area or room with plants in it can't be removed until they are moved; removing a spot leaves its plants in the room.
- **Roof overhead** (outside) and **Heated** (inside) decide how frost warnings and watering treat the plants there. Outside with a roof counts as a covered porch; inside without heat counts as a garage or shed.
- On a plant's page, choose **Inside** or **Outside**, then the area or room, then the spot. **More about where** (the old "Spot (where exactly)") keeps whatever you wrote.
- Your Rooms and shelves from the Grow lights page became rooms and spots, and a light spot's **Where** chooses from the same list.
- **Spots to sort out**, at the top of Rooms and spots, lists the places written on your plants with a suggested spot name for each. Change any names or areas, then press **Make these spots** to put those plants in them.

### Pots and trays

**Pots and trays** (under Care) keeps each kind of pot and catch tray you have:

- **Name**, **Shape** (circle, square or rectangle) and its sizes in inches: across for a circle, the side for a square, length and width for a rectangle, and the height (pots) or depth (trays).
- **Floor it covers**, worked out in square feet. A round one counts as the square around it.
- For pots, **Drainage holes** (a pot with none gets a reminder to water less).
- **Material**: terracotta, thin plastic, thick plastic, or **Other** to type your own.
- **How many you have**, typed straight in, with **3 / 5 in use, 2 free** beside it and links to the plants using them. More in use than you have is allowed and shown.
- **Photos**: **Add a photo** under the picture.
- **Add a pot** and **Add a catch tray** add a new one to fill in.

Choose a plant's **Pot** and **Catch tray** on its page. The Grow lights page then uses the real floor it takes: the tray's, or the pot's when it has no tray (the old Pot size guess otherwise).

### Editing on the page

On the light cards (Grow lights), Pots and trays, Rooms and spots, and the top of each plant's page (names, home, where, pot and tray, ID confidence, winter plan, health), type or choose a new value. It saves when you leave the box or press Enter. **Escape** puts back what was there before you started, and the message that follows has **Undo** (or press U). Notes and other long text have a small **Edit** button, so reading a page never changes it. **Edit this page** still has everything else. People who can only view see the values but cannot change them.

### Settings that follow you

These are saved for your sign-in as well as in the browser, so any device you sign in on picks them up: the Plants page filters, the Library's choices, the Mushrooms and Audit log filters, folded sections (such as Your lights), the weather chart choices, the Home button and Identify's list. On this computer (localhost) they are the owner's.

**Display** settings stay on each device, because a phone and a big monitor usually want different text sizes. Each part of Display (Text and colours, Page layout, Reading aloud, Photos and touch, Keyboard) has **Use these on every device I sign in on**. Tick it on each device that should share that part; the first one to tick it shares its settings, and the others take them. Your name on this computer, the offline copy and the device name always stay on the device.

## Homes, adding several plants, and your plant photos (from 1.28.0)

### Homes

Plants can live at more than one home: Round Rock, and Nevada City in California (added with this update). Each home has its own weather, frost warnings, watering and hardiness zone.

- **Every plant has a Home** (under Names and place when you edit it). Plants you already had are at the main home, Round Rock.
- **The Plants page** has a **Home** filter, and each card says which home the plant is at (⌂ Nevada City, CA). The Identify photo table and Previous / Next follow the same filter.
- **Choose a home with the Location button** to see its weather, frost warnings, watering and Back outside. Each of those only lists the plants at that home. A place where no plants live (one you only watch the weather for) shows the main home's plants, as before.
- **The Weather page's Places table** has a **Plants** column, and **Plants live here** or **No plants live here** for each place. A home with plants in it can't be removed or turned back into a weather-only place until its plants are moved.
- Hourly updates and backups still use the main home.

### Add several plants at once

**Add a plant** now starts with two buttons: **One plant** (the form, as before) and **Several plants from photos**.

1. Choose the home and the location (Outdoors, Indoors...) for the plants.
2. Choose all the photos at once. A photo of a plant's label or tag helps.
3. Press **Check these photos**. Each photo is checked by the picture checker on this computer, one at a time ("Checking photo 3 of 12").
4. **The review screen** shows one box per plant:
   - From 1.38.0, under each photo you say what it shows: **Same plant as the photo above**, **A different plant**, **Shows all of them** (a wide shot that goes on every plant) or **Leave this photo out**. The photos are in the order they were taken; the first guess is "same plant" when the picture checker sees the same species in both, and the plant boxes follow your answers. (The old "taken within 3 minutes" grouping is gone.)
   - **What the picture checker thinks it is**: the 3 likeliest species, with how likely each is. The names, family, genus, plant type, safety for pets and ID confidence are filled in from the one chosen. Choose another, or **None of these** to type them yourself. Anything you type is kept.
   - **This may be a plant you already have** appears when a plant looks like one in the record. It starts unticked, so it isn't added twice.
5. Press **Add N plants**. Nothing is added until then. Each plant gets its photos (the first is the main photo), and its page says where its name came from.

The care details (temperature, water, light...) start empty, as with one plant. Photos waiting on the review screen are kept for two days.

### Your plant photos (Identify page)

At the bottom of the Identify page, **Your plant photos** lists every plant, one row per plant, with its photos in a strip, its home and spot, and the date of its newest photo. These are the photos Identify compares your pictures with. Choose a plant or a photo to open its page. It has the same search and filters as the Plants page (changing them here changes them there), plus **Only plants with no photos**. It shows 30 plants at a time, with **Show more**.

### Not tied to Texas

From 1.28.0 the Library's lists, filters and tags, Identify's state list, and the question sent to Claude all follow the place chosen with the Location button. The cleaning-the-pot tip no longer mentions Central Texas, and the mushroom safety page points to a local mycological society anywhere. The written winter notes for Round Rock are still only used near Round Rock; other places use their own weather history. The wishlist's local nurseries are near Round Rock; the owner can add others under Shops.

## Offline use on phones and tablets (from 1.24.0)

The plant record works on a phone or tablet without a connection: out in the woods, in a basement, anywhere. Changes you make there are kept on the device and sent to the plant record as soon as it can be reached again.

**Setting up a device (once, while it's online):**

1. Open the plant record on the phone (through Tailscale, at your https://plants… address).
2. **iPhone or iPad:** in Safari, press Share, then **Add to Home Screen**, and from then on open it from the Home Screen. Safari clears what a site saved after a few weeks unless it's on the Home Screen. **Android:** in Chrome's menu choose **Install app** (or **Add to Home screen**).
3. Press the **Online** button at the top of the page. It opens **Offline use**.
4. Tick **Keep a copy on this device**. It saves every plant page, mushroom find, care log and photo (full size). The first time takes a few minutes. After that it saves again by itself whenever the copy is a few hours old and the device is online.
5. Give the device a name (for example "Ethan's phone"). The name shows on changes that came from it.
6. If you want the library offline too, tick **Also keep the library's download areas** (their plant lists and photos). The owner adds the areas under **Photos for offline use** on the Library page first.

**Without a connection:**

- The button at the top says **Offline**, and each page says it is showing what the device saved, and when.
- **You can:**
  - read every plant, mushroom find and photo;
  - log watering and care (with the day you did it);
  - edit plants, move them and archive them;
  - add photos;
  - add mushroom finds with photos (a new find gets a temporary code until it is sent; its location still comes from the photo);
  - use your notes, tags and wishlist;
  - search the saved download areas in the library.
- **Identify** keeps the picture and checks it when you're back online. The answer appears on the Offline use page.
- Things that need the computer (backups, settings, adding a new plant page, the weather update) say they need a connection.
- The top button counts the changes waiting ("Offline · 3 to send"). The Offline use page lists them, and you can take any of them back before they're sent.

**When the device can reach the plant record again**, the waiting changes are sent by themselves, in the order you made them. Each change is made only once, even if the connection drops halfway and it is sent again. Then:

- If someone changed **other** things on the same plant meanwhile, both are kept.
- If someone changed the **same** thing (say the pot) to something different, nothing is overwritten. Both versions wait on **Needs your decision** (the top button says "1 to decide"). There you see both side by side, who made each change, when and on which device, and press **Keep this** on the one you want. Owners and editors can decide.
- A change the plant record refused (for example, the plant was deleted meanwhile) stays on the Offline use page under **Could not be sent**, with the reason. You can **Try again** or **Remove it**.

Changes from a device are in the Audit log like any other, under the person's name. Clashes are listed under "Clashes between devices".

**Delete the saved copy on this device** (Offline use page) removes the copy from that device. Changes still waiting to be sent are kept.

## Mushroom finds (from 1.22.0)

**Mushrooms** in the top menu is a page of its own for the mushrooms you spot: in the yard, in a plant pot, or anywhere else. Each find gets a code, F-001, F-002 and so on.

**Adding a find.** Press **Add a find**.

- **Photos:** take photos of the cap from above, the underside (gills or pores), the whole stem and the very base. On a phone the button can open the camera. If a photo carries its location (most phone photos do, if location is on for the camera), the find gets that location.
- **Where and when:** the date, and whether it was in the yard, in a plant pot (then pick which plant) or somewhere else, plus a description. **Use my location now** asks the phone or browser for where you are. Locations are seen by everyone you have given access to the app.
- **What it grew on:** soil, mulch, dead wood, a living tree, potting mix and so on; trees nearby; how many.
- **What it looks like:** cap width and colour, gills or pores, a ring on the stem, a cup or sac at the base, spore print colour, colour change when cut, smell.
- **Name:** a common name or your own description, the scientific name, and how sure the name is: not identified yet, a guess, fairly sure, or confirmed by an expert.

Only the photos and the place really matter at first; you can fill in the rest any time with **Edit this find**.

**A find's page** shows its photos (**Previous photo** and **Next photo**, **Make this the main photo**, **Edit caption**, **Remove photo**), where and when (with a link to the map), and what you noted. **Identify the photo shown** compares the photo on screen with the 49,000 fungi, on this computer. **Use this name (as a guess)** saves a suggestion as the scientific name, marked "A guess". **Archive this find** takes it off the list without deleting it.

**The list of finds** can be searched and filtered by how sure the name is, where, and year. **Show** includes archived finds.

**Safety.** Every mushroom page has a short safety note, and **Read more** opens the full one. Never eat a wild mushroom because of an app, a photo, or this record. If a pet may have eaten one, call your vet or ASPCA Animal Poison Control at (888) 426-4435. If a person may have, call Poison Control at 1-800-222-1222 (or 911 if they are very ill).

Changes to finds are in the Audit log under "Mushroom finds", and the finds and their photos are in your backups like everything else.

## Undo right after a care button (from 1.19.0)

After you press **Watered** or **Still moist** (on the Today page or a plant page), **Watered all**, or save **Log other care**, the message at the bottom says what was saved and has **Undo** and **Close** buttons. It stays for 30 seconds, and says how long is left. The countdown pauses while the pointer or the keyboard focus is on the message. With a keyboard, press **U** while it shows (Display settings can turn keyboard shortcuts off).

Undo removes only the entries that press made, so the rest of the care log is untouched. For "Watered all" it removes all of them and says how many. If someone else already removed the entry, it says "Nothing to undo". The change log records it as "Undone right after it was logged". To remove an older entry, use the care log on the plant's page.

## Large-print care cards (from 1.19.0)

A printable card with a plant's needs in big type, to tape to a pot or shelf or keep beside the plants indoors, and read without opening the app.

- On a plant page, press **Large-print care card**. On a group's page, **Large-print care cards** makes one card for each plant in the group. On the **Labels** page, **Print care cards for all plants** makes one for every active plant (from 1.20.0).
- **Size** (from 1.20.0):
  - **4 × 6 inch card** (the usual choice): the plant's name, code and spot, its main photo and a code to scan that opens its page. Under that is one line each for **Water** (how often to check, the same figure as the Today list), **Light**, **Temp**, **Humidity**, **Feeding** and **Careful** (pets and people). It prints on 6 × 4 inch paper, turned sideways: choose 4 × 6 inch paper (or index cards) in the print window. Most plants fit on one card; a few with long wording run onto a second.
  - **Full page (Letter):** the same, plus the plant's winter plan and notes in boxes, with **Short** or **Full** notes.
- Under **Also show**, choose whether to show the photo, the scan code and the dangers to pets and people (on to start with). The choices are remembered in this browser. **Print** opens the browser's print window, where you can pick a printer or "Save as PDF".
- The printout is always black on white and large print. Nothing on it is smaller than about 16 point (from 1.20.0, the "Printed on" line and "Scan for the full page" are as big as the notes). The name is about 21 point on a card and 30 point on a page.
- People who can only view the app can print cards too.

## Grow lights (from 1.13.0)

The **Grow lights** page (in the top menu) holds your grow lights, the spots they light indoors, and how much light each plant gets there. Your 11 lights arrive with the update, from the photos and listings you saved in `Plants\Grow Lights`. Each has a photo, how many you have, its timer and brightness steps, and the maker's light figures. Where the maker gives none, Claude's estimates are used and marked.

How much light a plant gets is its **daily light (DLI)**, in mol/m² a day: the light at its leaves while the light is on (PAR, in µmol/m²/s) times the hours it is on. 100 PAR for 12 hours is about 4.3. Each plant page lists the range it wants, under Sunlight.

- **Light spots.** A spot is one of your lights over some plants: how many of that light side by side, how far it is from the top leaves, hours a day and brightness. Press **Set up a spot**. While you choose, the window shows the light at the leaves and says for every plant whether that is too dim, a bit dim, good, a bit bright or too bright. The setting is shown in words and with a symbol, not by colour alone.
- **Suggested layout.** For plants that live inside or are coming in and are not in a spot yet. Plants that need the most light are placed first. Each goes under the smallest of your lights that can give it enough, sharing a light with plants whose needs overlap, while there is room under it. Pot sizes count, if they are set. **Set up this spot** opens the suggestion so you can rename it (for example "Living room shelf") or change anything first.
- **No light left for these** lists the plants your lights cannot cover, with the reason.
- **Easing them in.** Under a spot, "Easing them in from outdoor light" gives a first and second week brighter and longer than the spot's own setting, so plants used to the sun do not drop their leaves all at once.
- **Timers.** Each spot says whether to use the light's own timer or a plug-in outlet timer. Some lights forget their timer after a power cut.
- **Your lights.** Press **Change this light** to note where it is (for a bulb, the lamp or socket it screws into), correct how many you have, or fix its figures. **Add a light** adds one you buy later. Type its figures as distance and PAR, for example "12 in 719, 24 in 234".
- **Plant pages** show the plant's spot, or what the suggested layout gives it, under Sunlight.
- **Rooms and shelves (from 1.13.1).** The rooms, shelves and tables where plants go inside. Yours are listed already: the Downstairs Living Room (Tall Black Shelf, Tall Brown Shelf, Short Brown Shelf, Large Brown Hutch, Side Table), My Bedroom (Shelves), the Garage and the Upstairs Living Room. Press **Add a room or shelf** to add more, for example each new bedroom shelf, and choose one under **Where** when you set up a light spot.
- **Manufacturer model (from 1.13.1).** Each light has a field for the model number on its box or label. Fill it in with **Change this light**. From 1.27.2, the Barrina standing light, the SANSI 80 W, 30 W and 10 W bulbs and the SANSI pot clip lights have theirs filled in from your label photos.

Changes to lights, spots, rooms and shelves appear in the audit log under "Grow lights". People who can only view see everything but cannot change it.

## About this plant (from 1.14.0)

Every plant page has an **About this plant** section after Identification (also in the jump row and the "On this page" menu):

- **Type of plant and classification:** for example "Evergreen tropical tree", then kingdom, order, family, genus and species.
- **Mature size:** a table of height and width in the ground and in a pot, plus growth rate and lifespan.
- **Hardiness zones (USDA):** the coldest and warmest zones it grows in outdoors all year, and a line saying **✓ Hardy here** or **▼ Not hardy here** with how much colder a usual winter is than the plant can take. Your zone comes from the weather history the app keeps for your place: the average of each winter's coldest night, which is how the USDA defines zones. For Round Rock that is about 22°F, zone 9a. The 2023 USDA map puts Round Rock on the line between 8b and 9a; the link opens the map so you can look up a ZIP code. Annual plants have no zone.
- **Native range, conservation status and invasive risk.** Conservation status is the IUCN Red List category where Claude could confirm one, and notes CITES (which only controls international trade, not growing a plant at home).
- **Flowers and fruit,** including whether the fruit is edible.
- **Dangers** to people and to pets, in a box with the Poison Control number (1-800-222-1222) and the ASPCA Animal Poison Control Center (888-426-4435).
- **Propagation,** as numbered steps.
- **Sources and further reading:** links to the pages the details came from. They open in a new tab.

If the identification is less than 85% sure, a note says the details are for the closest match. Change anything with **Edit**, under "About this plant". In the **Sources** field, put one source per line as `Title | https://link`, and it shows as a link.

## Uses, partners and propagation (from 1.27.0)

Every plant page has a section **Uses, partners and propagation** (the **Uses** button in the row of section buttons). Species pages in the Library have it too, and mushroom finds have **What it does, and growing it**.
- **Uses**: what people use it for (food, skin and first aid, dye, crafts, ground cover, cut flowers...), each with its safety warnings. Traditional uses are labelled as such and are not medical advice.
- **In the compost**: good, fine in small amounts, poor, or keep it out, and why.
- **Keeps away** and **Brings in**: pests or animals it deters, and the pollinators, birds and helpful insects it feeds.
- **Good partners** and **Keep apart from**: each with how sure it is ("shown in trials", "gardeners' lore, not proven", "same light, water and soil", or "needs different light, water or soil"). When you have a partner plant, it says **You have it** and links to it.
- **Propagation**: the ways to make more of it, and the best time of year here.
- **Breeding**: how it crosses, then links to **your plants of the same species** and **your plants it may cross with**. Patented varieties are flagged: propagating a patented plant isn't allowed while the patent lasts, even for yourself.

For your plants, Claude wrote these from general horticultural knowledge (upgrade batch A9, about 50 species, plus their genus for named hybrids). Nothing was checked by a person. For any other species, press **Write them with Claude** on its page. Like care sheets, it uses the owner's Anthropic key (saved on the Identify page) and keeps the result. For mushrooms, uses never include eating them.

## Audit log (from 1.10.0)

The **Audit log** page (in the menu bar; it used to be called Change log) lists every change to every record, newest first: edits to plant pages, plants added or archived, photos added, moved or removed, feeding and care, requests and answers, the "Still to photograph" list, settings and backups. Each change shows when, which plant (with a link), who, what changed, and the value before and after.

- **Filters** (at the top; on a phone, open **Filters** first):
  - **Search**: any words, a plant code, a name or a value, for example `hyacinth`, `P-024` or `Poor`.
  - **Plant**: one plant, or "Not about one plant" for settings, backups and the like.
  - **Who**: one person, "People" (everyone but Claude's updates) or "Claude's updates".
  - **Kind of change**: for example Photos, or Feeding, watering and care.
  - **Field**: one detail, such as Health rating or Location.
  - **From** and **To**: dates, in your time zone.
  - **Order**: newest or oldest first.
- The line under the filters says how many changes match, for example "Showing 1 to 100 of 2,253 changes". **Previous page** and **Next page** go through them 100 at a time.
- **Clear filters** shows everything again. This browser remembers the filters until you clear them.
- **Download these changes (CSV)** saves just the changes that match, for a spreadsheet.

### Debug button and the audit log console (from 1.10.0)

The **Debug** button sits next to **Display** at the bottom right of every page, and opens a window of tools for seeing what the app is doing:

- **Show the audit log console**: a small window at the bottom of the screen with the newest changes to any record. It checks for new ones every 3 seconds, so you can watch a change appear as you, someone else or an update makes it.
  - **Changes it shows before you scroll**: 3, 4 or 5. Scroll it up for older ones (it keeps the last 200), or click into it and use the arrow keys.
  - If you have scrolled up when a new change comes in, it stays where you are and shows a **new changes below** button instead of jumping.
  - **Pause** stops it checking until you press **Resume**. **Open the audit log** goes to the full page. **Close** turns it off.
- **Let screen readers announce each new change**: off to start with, so a screen reader is not interrupted every time something is saved.
- **About this browser and the app**: the version, window size, text size, layout and how many changes are logged.

These choices are remembered in that browser. The console never covers the Debug, Display or Sections buttons, and plant pages leave room for it.

## What's in the pages

- **Plants**: all pages, filterable by winter plan, health and ID confidence; sortable.
- **Today**: what to water, feed and answer today (see above).
- **A plant page**: names, ID confidence and what to send to raise it to 100% (with a "Copy this as a request for Claude" button), temperature strip showing 20, 32 and 38 F against the plant's limits, humidity, sunlight, winter steps, how to keep it comfortable when the weather cannot, health and steps to improve, photos, quick care buttons and the care log, the timeline, and the page history (version, date, who, what changed, before and after, restore).
- **Winter plan**: the 7-day forecast, expected versus tracked weather for October to March, when to act, every plant grouped by what it needs, and the cold-night checklist.
- **Weather**: forecast, charts, sensor connection and location (see above).
- **Fertilizer**: today's feed / hold / rest verdict for every plant, a calendar, and the feeding log (see above).
- **Identify** and **Library**: which plant the camera is pointing at, and every plant species by name (see "Identify a plant and the plant library").
- **Photos**: wide shots not yet tied to a plant, and a "still to photograph" checklist.
- **Labels**: printable QR labels.
- **Audit log**: every change to every record, with filters and CSV and JSON downloads (see "Audit log" above).

Editing a page saves a new version and keeps the old one. "Restore" puts an older version's text back as a new version (photos are not changed). Two people editing the same page at once: the second save is refused with a message, so nothing is overwritten.

## Your data and backups

Everything is in the `data` folder next to `docker-compose.yml`:

- `plants.db`: all records, versions and the change log
- `photos`: every photo
- `photos_deleted`: photos you removed (kept so you can recover them by hand)

### The Backups page (from 1.7.0)

Open **Backups** in the menu.

- **Back up now** makes a backup straight away. Add an optional note, and tick **Include the photos** if you want them too.
- **Automatic backups**: switch them on or off and choose:
  - how often: every 6 hours, every 12 hours, daily, every 3 days or weekly
  - the hour of day
  - how many automatic backups to keep (older automatic ones are deleted; backups you make yourself and the updater's backups are never deleted automatically)
  - whether to include the photos
- The **Your backups** list shows each backup with a Download and a Delete button.

Backups are zips named `plantdb-backup-YYYYMMDD-HHMMSS-<manual|auto|update>.zip`. Each holds `plants.db`, a `backup.json` describing it and, if chosen, a `photos` folder. They are saved in the `backups` folder next to `data`, so updates do not touch them. That folder is still on the same disk, so copy a few to another drive or cloud folder now and then.

The app must be running for automatic backups. If it was off when one was due, that backup runs within a few minutes of the next start.

### Restoring a backup

Stop the app, keep the current database under another name, put the backup's `plants.db` in its place, and start the app again. The example uses `plantdb-backup-20261021-030000-auto.zip`; use your file's name.

Windows (cmd.exe):

```
docker compose down
ren data\plants.db plants-old.db
tar -xf backups\plantdb-backup-20261021-030000-auto.zip -C data plants.db
docker compose up -d
```

If the backup has photos, also run `tar -xf backups\plantdb-backup-...zip -C data photos` before starting.

Windows (PowerShell):

```
docker compose down
Rename-Item data\plants.db plants-old.db
Expand-Archive backups\plantdb-backup-20261021-030000-auto.zip -DestinationPath restore-tmp
Copy-Item restore-tmp\plants.db data\plants.db
if (Test-Path restore-tmp\photos) { Copy-Item restore-tmp\photos\* data\photos -Recurse -Force }
Remove-Item restore-tmp -Recurse
docker compose up -d
```

macOS / Linux (bash):

```
docker compose down
mv data/plants.db data/plants-old.db
unzip -o backups/plantdb-backup-20261021-030000-auto.zip plants.db -d data
unzip -o backups/plantdb-backup-20261021-030000-auto.zip 'photos/*' -d data   # only if it has photos
docker compose up -d
```

Once the restored data looks right, you can delete `data\plants-old.db`.

### Copying the whole data folder by hand

Windows (cmd.exe):

```
docker compose stop
xcopy data data-backup /E /I /Y
docker compose start
```

Windows (PowerShell):

```
docker compose stop
New-Item -ItemType Directory -Force data-backup | Out-Null
Copy-Item data\* data-backup -Recurse -Force
docker compose start
```

macOS / Linux (bash):

```
docker compose stop
cp -r data data-backup
docker compose start
```

You can also download everything from **Audit log**: plants as CSV, the change log as CSV, or all data as JSON. To start over with the original 77 plants, stop the app, delete the contents of `data`, and start it again.

## Notes

- Photos are re-saved when uploaded (JPG, max 1600 px). Location data in the photo is removed. iPhone HEIC files are not supported; use JPG or set the phone camera to "Most Compatible".
- Plant IDs are Claude's best reading of the photos. Low-confidence plants say what would settle it.
- Fonts (Spectral, Atkinson Hyperlegible) are bundled under the SIL Open Font License; nothing loads from the internet.
- "Expected" weather figures are climate averages for Round Rock / Austin; the sources are listed on the Winter plan page. Tracked figures come from Open-Meteo and your sensor.
- Plant pages and the Display settings were designed for low vision: large type, high contrast, roomy spacing and no tiny tap targets. If something is still hard to read, tell Claude which page and what size and it will be changed.
