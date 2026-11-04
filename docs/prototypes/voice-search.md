# Prototype: search by voice

Branch: `proto/voice-search`

## What it does and why
Typing a plant name into a small search box is slow when the text is hard to see, and long names like "Philodendron 'Pink Princess'" are easy to mistype. Now every search box has a **Search by voice** button beside it. Press it, say what you are looking for, and the app puts the words in the box and searches.

- The button is beside the search box on:
  - the Plants page, and the "Filters for Previous / Next" on plant pages
  - the Identify page (Your plant photos)
  - the Library
  - Mushrooms
  - the Audit log
  - "Find a plant" in the long plant lists inside group windows
- While it listens, the button is filled in and says **Listening. Press to stop**. Press it again to stop.
- The line under the button says what it heard and how many plants match, for example: *Heard "monstera". 4 plants match.* Screen readers read this line out too.
- **Plant codes are tidied up.** "P 36", "pea zero three six" and "P036" all become **P-036**. "F 2" becomes the mushroom find **F-002**.
- **Extra words are dropped.** "Show me the monstera plants" searches for **monstera**.
- **"Open ..." opens the plant.** Say "Open P 6" (or "Open pink princess") and, when exactly one plant matches, its page opens. When several match, the list is filtered and the line under the button says to say one of their codes.
- **Keyboard shortcut V.** Press V anywhere (except while typing in a box) to start listening for the search on that page. V is in the shortcuts list (press ?), and it is off when Display settings turn shortcuts off.
- If something goes wrong, the line under the button says what to do, in plain words:
  - the browser was not allowed to use the microphone (with where to allow it)
  - no microphone was found
  - nothing was heard
  - the speech service could not be reached
- Viewers can use it too, because it only searches and changes nothing.

### Which browsers
It uses the speech recognition built into the browser. Nothing is sent by the app itself.
- **Chrome and Edge** (Windows and Android) work. They send the sound to Google or Microsoft to turn it into words, so they need the internet.
- **Safari** on iPhone and iPad works. Apple may do this on the device or on its servers.
- **Firefox** has no speech recognition, so no button appears there.

The first time, the browser asks whether Plant record may use the microphone. Say Allow.

## How it looks
Plants page on a laptop, while listening, and after hearing "p 6":

![Listening](voice-search/laptop-listening.png)

![After hearing "p 6"](voice-search/laptop-heard.png)

On a phone, light and dark. On narrow screens the button sits right under the search box, the full width of the screen:

![Phone, light](voice-search/phone-light.png) ![Phone, dark](voice-search/phone-dark.png)

On a phone with the largest text size:

![Phone, largest text](voice-search/phone-bigtext.png)

## How to try it
1. Open the Plants page.
2. Press **Search by voice** (or press V).
3. Allow the microphone if the browser asks.
4. Say a plant name or code.

## What it changes in your database
Nothing. There are no new tables, columns or settings.

The only server change is one header: the app now tells the browser that its own pages may use the microphone (`microphone=(self)` in `Permissions-Policy`). Before, it blocked the microphone everywhere.

## For developers
- `app.js`, block "search by voice", after the keyboard shortcuts block:
  - `vsAdd()` runs from a `MutationObserver` on `#app` and `#dlg`. It puts a `.vs-wrap` (button with `data-act="vsearch"`, plus a `role=status` line) after the `<label>` of every `input[type=search]`, but only when `SpeechRecognition` or `webkitSpeechRecognition` exists.
  - `vsStart()` / `vsFinish()` fill the box and send an `input` event, so each page's own search code runs unchanged.
  - `vsClean()` tidies what was heard. It is exposed as `window.PlantVoice.clean` for the test.
  - The V key has its own `keydown` listener. The act is registered with `queueMicrotask`, because `acts` is declared further down.
- `style.css`: a "proto/voice-search" block before the 1.16.0 groups block.
- `server.py`: `Permissions-Policy` allows the microphone for the app's own pages.
- Test: `dev/test/voice_check.py` (a stand-in speech recogniser).

## Open questions for Ethan
1. Should the line under the button also be **read aloud** with the Read aloud voice, so you hear what it understood without looking? Screen readers already read it.
2. Should "Open ..." also work for **pages**, for example "Open weather" or "Open Today"?
3. Would you like a **Display setting** to hide the voice buttons, if you don't use them?
4. Chrome and Edge send the sound to Google or Microsoft. Is that all right, or should the button carry a short note saying so?
