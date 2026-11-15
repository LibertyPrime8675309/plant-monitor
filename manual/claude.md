# Working with Claude

Part of the Plant record manual. The README in the folder above has how to start, stop, update and back up the app, and the list of every manual page.

## What Claude needs from you

When Claude needs something to finish a plant's page (a check, a question, a photo or ID details), it is listed at the top of that plant's page under **Needed from you**, with **Answer** and **Mark done** buttons. Answers are kept on the page and in the change log. To send them to Claude, use **Copy my answers for Claude** (below). On the **Plants** page, **Show plants that need something from you** filters to just those plants; plants whose identification is under 70% sure are included, with what would help. Things to photograph that are not in the database yet are on the **Photos** page.

### Copy my answers for Claude (from 1.8.0)

**Copy my answers for Claude** is on the Plants page (it says how many answers are new, for example "(2 new)") and in "Needed from you" on each plant page. It puts everything you have done since you last copied into one message: your answers first, then changes to plant pages, photos added, feeding and care, and the "Still to photograph" list. Press **Copy message**, then paste it into your chat with Claude (Ctrl+V). **Save as a text file** puts the same message in your Downloads folder instead.

Next time it starts from where the last copy ended, so nothing is sent twice. **What to include** can also be "The last 7 days", "The last 30 days" or "Everything", and **Also list what is still open** adds the open requests and photos, which helps when you start a new chat. Photos themselves can't go in the message, so attach any you want Claude to look at.

## Updates from Claude (from 1.58.0)

When Claude has corrections, photos or new pages for your plants, it saves one small file on this computer and tells you its name. You look through the changes and decide. Nothing is changed until you press the button.

**Where the file goes.** Claude saves it in the folder `plant-updates`, inside your `plant-database` folder (beside `data` and `backups`). Its name starts with `plant-updates` and ends in `.json`, or `.zip` when photos come with it. The app only reads that folder. The files hold details of your plants, so they stay on this computer: they are not in a release and not on GitHub.

**Today tells you.** While a file is waiting, Today has a line near the top: "Plant updates from Claude are waiting", with the file's name, how many changes it holds, and **Look at the changes**.

**The page.** **Updates from Claude** is in the Plants menu. Opening a file shows:

- The file's name, the day it was made, and Claude's note about it.
- Every plant in one block, with its picture and its changes. Each change says what the page says **now**, what it would **change to**, and **why**.
- A tick box on each change, ticked to begin with. Untick a change to leave it out. **Tick every change** and **Untick every change** do them all.
- **Needs your decision:** a change to something that no longer says what the file expected, so it may be an edit you made yourself. It stays as it is unless you choose **Change it to Claude's**. A new page for a name your record already has needs a decision too.
- **Nothing to do:** the page already says it. **Left out:** the plant in the file is not in your record under that code and name, or the change is not one a file can make. Each says why.
- **Make the N changes** makes the ticked changes, all together. **Change nothing** sets the file aside.

**What a file can hold:** a change to something on a plant's page, a plant to move to the archive, a question for you (it joins **Needed from you** on that plant's page), photos for a page you already have, and a new page, with its photos. Photos are shown small with their captions in words; they join the page's photos, and the page's main picture stays as it is. A new page is made at your main home unless the file names another of your homes, and when you have more than one home the page says which ("Indoors, at Baraboo, WI"). A file that names a home your record does not have leaves that page out.

**Afterwards.** The page lists what changed and what was left. Each change is in the plant's **Page history** and in the Audit log, signed "Claude" with the file's name, with the reason and your name as the one who accepted it. To take one back, open the plant's page, then Page history, and restore the version before it.

**Once.** A file is brought in once. Opening it again shows what it did. A file you set aside is listed under **Files you brought in before**; **Look at it again** brings it back while it is still in the folder. You can delete files from the `plant-updates` folder whenever you like.

**A file kept somewhere else.** On the page, **Choose a file** takes an update file from anywhere on the computer.

Only the owner sees this page, the files and Today's line.
