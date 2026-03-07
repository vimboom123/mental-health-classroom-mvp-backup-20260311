# Claude Code Review — empirical figures (journal readiness)

Reviewed targets:
- `generate_publication_figures.py`
- `README_figures.md`
- `figures/*.png`

## Strengths
- Fig2 forest plot logic is solid: OR + 95% CI derived from manuscript coefficients/SE.
- 300dpi export and deterministic seed improve reproducibility.
- README clearly separates manuscript-derived values and simulation assumptions.

## Main risks
1. **Fig1 labels overlap** on x-axis (readability issue).
2. **Fig2 log minor tick artifact** (`6×10^-1`) appears and looks unpolished.
3. **Fig3 survival curve** is illustrative/simulated; title should state this explicitly; CI method can be improved.
4. **Fig4 robustness** visual alignment/legend placement can be cleaner.
5. Abbreviations (AS/FT/IR) need full-name definitions in caption or axis notes.

## Recommended fixes before submission
- Rotate Fig1 x-labels to 45° and right-align.
- Suppress minor tick labels on Fig2 log axis.
- Change Fig3 title to include “Illustrative”, and use transformed CI instead of simple symmetric CI.
- Reposition Fig4 legend away from data; refine range markers.
- Add abbreviation glossary in figure captions.
- Pin library versions in README.
