# Away from home, on the phone and offline

Part of the Plant record manual. The README in the folder above has how to start, stop, update and back up the app, and the list of every manual page.

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

### Sharing it with someone

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

The app itself checks every request. So hiding a button is only a convenience: a change someone isn't allowed to make is refused even if they try it another way. The audit log shows each change under the Tailscale name of the person who made it. You can change the name shown for you in the same window.

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

### The names this computer answers to (from 1.58.0)

On this computer's own address (`http://localhost:8080`) the app treats everyone as you, the owner. So that a web page from somewhere else cannot reach it through your browser by giving 127.0.0.1 a name of its own, the app answers there only to:

- `localhost`, and number addresses such as `127.0.0.1` or `192.168.1.20`;
- a single-word name, such as your PC's name on the home network, and names ending in `.local`, `.lan`, `.home`, `.home.arpa`, `.internal`, `.localhost` or `.test`;
- the address saved for labels, and the public address saved for the calendar.

Any other name gets a short page saying so. People who come in through Tailscale are not affected: they are let in by who they are. If you reach this computer's port under a name of your own with dots in it (through your own proxy, say), list it in `.env` and restart (several names: separate them with commas):

- Windows (cmd.exe): `(echo PLANTDB_HOSTS=plants.myhouse.example)>>.env` then `docker compose up -d`
- Windows (PowerShell): `Add-Content .env 'PLANTDB_HOSTS=plants.myhouse.example'; docker compose up -d`
- bash: `echo 'PLANTDB_HOSTS=plants.myhouse.example' >> .env && docker compose up -d`

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

## On the phone and offline (from 1.38.0)

### Watering offline

On the Today page without a connection, **Watered** and **Still moist** now take the plant off the list at once. The plant's care log shows the entry as "not sent yet". The plant server gets it when it can be reached again (the entry then loses its "not sent yet" and gains its Remove button).

The same goes for the other everyday changes:

- "Log other care", and Remove on a care entry
- Moved indoors and Covered on the cold-night list, and Fed
- answers to Claude's requests, and the Still-to-photograph ticks
- photo captions, the main photo and removing a photo
- the porch reminder, the wishlist and species notes

 Each shows on its page at once and goes to the server later. A photo added offline shows as a thumbnail in the "Not sent yet" line on the plant's page. Settings, rooms and spots, lights, groups, stores, backups and sensors still need a connection (they are things you do at the PC).

### When Tailscale comes back

The app now tells apart "this phone has no network" from "the plant server cannot be reached" (Tailscale off, or the computer asleep): both show as **Offline** at the top. While the server is out of reach the app tries again every 30 seconds, whenever you bring it to the front, and when the network comes back. The offline note on every page and the Offline use page have a **Try to connect now** button as well. When the server answers, the waiting changes are sent and the page is drawn again from the server (unless you are in the middle of a form). No relaunch needed.

### Back goes back to where you were

