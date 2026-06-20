# Stain detection threshold (T10) — method and reproduction

Rangipo disc damage analysis, BSI. Colour-threshold detection of traumatic
resinosis in radiata pine disc cross-sections.

## What is being detected
Traumatic resinosis darkens and reddens the affected wood relative to clean
sapwood. The detector classifies each pixel by how close its colour is to a
fixed reference colour of resin-stained wood, and counts the pixels that match.
The threshold **T** sets how close a pixel's colour must be to count as stain.

## Definition of T10 (software-agnostic)
1. **Image**: 8-bit RGB, the standardised TIFF (fixed RAW→TIFF conversion, auto
   brightness and auto colour OFF), scale 0.25 mm/px (1 mm = 4.0 px).
2. **Reference colour** `Cref = (Rref, Gref, Bref)`: a single RGB triplet
   representing resin-stained wood (see derivation below).
3. **Per pixel** `C = (R, G, B)`, compute the Euclidean distance in RGB space:

   `d = sqrt( (R − Rref)² + (G − Gref)² + (B − Bref)² )`

4. **Classify as stain if `d < T`**, with **T = 10** (8-bit levels, 0–255 per
   channel; the full possible range of `d` is 0–441).
5. Restrict to inside the disc (exclude background and bark); an optional
   morphological opening/closing removes isolated speckle.

In words: **T10 selects a sphere of radius 10 in RGB colour space centred on the
resin reference colour.** Any tool offering "select by colour within a tolerance
using Euclidean RGB distance" reproduces it with tolerance = 10. Tools that use
per-channel or differently-scaled tolerances will not match exactly.

## Reference colour (Cref)
`Cref` is derived once from the most heavily stained reference disc (barcode
23717): the median RGB of the top 1% most colour-saturated, dark, red pixels
within the loaded (stained) hemisphere. The same triplet is then applied to
every disc, so all discs are measured against one fixed standard. To reproduce
in other software, sample clean resin-stained wood to obtain the equivalent
`Cref` triplet, or use the pinned values from this project.

## Why T = 10
A fine threshold sweep (T5–T15) showed the selected stain area increases
**continuously** with T — there is no natural plateau, because the stain colour
blends smoothly into surrounding wood. Consequences:

- Below ~T7 the selection is too sparse to be reliable (noise).
- Above ~T15 the selection begins to capture the naturally darker **growth-ring
  latewood** and basal heartwood, inflating the measured area with tissue that
  is **not** cyclone damage.
- **T10 is the lowest threshold that gives a usable, ring-free signal**, and it
  places each tree's damage maximum at the physically expected mid-stem height.

## How to interpret the number
Because the area–threshold relationship is a continuous ramp, the T10 area is a
**relative (ordinal) index of stain extent** — the dark stain core, measured
identically across all discs — rather than an absolute measure of total affected
tissue. It is therefore used to **rank and compare** trees, not as an absolute
area. Discs whose selection escapes into the growth rings across the T5–T15
sweep are flagged low-confidence and down-weighted.

## Limitation
A single fixed reference colour can under-read clones whose stain hue differs
from the reference. A self-calibrating variant (re-centring the reference to each
disc's own sapwood) was prototyped to address this but is not yet validated; T10
against the fixed reference remains the working method.
