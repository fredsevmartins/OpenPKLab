# Scientific plugins and calculation methods

## Data quality (`data_quality`)

Runs on a copy of a CSV/XLSX table. Reports row/column count, fraction of nonmissing cells, missing values by column, duplicate whole rows, multiple values in columns ending in `unit`/`units`, numeric conversion failures/nonfinite entries where at least half the nonempty column is numeric, and negative values in `time`/`concentration`. For numeric columns with at least four finite observations, values outside Q1 − 1.5 IQR to Q3 + 1.5 IQR are flagged for review.

These are screens, not automatic exclusions, unit conversions, evidence of misconduct, or inferential tests. Replicates can look like duplicates and legitimate measurements can be IQR outliers. Unit detection is limited to explicit unit columns and supplied metadata; it cannot infer undocumented units. Original values are never changed.

## PK visualization (`pk_visualization`)

Required options:

```json
{"time_column":"time", "concentration_column":"concentration", "time_unit":"h", "concentration_unit":"mg/L", "scale":"linear"}
```

`scale` may be `log`, which requires every concentration to be positive. `group_column` and `individual_column` partition profiles (at most 100). Within each profile, times must be finite, nonnegative, unique and strictly increasing; concentrations must be finite, nonnegative and complete. Missing grouping labels are rejected. No points are silently dropped, averaged, sorted, imputed or smoothed. A PNG of observed points joined by straight lines is saved as a derived figure with its source file ID/checksum and options. Matplotlib is headless.

## NCA (`nca`)

The same time/concentration column/unit options are required. Analyze **one individual, treatment group, occasion and dose interval at a time**. Standard `subject`, `group`, `occasion` and `dose_interval` columns with multiple values are rejected. If your identifiers use other column names, split the source into explicit documented profile derivatives first; the software cannot infer arbitrary grouping semantics.

Supported time labels: `h`, `min`, `s`. Concentration labels: `mg/L`, `ug/mL`, `ng/mL`, `ug/L`, `mg/mL`, `nmol/L`, `umol/L`. Values stay in their supplied units. No cross-unit conversion is performed. Explicit conflicting `<column>_unit` or `<column>_units` columns and mixed unit columns are rejected. Units omitted from the source must be verified by the researcher before supplying options.

- **Cmax:** maximum observed concentration.
- **Tmax:** time of the first observed maximum.
- **AUClast:** sum of `(C[i] + C[i+1]) / 2 * (t[i+1] - t[i])` from the first through last observed sample, using linear trapezoids. Units: concentration × time. No extrapolation from missing time zero, to infinity, or across dosing intervals.
- **Lambda-z:** exploratory ordinary least-squares regression of `ln(C)` on time using the final three observations, all positive and strictly after observed Tmax. Require negative slope, R² ≥ 0.90 and a fitted interval spanning at least one estimated half-life. Lambda-z = negative slope.
- **Terminal half-life:** `ln(2) / lambda-z`. Units: input time.

If terminal criteria fail, lambda-z and half-life are null with explicit uncertainty; Cmax, Tmax and AUClast may still be available (`status: partial`). A terminal estimate has `status: estimated`, fit R² and zero-based source row indices. No automatic optimal terminal-window selection, weighting, dose normalization, AUC infinity, clearance, volume, bioavailability or bioequivalence is implemented. Passing a three-point fit is not evidence that a true terminal phase was sampled.

Analytical validation: synthetic `C(t) = 16 exp(-ln(2)t)` at `t = 0,1,2,3,4` gives Cmax 16, Tmax 0, **linear-trapezoidal** AUClast 22.5, lambda-z ln(2) and half-life 1. The continuous analytical integral differs from a trapezoidal approximation; tests deliberately validate the stated numerical method. A linear profile at `(1,2),(2,2),(4,0)` has AUClast 4 and first Tmax 1.

Every successful plugin invocation records source ID/SHA-256, complete options, plugin version, Python/scientific library versions and computational results in append-only notebook records. A human reviews the result; it does not become a measured observation.

## Lightweight extension interface

Install only trusted Python packages; plugins execute with the server's privileges. A plugin is a class with `name`, `version` and `run(frame: pandas.DataFrame, options: dict) -> dict`. Return JSON-serializable finite values. Optionally return PNG bytes under `image_bytes` for a derived figure. The core supplies a deep copy of the parsed table. Register a package entry point:

```toml
[project.entry-points."openpklab.plugins"]
my_analysis = "my_package.plugin:MyAnalysis"
```

Restart after installing. Plugins are discovered at `Lab` startup, duplicate names are rejected, and `run_scientific_plugin` dispatches by plugin name. No changes to the core notebook are required. This is not a sandbox or a plugin marketplace. Custom plugin scientific validation is the author's responsibility.

## Scientific hints

Adding observations, results, methodology or datasets triggers deterministic missing-methodology checks, table quality screens, and a potential-conflict check for explicit endpoint/time/group/subject/unit values. A differing value may be a valid replicate; the hint asks the researcher to clarify. Generic missing-method questions are persisted once per distinct finding. Feedback is accepted/rejected/deferred and never rewrites evidence.

Each hint contains observed evidence, computational finding, scientific interpretation, hypothesis, recommended action, uncertainty, priority and experiment/record/file IDs. Pending and historical hints remain distinguishable by timestamps and feedback; accepted/rejected items are retained for audit, not erased when source context changes. No server-side LLM or literature lookup is used. ChatGPT can propose further hypotheses, statistical analyses and follow-up experiments from the retrieved context, but must label these as suggestions and avoid inventing absent design details or claiming confirmation.
