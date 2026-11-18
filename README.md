# Temporal coordination prototype — v0.3

An experimental stimulus generator for asking whether multimodal models use
frame order to judge which of two movement components leads.

**Status:** synthetic proof of concept. The checks validate the generator's
construction, not models, human perception or biomechanics. No model has been
evaluated as part of this release. The figures are schematic, not validated
cross-country skiing movements. This is a filmstrip task, not yet a video test.

## Quick start

The included `example_output/` is ready to use; no installation is needed to
inspect the PNG images or fill in the response spreadsheet.

To generate another set, install Python and then run these commands from the
project directory:

```bash
python -m pip install -r requirements.txt
python coordination_prototype.py --out output
python -m unittest -v
```

Defaults: offsets 15°, 30°, 60°; 2 independent **pairs** per offset; 2 zero-offset
catch trials; 12 frames spanning one complete cycle; seed 1. This produces
14 stimuli in each of 3 modes, hence 42 images. There are only 6 independent
nonzero-offset pairs: 42 images are not 42 independent movement samples.

For another sampling resolution, for example:

```bash
python coordination_prototype.py --frames 24 --reps 4 --seed 2 --out output_24frames
```

Use a fresh output directory. Existing nonempty directories are deliberately
not overwritten. Only one cycle per sequence is supported; `--cycles 2` is
rejected. Offsets must be unique and strictly between 0° and 180°. Zero is
reserved for catch trials; half-cycle offsets have an ambiguous lead direction.

## Task and exact matching

One red arm and the opposite blue leg swing at the same frequency. The question
is which reaches its right-most peak shortly before the other around a repeating
cycle. It is about relative phase, not which peak happens first after the chosen
start of the image. The answer is ARM, LEG or SAME.

For each nonzero offset, a new base sequence is generated with random start
phase and independently varied arm and leg amplitudes. Its partner is the exact
time reversal. Reversal retains the starting frame:

- Forward canonical indices: 1, 2, 3, ..., N.
- Reverse canonical indices: 1, N, N−1, ..., 2.

Both ordered versions have the **same first posture and the same set of
postures**, but opposite labels. Amplitudes and starting phase are shared within
a pair and varied between pairs. No pose interpolation is required for reversal.

## Presentation modes

| Mode | Information shown | Role |
|---|---|---|
| `ordered` | One complete cycle in the appropriate direction | Main temporal-order task |
| `shuffled` | One permutation of the base poses, identical for both pair members | Matched control for the original direction |
| `single` | One randomly selected base pose, identical for both pair members | Matched static control |

Control PNGs are copied within each pair and verified to have identical SHA-256
hashes. Their filenames differ, so **do not expose filenames, paths or trial IDs
as model-visible text**. When using an API, send image bytes and the prompt only.
For manual use, present the image with a constant neutral attachment name such
as `stimulus.png`, in a fresh conversation for every trial. A chat interface may
retain context or handle images differently; manual results are exploratory.

The label in a control row refers to the original ordered sequence; it cannot
be recovered from the matched control image. A shuffled sequence may have local
timing patterns, but those patterns give no information about which original
label generated it because both labels receive the very same image. Do not
describe this as proving that all temporal information has been destroyed.

The same prompt is used for all modes. The deliberately underinformative controls
measure performance without access to the original ordering. They are not tests
of whether a model can reconstruct the original timeline or express uncertainty.

## Files and first manual pilot

1. Open `responses.csv` in a spreadsheet. Use `presentation_order` within each
   mode; modes have separately randomized schedules.
2. Open the image specified by the `image` column. In a **fresh conversation**,
   send only that image and the exact text of `prompt.txt`. Do not attach the
   complete CSV, this README, the answer key or both members of a pair together.
3. Record the exact response, model name/version, date and available sampling
   settings. Preserve any explanation or refusal in `notes`. Do not force an
   invalid response into a valid category after seeing the key.
4. Finish the planned set before checking `answer_key.csv`. Join results using
   both `trial_id` and `mode`.
5. Compare ordered, shuffled and single accuracy separately for nonzero offsets.
   Report zero-offset SAME catch trials separately, along with response counts
   (ARM/LEG/SAME/invalid). Catch trials can be solved from static poses.

Outputs:

- `trials/<mode>/trial_XXX.png`: image stimuli, without answer labels.
- `responses.csv`: answer-free sheet for recording model outputs.
- `answer_key.csv`: private labels, pair IDs, full-precision parameters,
  canonical frame indices and file hashes. Never provide it to the model.
- `angles.csv`: segment angles for every presented frame, for technical audit.
- `prompt.txt`: shared prompt.
- `validation.json`: generator settings and automatic construction checks.

The demo file `pair_demo.png` (in this package) reveals labels and is explanatory
only; it must not be used as an evaluation input.

## Interpretation and limits

- A good ordered score alone is insufficient. The contrast with matched controls
  asks whether the presented order contributes to the answer for this task.
- Nonzero-offset labels are balanced ARM/LEG. A random guess between these two
  has 50% expected accuracy. A uniformly random ARM/LEG/SAME guess has 33.3%.
  Report SAME and invalid responses; do not silently discard them or assume one
  universal chance level for every response policy.
- For identical control inputs with opposite labels, a deterministic image-only
  response scores exactly 50% per pair if it always chooses ARM or LEG. SAME or
  invalid responses reduce that score. Independently sampled stochastic responses
  can land above or below 50% in a finite run. Such a small-sample deviation is
  not by itself evidence of a shortcut. Repeated trials are not independent data.
- Small default counts are for checking the workflow, not estimating detection
  thresholds or making capability claims. Later uncertainty estimates should
  account for pair clustering and matching across presentation modes.
- With 12 frames, temporal sampling steps are 30° of the cycle. This does not
  impose an absolute 30° detection limit: smaller offsets also change sampled
  positions. Vary frame count deliberately and inspect image resizing, legibility
  and model input handling. More frames in a wide strip can mean smaller figures.
- The analytic phase check uses the known one-cycle sinusoidal signal. It is not
  an independent scientific validation or a model baseline operating on PNGs.
- Randomization and exact pairing address specific static shortcuts; they do
  not prove that every possible cue, strategy or interface artefact is excluded.
- Success concerns ordering in schematic images. It does not establish expert
  movement understanding, natural-video competence, or physical-world safety.
- Biomechanically meaningful stimuli, human comparison, thresholds and movement
  entropy remain future work. Real-motion stimuli need their own validation.

## Changelog

- **v0.3:** exact reversal pairs with identical starting poses; byte-identical
  paired controls; one-cycle validation; clearer cyclic prompt; private answer
  key and randomized response sheet; full-precision parameters and angle export;
  automatic construction audit and regression tests; corrected control claims.
- **v0.2:** lead/lag task, varying start phase and amplitudes, three presentation
  modes. Pair members were sampled independently, so exact matching was not yet
  enforced. The phase verifier incorrectly allowed arbitrary cycle counts.
- **v0.1:** fixed-start coordination comparison; a static first-frame shortcut
  revealed the answer. Replaced by the temporal-direction task.

Developed with AI-assisted coding (Claude and ChatGPT/Codex), with iterative
review of the experimental design. No API calls or paid services are used by
this generator.
