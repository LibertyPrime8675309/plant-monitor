# Reporting a problem, the Issue tracker and checking for updates

Part of the Plant record manual. The README in the folder above has how to start, stop, update and back up the app, and the list of every manual page.

## Report a problem (from 1.58.0)

When something goes wrong, looks odd or could be better, you can say so from the page you are on, on any device, without having to remember the details later.

**Where the button is:**

- At the foot of the **Navigation** menu on every page, above Display.
- On **Settings**, on the card **Problems and ideas**.
- On a computer, some pages have no Navigation menu: All plants, Add plants, Mushrooms, Year in review, Offline decisions, the Audit log and the Issue tracker. There it is at the **foot of the page**, and as **Report** in the top bar beside Display when the bar has room.
- At the largest text sizes on a phone, the button comes after the list of sections in Navigation (scroll the list to its end). So the list keeps its room.

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

Above the cards:

- **Show**: Open and being looked at, to start with; or one status; or All.
- **Search the reports**: their words, names, devices, pages and your notes.
- **Report a problem**, and **Copy the ones shown for Claude**.



Reports stay in your plant record: they are in every backup, and their pictures are in every backup that includes photos. Nothing sends them anywhere else. Copied text names the account that sent the report, so paste it only where you mean to.

## Check for updates (from 1.58.0)

A phone, tablet or computer that has had the app open since before an update can go on showing the old version. From 1.56.5 the app notices this by itself the next time it talks to the plant server, and reloads once (or shows **Reload now** if you are typing). **Check for updates** is for when you want to ask yourself.

**Where the button is:** beside the version number at the top of **Settings**, and at the foot of **Navigation** beside Report a problem. On a page with no Navigation, it is at the foot of the page.

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
