# Rangipo disc 3D damage reconstruction

Reconstruct the internal resin-stain damage in radiata pine stems in 3D from
photographed serial disc cross-sections, to show where damage is greatest and
how it runs up the stem. Part of the BSI Rangipo wind-damage project (Cyclone
Gabrielle, Feb 2023). This repo is the imaging/3D side; the stem wind model is
separate.

## Priorities (in order, gated)
1. The disc metrics from `disc_band_metrics.py`: per disc, distance from pith
   and edge, arc, max thickness, and area as a pixel count scaled to mm2, per
   threshold. Get these right. Do not proceed until Steve is satisfied with
   them.
2. Only once Steve is satisfied with the metrics: the per-tree 3D model, the
   colour-threshold volume showing stain and growth rings as nested shells
   about a thin pith axis, sweepable through thresholds (bands 5 or 10 wide).
3. Only after that: evaluate the rest, which includes damage area against stem
   height and peak-damage height, validation against the screening model's
   predicted height, and comparison between clones and across tree sizes. Scope
   and order of these to be set by Steve at that point.

Do not move to a later priority until Steve signs off the earlier one.

## Tooling
- Imaging and 3D: Python (numpy, scipy, PIL, pandas, plotly, matplotlib, rawpy).
  This is the right tool for this work; do not port it to R.
- The disc marker UI is R/Shiny (magick) because it was convenient, not because
  R is preferred for the pipeline.

## Data and join keys
- Disc photos: one TIFF per disc, 8-bit RGB, ~5616x3744, converted from Canon CR2.
  CR2 to TIFF must use identical settings across all discs, auto-brightness and
  auto-colour OFF, or cross-disc comparison breaks.
- `disc_manifest.csv`: tree, plot, treeno, height_m, barcode, file. 65 discs,
  14 trees plus a `prune` test tree. `file` is `<barcode>.tif`.
- `disc_marks.csv`: file, pith_x, pith_y, flip, bad. Pith from mouse clicks in
  the marker tool, in original pixel coordinates. flip=1 means rotate the image
  180 before use. bad=1 means exclude.
- Join manifest and marks on `file`.
- Calibration frame: a separate CR2 of a 1 m FULLER rule. Scale is fixed:
  1 mm = 4.0 px, so **0.25 mm/px**. Same light box and camera height for every
  disc, so this one scale applies to all.

## Scripts
- `disc_pith_marker.R` (Shiny): mark pith by click, flip 180, flag bad, save
  `disc_marks.csv`. CROP parameter at top zooms in for clicking.
- `disc_band_metrics.py`: per disc, colour-distance to a fixed resin reference,
  thresholded into bands. Writes `disc_threshold10_metrics.csv` (full crescent
  geometry at threshold 10) and `disc_area_by_threshold.csv` (area as pixel
  count at thresholds 10..100). MM_PER_PX at top.
- 3D assembler: NOT YET BUILT. See Next.

## Method (settled, do not relitigate)
- The stain is the wood that was at the cambium when the cyclone hit. About
  three growth rings have grown outside it since. It is therefore one continuous
  growth-ring surface and must run up the stem unbroken, changing only smoothly
  with the taper. Per-disc detections interpolated as raw pixels produce false
  breaks; that is wrong.
- Each disc's stain is a crescent with an inner radius, an outer radius, an arc
  length (circumference coverage) and a radial thickness. It is not a flat plane
  and not a single-radius sheet.
- Reconstruct by interpolating crescent PARAMETERS (arc, thickness, inner/outer
  radius, bearing) against height, not pixels. This is shape-based interpolation
  (literature: Raya & Udupa; contour interpolation needs slices mutually centred,
  similar size, similar shape). It fails on branching or dissimilar slices, so
  branch discs and runaway selections must be excluded, not interpolated through.
- Colour-distance threshold knee: pixel counts climb gently from threshold 10 to
  50, then jump four to tenfold at 60 as the selection escapes the stain into
  normal wood. Signal lives in 10 to 50.
- Damage sits on one compass bearing. After flip-correction it is the loaded
  hemisphere (right of pith in the current files).

## Registration per disc
- Pith (centre): from `disc_marks.csv`.
- Outer diameter (radial scale, taper): from the disc edge.
- Height (z): from the manifest.
- Bearing (rotation, N-S): the saw cut runs through the pith on a N-S axis. The
  cut line locks rotation so the stain does not spiral between discs. Auto cut
  detection works on clear discs and fails on faint ones; the marker tool can be
  extended to capture it with a second click if needed.

## Current state
- Tree 7308 fully marked, 7 discs 3.4 to 9.4 m. 23721 (7.4 m) is a branch disc,
  flagged bad. 23735 (8.4 m) was excluded once as it read larger than its taper;
  optional.
- 7308 band metrics produced. Scale fixed at 0.25 mm/px.
- Other trees: TIFFs not yet converted/uploaded. Pipeline runs off the manifest
  once they exist.
- A continuous-band, multi-threshold 3D render exists as a prototype but is not
  packaged.

## Next
1. Package a manifest-driven assembler: a per-disc parametriser returning the
   crescent parameters per threshold, and a per-tree stacker that interpolates
   those over height and builds the model. Run from the manifest for any tree.
2. The end product is the whole stem as a colour-threshold volume: growth rings
   as concentric shells and stain as the continuous eccentric band, about a thin
   pith axis, sweepable through thresholds. Bands 5 or 10 wide.
3. Lock rotation to the cut line to remove spiral.
4. Convert remaining trees' CR2s to TIFF (identical settings) and run all trees.

## Conventions
- No defensive code: no tryCatch, no if-exists checks, no NA-filling. Assume
  inputs are clean and let it fail loudly.
- No start/finish print notices or custom error messages. Keep code uncluttered.
- Put `#DD.MM.YY HH:MM NZST` at the top of every script, updated when edited.
- Figure export: half page 7.5x5 cm, full page 15x10 cm, 300 dpi.
- Institution is BSI. Scion was merged into BSI; do not reference Scion as a
  separate entity.
- Answer only what is asked. Be concise. State only what is known.
- Always reply with a TLDR only. Steve will ask for more if he needs it.
- Always commit changes and deliver via a pull request, not a direct push to main.
- During development, self-merge each PR right after pushing; Steve just pulls main.
