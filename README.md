# Wandawega 2026 Ping-Pong Tournament

A mobile-first, single-page web app for running a company ping-pong tournament. Anyone with the URL can sign up; an admin generates a randomized single-elimination bracket and records winners by tapping. Every device viewing the page sees the live bracket update within a second via Firebase Realtime Database.

The entire app is a single `index.html` file. No build step, no server, no dependencies beyond the Firebase compat SDK loaded from `gstatic.com`.

## Features

- **Sign up** — anyone with the URL adds their name. Firebase transactions prevent duplicates and race conditions.
- **Bracket** — Fisher–Yates shuffle for seeding, padded to the next power of two with byes that auto-advance.
- **Admin** — passcode-protected. Generate bracket, record winners by tap, reset bracket, remove players, change passcode.
- **Live sync** — every action propagates to all viewers via `onValue` listeners.
- **Mobile-first** — dark theme, large touch targets, single column.

## Setup

### 1. Firebase project

Create a free Firebase project at <https://console.firebase.google.com>, then:

1. **Add a Web app** to the project. Copy the config object.
2. **Enable Realtime Database** (not Firestore). Pick a region. For development, start in **test mode** (open read/write for 30 days). Tighten before public exposure — see "Production database rules" below.
3. **Paste the config block** into `index.html` between the `FIREBASE_CONFIG_START` / `FIREBASE_CONFIG_END` markers. The `apiKey` here is a public project identifier, not a secret — security is enforced by database rules.

The connection pill in the header reads **Live** (green) when the page is connected.

### 2. Local testing

Open `index.html` directly in a browser, or serve it with any static server:

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

## Deploy to GitHub Pages

This repo is wired up for Pages. After pushing `index.html`:

1. Go to repo **Settings → Pages**.
2. Under **Source**, choose **Deploy from a branch**.
3. Pick branch `main` (or whatever branch holds `index.html`) and folder `/ (root)`. Save.
4. Wait ~30 seconds. The URL appears at the top of the Pages settings page — typically `https://<user>.github.io/<repo>/`.

That's it. Subsequent pushes to the chosen branch redeploy automatically.

## Other hosting options

- **Firebase Hosting** — enable Hosting in the Firebase console, then `firebase deploy` from a machine with the Firebase CLI installed. Gives `<project-id>.web.app`.
- **Netlify Drop / Vercel / Cloudflare Pages** — drag `index.html` onto their drop pages. All require an account.

## Production database rules

Test-mode rules expire after 30 days and allow anyone to read or write anything. Before the tournament, replace the rules in Firebase Console → Realtime Database → Rules with:

```json
{
  "rules": {
    "players": {
      ".read": true,
      ".write": true,
      "$pid": {
        ".validate": "newData.hasChildren(['name','addedAt']) && newData.child('name').isString() && newData.child('name').val().length <= 40"
      }
    },
    "bracket": {
      ".read": true,
      ".write": true
    },
    "settings": {
      ".read": true,
      ".write": true
    }
  }
}
```

Open write is fine for a low-stakes internal tournament — the admin passcode lives in the database, so anyone with the URL could in theory poke at it. If that matters, switch to Firebase Authentication and gate writes on `auth != null` for `bracket` and `settings`.

## Day-of checklist

- [ ] Firebase config pasted into `index.html` and committed.
- [ ] Database rules tightened (no longer in test mode).
- [ ] Admin passcode changed from the default `pingpong2026` (Admin tab → Settings).
- [ ] Public URL printed on a poster with a QR code.

## Customization tips

- **Theme color** — edit the CSS custom properties in `:root` near the top of `index.html` (`--accent` for the gold highlight).
- **Title** — change the `<title>` and the `<h1>` in the header.
- **Match format** — currently single-elimination only. Double-elimination, round-robin, or pools would require a different bracket generator.

## Files

- `index.html` — the app.
- `README.md` — this file.
