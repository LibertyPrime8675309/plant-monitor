Tailscale for Plant record (from version 1.12.0)

config\serve.json  tells Tailscale to answer https://plants.<your-tailnet>.ts.net and pass each visit to the app,
                   with the visitor's Tailscale name. Funnel (opening it to the whole internet) is switched off here.
state\             is created on first start and holds this device's Tailscale sign-in. Keep it private: do not share it,
                   and do not put it in a zip. If you delete it, run "Set Up Remote Access" again to sign in.

To set up or check: tools\Set Up Remote Access.cmd (see README, "Using the app away from home").
