# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository overview

Static GitHub Pages site for **海鮮餃子 北京 (Kaisen Gyoza Pekin)**, a Chinese restaurant in Hirakata, Osaka. Served from the `gyozapekin.github.io` repo and reachable at gyozapekin.com. A `.nojekyll` file is present so GitHub Pages serves files verbatim (no Jekyll build).

**Primary language of UI, comments, commit messages, and user-facing copy is Japanese.** Preserve existing Japanese strings when editing and match the existing tone in new copy.

There is no build system, no package manager, no test suite, and no linter. You edit HTML/CSS/JS files directly and commit. To preview locally, open the `.html` files in a browser or run a trivial static server (e.g. `python3 -m http.server`) from the repo root.

## Top-level structure

- Public marketing pages at repo root: `index.html`, `menu.html`, `about.html`, `order.html`, `howto.html`, `blog.html`, `gallery.html`, `contact.html`, `shift.html`. Each has its own copy of the `<header>`, `<nav>`, and `<footer>` — there is no template system, so navigation/footer changes must be duplicated across all pages.
- `css/style.css` — single shared stylesheet for the marketing pages. The shift app under `shift/` uses its own inline `<style>` blocks and does not depend on it.
- `images/gallery/YYYYQn/` — quarterly photo directories referenced by `gallery.html` and the `index.html` slideshow. When adding a photo, both the file and an `<img>` tag must be added.
- `shift/` — self-contained staff scheduling web app (see below). Linked from the public site via `shift.html`, but in production the shift app is served from the `shift.gyozapekin.com` subdomain.
- `robots.txt`, `.nojekyll` — GitHub Pages plumbing.

## The shift scheduler (`shift/`)

This is the most substantial code in the repo and where most development happens. It is a client-side-only SPA-like app split across four HTML files, each containing its own CSS and JS (no shared modules, no bundler).

- `shift/index.html` — login screen. Reads user records from `localStorage` / Firebase and sets a `sessionStorage.pekin_session` with an 8-hour expiry, then redirects to `admin.html` or `staff.html` based on role.
- `shift/admin.html` (~2100 lines) — manager console. Tabs: shift edit, overview, availability, staff, settings, template.
- `shift/staff.html` — staff availability input + read-only shift view + account/password.
- `shift/pekin_shift.html` — older/alternative single-page implementation. `admin.html` and `staff.html` are the active pages; treat `pekin_shift.html` as legacy unless a task specifically targets it.
- `shift/db.json` — snapshot of all shift data used as a fallback when Firebase is unreachable. It is served as a normal static file; the app fetches `/shift/db.json` with a cache-buster.

### Data model and storage

All state lives in `localStorage` under these keys (the `_STATIC_KEYS` constant lists the config-like ones):

- `pekin_users` — array of user records `{id, name, username, password, role, type, customPassword?}`. `role` is `'admin'` or `'staff'`; `type` is `'admin'|'part'|'fixed'|'free'|'alt'`. Defaults are hard-coded in both `index.html` and `admin.html` — if you change the default roster, update **both** copies.
- `pekin_settings` — `{defaultClosedDays:[dow...], specialDates:{'YYYY-MM-DD':{type,label}}}` where `type` is `'holiday'|'closed'|'other'|'open'`. `'open'` is a *force-open override* for a regularly-closed day, not a closed marker; `isClosedDay()` / `getClosedInfo()` in `admin.html` encode this logic and are the source of truth.
- `pekin_shift_template` — two-week rotation `{weekA:{0..6:{lunch:[],dinner:[]}}, weekB:{...}}` keyed by `Date.getDay()` (0=Sun). Applied to a month via `applyTemplate(y,m)`; week A/B is chosen by `Math.floor((day-1+firstDow)/7) % 2`.
- `pekin_master_pw` — optional master password that works for any non-admin staff account (combined with their username).
- `pekin_shift_YYYY-MM` — per-month shift assignments: `{dateKey:{lunch:{names:[],ext:bool}, dinner:{names:[],ext:bool}}}`.
- `pekin_published_YYYY-MM` — `'1'` if that month's shift has been published to staff.
- `pekin_avail_YYYY-MM` — per-month staff availability: `{staffId:{dateKey:'ok'|'off'|'maybe'}}`.
- `pekin_db_v` — monotonic version number used by the sync logic (see below).

