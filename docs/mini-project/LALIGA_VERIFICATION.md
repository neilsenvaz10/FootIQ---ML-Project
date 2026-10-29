# La Liga 2026-27 regulation: manual verification (status: PENDING, not confirmed against the live document)

## What has to be confirmed
The La Liga tie-break and relegation rules in `config/season_rules.json` come from this federation document:

**Official file (live):** `https://rfef.es/sites/default/files/2026-06/1._CNL_Primera_y_Segunda_Division.pdf`
Title: *Normas reguladoras y bases de competición de los Campeonatos Nacionales de Liga de Primera y Segunda División, temporada 2026-2027*. Article 10 (tie-break for equal points) is on page 6; article 8 no. 7 (positions 18th, 19th, 20th relegated) is in Title II.

The live URL refuses automated downloads (HTTP 403, Cloudflare; rechecked 2026-10-25 and not bypassed). I therefore read the Internet Archive capture of the same URL:
`https://web.archive.org/web/20260714112722id_/https://rfef.es/sites/default/files/2026-06/1._CNL_Primera_y_Segunda_Division.pdf` (captured 2026-07-14 11:27:22 UTC; the `id_` form returns the original bytes unmodified; the origin file was last modified 2026-06-30).

| Property of the file I read | Value |
|---|---|
| Size | 289,520 bytes |
| **SHA-256** | **`35b0a9e4a011325a5dd1144b790cf986bdcdb33a2c2b1c4cf6fed7872d6146ac`** |

**Until your checksum matches, nobody should say the live document was confirmed.** The profile therefore carries `live_confirmation: PENDING`, which the application shows next to the rules notice.

## How to check (about one minute)
1. Open the live URL above in your own browser and save the PDF (do not print-to-PDF or re-save from a viewer: that changes the bytes).
2. Compute its SHA-256:
   * Windows PowerShell: `Get-FileHash -Algorithm SHA256 "C:\path\to\1._CNL_Primera_y_Segunda_Division.pdf"`
   * Windows Command Prompt: `certutil -hashfile "C:\path\to\1._CNL_Primera_y_Segunda_Division.pdf" SHA256`
   * macOS or Linux: `shasum -a 256 file.pdf` or `sha256sum file.pdf`
3. Compare with the value in the table (case does not matter, spaces are ignored).

## How to read the result
* **Identical:** your file is byte-for-byte the document I read. Tell me and I will mark the live confirmation as done (with your name and date in the profile note) and record the check.
* **Different:** the federation may have updated the file after 14 July 2026, or the download was altered. Send me the file (put it in `data/supervised/rules_research/` and tell me) and I will compare Article 10 and Article 8 no. 7 line by line. Nothing is assumed meanwhile.

## Manual cross-check of the text (optional)
Article 10, two clubs level on points, in this order: (a) greater goal difference in the matches between them; (b) greater overall goal difference; (c) more goals scored; (d) better fair-play classification; (e) a match on neutral ground designated by the RFEF. More than two clubs: (a) better points in the matches between them, as a mini-table (if all clubs then have different points no further criterion is used; the second criterion is reached only if two clubs remain level); (b) goal difference in the matches between them; (c) overall goal difference; (d) most goals scored; (e) fair play; (f) a match on neutral ground. Article 8 no. 7: the clubs in 18th, 19th and 20th place are relegated to the Segunda División.

## What is not affected
The points-only simulation does not use these rules. The final-position simulator is disabled regardless of this check.
