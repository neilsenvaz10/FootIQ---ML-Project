# Club crests (local, licensed only)

FootIQ shows a generated badge (initials on a deterministic colour) for every team unless a **licensed** crest is listed in `src/data/crests.json` **and** its file exists in this folder. Nothing is downloaded, hotlinked or fetched at run time.

This folder is empty: no crest pack has been supplied, and club badges are trademarks, so none is bundled.

## Adding a licensed pack

1. Put the image files here (`.svg`, `.png` or `.webp`; square or transparent background, ideally 256 px or more).
2. Add one entry per team to `crests` in `src/data/crests.json`. The key is the team name as the app displays it, lower-case, without accents or punctuation, and without club prefixes such as "FC":

   ```json
   {
     "schema": 1,
     "crests": {
       "arsenal": {
         "file": "arsenal.svg",
         "licence": "name of the licence or the permission you hold",
         "source": "where the file came from (URL or the name of the supplier)",
         "attribution": "text the licence requires you to show (optional)"
       }
     }
   }
   ```

3. `file`, `licence` and `source` are all required. An entry that lacks one of them, or whose file is missing, is ignored (the badge is shown instead) and `tests/crest.test.jsx` reports it. Entries with an `attribution` are listed in the page footer automatically.
4. Run `npm test` and `npm run build`.

Do not add images whose licence you cannot document.