Going back to a page (the phone's Back button, or a "Back to…" link) returns to the same place on it. A link to a new page starts at the top. Photo boxes have their size before the photo arrives, so pages no longer jump as photos load.

### Photos on the Add a plant form

**Add a plant** (one plant) has a **Photos** field: take them now or choose them from the phone's photos. The first becomes the main photo. **Fill in the names from the first photo** asks the picture checker and fills in the empty name fields. On Identify and on the plant page, "Choose a photo" / "Add photos" no longer forces the camera open: the phone offers its photos too.

### Adding a plant without a connection

Without a connection, saving the Add a plant form keeps the plant on this device (with a NEW- code) and sends it when the server can be reached. With a photo, the common name may stay empty: a stand-in name ("New plant, date") is used. Once the plant is sent, its first photo is checked by the picture checker and the Offline use page shows what it looks like, with a button to **put the first name on** the plant. The Plants page says how many new plants are waiting.

### Several plants from photos, on a phone

The review screen makes small previews of the photos on the phone itself (about 800 px), so it no longer shows white patches while scrolling. See "Add several plants at once" below for the new per-photo questions and the wide shot that goes on every plant.

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

## Photos from your phone, the year in review, and the mirror (from 1.37.0)

### Share a photo from your phone

On an Android phone with the app added to the Home Screen (Chrome or Edge: menu → Add to Home screen), **Plants** appears in the phone's share sheet. Share a photo (or several) from the camera or gallery and choose Plants. The app opens on **Photos shared with Plant record**. It shows the pictures, a plant to choose (recently changed ones first) and a caption. **Add** puts them on that plant, or under Photos to assign later. iPhones do not offer this for web apps. There, use the camera button on the plant's page as before. The Photos page has a link to the shared-photos page too.

### The year in review

**Plants → Year in review** (`#/review`): one card per plant for a year, from everything the app logged. Each card shows:

- whether it is new this year or archived, and how its health went
- its moves between places, waterings and feedings
- how many cold nights it sat outside below its damage point, and how many days at or above its heat-damage temperature
- the requests answered, and its first and last photo of the year

 The plants with the hardest year come first (■), those that got better are marked ✓. Choose the year, narrow the list (hard year, got better, new, quiet) and print it. Good for deciding what to keep, what to move and what to let go.

### The mirror: a read-only copy on another machine

The `mirror` folder in the app folder sets up a second copy of the app on another machine, such as the spare hardware or a family member's PC. It runs the same app with the backup receiver. It takes the newest backup every 5 minutes and shows it, read-only, at `https://plants-mirror.<your tailnet>.ts.net`. Every page on the mirror says which backup it shows and links to the main app; changes are refused. `mirror/README.md` has the steps (cmd.exe, PowerShell and bash). Photos on the mirror come from the last backup made with photos, so set the Backups page to include photos now and then.

## Notifications, a second copy of backups, and search (from 1.33.0)

### Notifications

**Settings, Notifications.** Press **Turn on for this device** on each phone or computer that should get messages (the browser asks for permission once). On an iPhone or iPad, add the app to the Home Screen first (Share, then Add to Home Screen) and open it from there. Then tick which kinds reach you; the choices are your own, saved for your sign-in, and apply to every device you turned on:

- **Cold nights:** when a cold night comes into the forecast, and a reminder at about 3 pm the day before it.
- **Shopping alerts:** a price at or under your limit, or something back in stock.
- **Watering and feeding due:** one message at about 8 am with what is due today.
- **Requests from Claude:** when a release adds a request (a photo or an answer Claude needs).

Cold nights and what is due are for the home you start on (People, Starts on). **Send a test** checks a device. Messages go through the browser's own push service (Google's for Chrome, Apple's for Safari). Only the title and a line of text are sent, encrypted for that device. Notifications need the app's Tailscale address (https) or this computer itself.

### Second copy of backups

**Backups, Second copy.** Each new backup is copied as soon as it is made:

- **Another drive:** to the folder named by `PLANTDB_COPY_DIR` in the `.env` file next to `docker-compose.yml` (for example `PLANTDB_COPY_DIR=D:\PlantBackups`), after `docker compose up -d`. Until that is set, copies go to `backups-copy` next to the data folder, which is the same drive and protects nothing if that drive fails. The newest 10 are kept. To set it (use your own folder; make the folder first):
  - Windows (cmd.exe): `(echo PLANTDB_COPY_DIR=D:\PlantBackups)>>.env` then `docker compose up -d`
  - Windows (PowerShell): `Add-Content .env 'PLANTDB_COPY_DIR=D:\PlantBackups'; docker compose up -d`
  - bash: `echo 'PLANTDB_COPY_DIR=/mnt/backups/plants' >> .env && docker compose up -d`
- **Another computer:** run the receiver from the `receiver` folder of the release on it (its README has the steps: Docker, a token, Tailscale), then type its address and token on the Backups page. The newest 20 are kept there.

**Copy the newest backup now** tries both. What happened last shows under the form, and failures go on the Problems list.

From 1.58.0 the app says so when every copy is on the record's own drive, with no folder named in `PLANTDB_COPY_DIR` and no other computer set. It says so at the top of the Backups page, on the Health card on Settings, and in one line on Today for the owner. Before 1.58.0 the Health card showed a tick for the `backups-copy` folder, and the Backups page could not see `PLANTDB_COPY_DIR` even when it was set.

### Search everywhere

The **Search** button in the top bar, or the `/` key anywhere, opens a search. It looks through plants (code, names, where they are, notes), pages, groups, rooms and spots, stores, mushroom finds, Shopping items and species in the library. Results are grouped; the arrow keys move through them and Enter opens one.
