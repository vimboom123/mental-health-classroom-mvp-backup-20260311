# Figure generation

Run the generator from this directory:

```bash
python3 generate_publication_figures.py
```

The script writes four 300 dpi PNGs under `figures/`.

## What each figure shows

- `fig1_correlation_heatmap.png`: Pearson correlation heatmap for `AS`, `FT`, `IR`, `TaskClarity`, `LearningCost`, and `DR7` in a seeded synthetic sample.
- `fig2_logit_forest.png`: Odds-ratio forest plot with 95% confidence intervals computed directly from the manuscript's Table 2 logit coefficients and standard errors.
- `fig3_survival_curve.png`: Dropout-free survival curves for low versus high learning cost, shown as Kaplan-Meier style step curves from a seeded proportional-hazards simulation.
- `fig4_robustness_coefficients.png`: Baseline manuscript coefficients compared with deterministic robustness anchors that preserve the signs and relative magnitudes described in Table 3.

## Data-generation assumptions

- Seed: `20260307`
- Sample size for synthetic data panels: `N = 986`, matching the manuscript's cleaned sample.
- Synthetic predictors are calibrated to Table 1 means and standard deviations, then correlated through a latent-factor construction so the heatmap is stable and reproducible.
- `DR7` is simulated from the manuscript's reported slopes, with the intercept recalibrated so the synthetic mean retention matches the reported `0.318`.
- The survival panel uses a Weibull proportional-hazards simulation anchored to the manuscript's robustness result `HR = 1.21` for `LearningCost`; groups are defined as `< 6` versus `>= 6`.
- Table 3 does not report full numeric robustness coefficients, so Figure 4 uses deterministic illustrative perturbations around the baseline rather than claiming exact recovered estimates.

## Dependencies

- `numpy`
- `matplotlib`
- `seaborn`
