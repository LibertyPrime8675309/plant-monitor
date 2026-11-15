# Reporting a problem, the Issue tracker, checking for updates and the test copy

Part of the Plant record manual. The README in the folder above has how to start, stop, update and back up the app, and the list of every manual page.

## Report a problem (from 1.58.0)

When something goes wrong, looks odd or could be better, you can say so from the page you are on, on any device, without having to remember the details later.

**Where the button is:**

- At the foot of the **Navigation** menu on every page, above Display.
- On **Settings**, on the card **Problems and ideas**.
- On a computer, a page with no Navigation menu (All plants, Add plants, Mushrooms, Year in review, Offline decisions, the Audit log, the Issue tracker) has it at the **foot of the page**, and as **Report** in the top bar beside Display when the bar has room.
- At the largest text sizes on a phone, the button comes after the list of sections in Navigation (scroll the list to its end), so the list keeps its room.

**The window:**

1. **What happened?** Write it in your own words. The line under the label says which page and section the report is about.
2. **Pictures or screenshots.** You can leave this empty. Up to 4.
3. **This device is called.** A browser cannot read a device's own name, so type one the first time ("Ethan's iPad mini"). The device remembers it for every later report. It is the same name as **This device's name** on the Offline page.
4. **Everything that is sent with it.** Open this fold to read every detail before you send.
5. **Send the report**, or **Cancel**.

**What a report carries, besides your words and pictures:**

| Detail | Why it helps |
|---|---|
| The version of the app on that device, and the version the plant server was running | A device can be left showing an older version than the server |
| The page and the section you were on | So nobody has to ask where it happened |
| The account, its role, and whether it came through Tailscale | Who to ask, and what they are allowed to do |
| The device's name, kind, browser, screen and window size, text size, touch or not | Most layout problems belong to one size of screen or text |
| Home Screen app or browser tab; online or showing a saved copy; changes waiting to be sent | Most "it would not update" problems are one of these |
| Your Display settings and the other settings kept on that device | High contrast, theme, text size, units and the rest |
| The last pages opened and how long they took; the last errors the app showed | Often the whole answer |

Everyone who can open the app can send a report, people who can only view included. A report changes nothing about your plants.

**Without a connection** the report waits on the device with your other changes (the Offline page lists it as "A problem report") and is sent when the plant server can be reached.

## The Issue tracker (from 1.58.0)

**Settings, Issue tracker** (in the row of pages under the top bar), or **Open the Issue tracker** on the Settings card. Only the owner can open it, and only the owner can see a report's pictures. Today shows one line when a report from someone else has arrived that you have not looked at; opening the page clears it.

Each report is a card, newest first:

- **Who and where:** the time, who sent it, their role, the device, and the page as a link you can press to go there.
- **Their words and pictures.** Press a picture to open it at full size.
- **Tags:** its status; **Device was on X, server on Y** when the device was showing an older version than the server; how many pictures.
- **Device, versions and settings:** a fold with everything the report carried.
- **Status:** Open, Being looked at, Fixed or Closed. With Fixed, a box appears for the version it was fixed in (three numbers, like 1.58.0).
- **Your notes:** only you see them. They are saved when you leave the box.
- **Copy for Claude:** copies the whole report as text (not its pictures: attach those in the chat yourself).
- **Remove:** asks first, then deletes the report, your notes and its pictures. To keep a report out of the way without losing it, set it to Fixed or Closed.

Above the cards: **Show** (Open and being looked at, to start with; or one status; or All), **Search the reports** (their words, names, devices, pages, your notes), **Report a problem**, and **Copy the ones shown for Claude**.

Reports stay in your plant record: they are in every backup, and their pictures are in every backup that includes photos. Nothing sends them anywhere else. Copied text names the account that sent the report, so paste it only where you mean to.

## Check for updates (from 1.58.0)

A phone, tablet or computer that has had the app open since before an update can go on showing the old version. From 1.56.5 the app notices this by itself the next time it talks to the plant server, and reloads once (or shows **Reload now** if you are typing). **Check for updates** is for when you want to ask yourself.

**Where the button is:** beside the version number at the top of **Settings**, and at the foot of **Navigation** beside Report a problem (on a page with no Navigation, at the foot of the page).

**What the window says:**

- **This device is showing:** the version of the app this device has loaded.
- **The plant server is running:** asked at that moment, past every saved copy.
- **The newest release** (the owner only): GitHub is asked at that moment.

Then one of:

- **This device is up to date.**
- **This device is behind.** Press **Reload the app to open version …**.
- **The plant server did not answer.** The device is offline, or the PC is asleep or off. Reloading would only open the saved copy.

For the owner, **An update is ready** means a newer release is waiting to be installed on the PC with the updater (`Update Plant Database.cmd`), as Today also says.

**Reload the app** is always in the window. A Home Screen app on an iPad or iPhone has no reload button of its own, so this is it. (The other way is to close the app in the app switcher and open it again.)

## Try a newer version in a test copy (from 1.58.0)

The **test copy** is a second Plant record beside your real one, for trying the newest work before it is released. It has its own folder (`plant-database-test`, next to `plant-database`), its own containers and its own copy of your data, and it answers at <http://localhost:8090>. Nothing you do there reaches your real Plant record. It sends no notifications, makes no backups (and so sends none to the second backup folder or another PC), does not check shops or ask about updates, and is not on Tailscale, so only this computer can open it. Every page in it says **Test copy**, and its browser tabs start with **TEST COPY**, so the two are never mixed up.

Three files next to `Update Plant Database.cmd` look after it (the updater puts them there):

- **Start Test Copy.cmd**: the first time, it fetches the newest work from GitHub (what has been merged since the last release), copies your data into the test copy, starts it and opens it. After that, it starts it again and opens it.
- **Refresh Test Copy.cmd**: asks which version to try. Press Enter for the newest work, type a pull request number (such as `136`) to try something not merged yet, or a release (such as `1.57.0`). It then asks whether to copy your data again; the answer starts as No, so what you did in the test copy stays. A pull request is built on your PC, which takes a few minutes; the others are fetched ready-built.
- **Stop Test Copy.cmd**: stops it. Your real Plant record keeps running.

**Copying your data stops your real Plant record for about a minute**, so the copy is never taken halfway through a change. It asks first. The Identify model (about 5 GB) is not copied, so Identify is off in the test copy; add `-Identify` to copy it and turn it on.

The updater never touches the test copy (a file named `TEST-COPY.txt` in its folder says what it is). To be rid of it, press Stop Test Copy and delete the `plant-database-test` folder.

The same from a terminal in the Plants folder:

Windows (cmd.exe):

```
powershell -ExecutionPolicy Bypass -File test-copy.ps1 -Action Refresh -Source 136 -NewData
```

Windows (PowerShell):

```
powershell -ExecutionPolicy Bypass -File .\test-copy.ps1 -Action Refresh -Source 136 -NewData
```

macOS / Linux (bash), with PowerShell 7 installed:

```
pwsh ./test-copy.ps1 -Action Refresh -Source 136 -NewData
```
