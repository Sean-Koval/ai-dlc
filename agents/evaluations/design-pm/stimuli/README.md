# Constructed Design PM inputs — coordinator access only

These deliberately authored fixtures are experimental **inputs**, not outputs of
any compared model condition. The separate case specification at 995a39b remains
an immutable preparation snapshot; `manifest.json` records the actual construction
follow-up. Human labels and dedicated experiment approval remain pending. Author
browser checks in `observations.json` verify constructed behavior, not human
preference or incremental workflow value.

## Participant isolation

Do not serve or attach this entire directory, README, manifest, observations,
corpus, source repository or construction recipes to an experimental participant.
A coordinator copies only the selected case's `participant_access: true` artifacts
into a fresh empty directory, preserving their relative layout, and supplies that
case's allowed task projection. Verify hashes before release. No calibration
packet may include DH01/DH02. Human approval/freeze and fresh-session exposure
attestation are still required before held-out release. The author has seen them.

For DC04 copy **only the three PNG files**. Its HTML source is retained solely for
capture provenance and must not be supplied or served to the participant. The
screenshots have no working interaction; playback remains unverified. Optional
DH02 `later.html` belongs to the separately approved constructed revision-pair
stress probe, is excluded from the primary packet, and must not be pooled with
naturally generated outcomes.

For other cases, serve the isolated packet through a local HTTP server bound to
127.0.0.1. For example, after manually assembling a permitted case packet:

```sh
python -m http.server 8766 --bind 127.0.0.1 --directory /path/to/isolated-case-packet
```

Open its `index.html` path. DC03 additionally needs `council.css` and `brand.md`.
All resources are local; no backend or account is used. Browser storage is
synthetic and origin-scoped: reset each attempt in a fresh browser context, or
clear that isolated origin's localStorage and reload. Never reuse a preceding
condition's storage. The README's example is a manual serving command, not an
experiment runner or automatic budget authorization.

## Author construction checks

The following checks were executed with installed Node 22.23.1, cached Playwright
CLI 0.1.18 and installed Chrome 152.0.7977.82 on September 8, 2026 (UTC). No runtime
was downloaded. Sources were served on loopback; a favicon 404 was incidental.
These are repeatable manual checks, with actual observations in `observations.json`:

1. DC01: select River Workshop Annex and 2030-04-04 09:00, review, confirm and
   reload. Review retained the selected date; saved confirmation instead showed
   2030-04-03, reproducing the intended failure. Initial viewport was not recorded.
2. DC02 at 360×800: confirm the supplied long description twice and reload. One
   Q041 record remained; document width did not exceed the viewport. No taste or
   comprehensive usability rating was performed.
3. DC03 at 360×800: select Apartment 11, review, save and reload. Its full address
   and Thursday remained; computed header background matched the original kit's
   rgb(23,44,75). This checks kit loading, not a human brand-fit score.
4. DH01 at 360×800: choose overflow; focus the opener and press Enter. Five Tab
   presses never reached dismissal, Escape left the dialog open, while mouse
   dismissal worked. Selected-point identity remained visible. This is a specific
   keyboard defect, not a comprehensive accessibility assessment.
5. DH02 at 360×800: in index.html retain North border at 21 minutes and edit North
   beds to 06:20. Reload preserves both. Open the constructed later.html, save
   North beds and reload: North border resets to 12 minutes. The prior/later pair
   is author-constructed; no generation experiment or natural regression occurred.
6. DC04: visit each construction page at 390×844, capture a CSS-pixel viewport PNG
   and visually inspect all three captures. The captured list, detail and paused
   states are real rendered images. Depicted playback controls do not establish
   functioning playback. Source and capture bytes are hashed in the manifest.

Fixture source/manifest integrity and PNG dimensions are covered by
`tests/test_design_pm_stimuli.py`. These tests cannot authenticate observer claims
or prove human quality. Changing a fixture requires fresh construction checks,
updated hashes and a new frozen stimulus version before any comparison. Keep
previous experimental registrations immutable; do not relabel old evidence.