Helpers `dKey(y,m,d)` and `shiftKey()/availKey()/publishKey()` generate the date/month keys and should be reused rather than reformatting date strings inline.

### Firebase sync — read this before touching `_applyDb` or `_pushAllToFirebase`

The shift app has a Firebase Realtime Database (project `pekin-shift`, region `asia-southeast1`) acting as shared storage so that the manager's PC, staff phones, and other devices see the same data. Credentials are embedded in `admin.html`, `staff.html`, and `shift/index.html` — this is intentional (client-only app, anyone-can-read config) but keep that in mind before changing them.

The sync contract is version-aware and **asymmetric** for `pekin_users`:

1. On load, each page reads `pekin/db` from Firebase (5 s timeout) and falls back to `/shift/db.json` on failure. `_applyDb()` then merges into `localStorage`:
   - If the Firebase `_v` is greater than or equal to local `pekin_db_v`, Firebase wins for dynamic keys (`pekin_shift_*`, `pekin_published_*`, etc.); otherwise the local copy is preserved (protecting unsynced manager edits).
   - Keys missing locally are always backfilled from Firebase, even when local is "newer".
   - **`pekin_users` is special**: if the manager PC has a local copy, it is treated as authoritative and pushed up to Firebase (this is what allows staff renames/deletions to survive). Only an empty local roster is replaced from Firebase. Do not "simplify" this into a generic merge — the asymmetry is load-bearing.
2. Every save goes through `_syncKeyToFirebase(key,value)` which writes that key plus a new `_v=Date.now()` and updates local `pekin_db_v`. `_pushAllToFirebase()` batches everything and is also called on `beforeunload`, `pagehide`, and (awaited) on `logout()` so edits do not vanish on navigation.
3. `admin.html` installs a realtime listener on `pekin/db` that only accepts incoming updates for `pekin_avail_*` keys, so a manager editing a shift never has their in-progress work clobbered by staff activity.

The login page (`shift/index.html`) has its own simpler `_applyDb` that uses pure version comparison — it does not need the `pekin_users` asymmetry because it only reads.

When adding a new persisted key: add it to `_STATIC_KEYS` (if it's config) and to the loops in `_pushAllToFirebase()` so it participates in sync; otherwise it will work on one device but silently disappear on another.

### Auth

Auth is entirely client-side. `shift/index.html:doLogin()` looks the user up in `pekin_users`, accepts either their stored password, their `customPassword`, or `pekin_master_pw`, and writes a `pekin_session` into `sessionStorage` with an 8h expiry. `admin.html` and `staff.html` redirect to `shift/index.html` if `getSession()` returns null or the role does not match. Passwords are stored in plaintext in `localStorage` and mirrored to Firebase — this is known and accepted for this low-stakes internal app.

## Editing conventions

- The marketing pages share navigation markup but not via includes. When you add/remove/rename a nav entry, update `index.html`, `menu.html`, `about.html`, `howto.html`, `blog.html`, `gallery.html`, `contact.html`, `order.html`, **and** `shift.html` (which has a trimmed nav without the shift link).
- `shift/admin.html` and `shift/staff.html` both hard-code the default user list and both contain their own copy of the Firebase config, sync logic, and helper functions. When fixing a bug in sync or auth, check whether the same fix is needed in the other file (and in `shift/index.html`).
- Commit messages in this repo are short, imperative, often bilingual, and frequently prefixed with `fix:` / `sync:` / `Update ...`. Match the existing style (see `git log`).
- GitHub Pages serves from the default branch. Do not introduce a build step or move files into a `dist/` — everything must be directly servable from the repo root.
