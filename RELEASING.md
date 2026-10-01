# Releasing epiplot

Steps for each new version, in order:

1. Check Colab's package versions in a fresh notebook. If any have changed,
   update the `colab` environment pins in `pyproject.toml` first.
2. Change `version` in `pyproject.toml` (new feature: middle number,
   e.g. 0.4.0 → 0.5.0; fix only: last number, e.g. 0.4.0 → 0.4.1).
3. `pixi run fix`, then `pixi run check`.
4. Commit ("Release X.Y.Z"), push, and wait for green ticks on GitHub.
5. `git tag vX.Y.Z` then `git push origin vX.Y.Z`.
6. On GitHub: Releases → Draft a new release → choose the tag → title
   `vX.Y.Z` → write a short "What's new" → Publish release.
   (Publishing the GitHub Release is what starts the PyPI upload; pushing
   the tag alone does not.)
7. Actions → Release run → Review deployments → tick pypi → Approve.
8. Check pypi.org/project/epiplot shows the new version, then run
   `%pip install -U epiplot` in a fresh Colab notebook and check
   `epiplot.__version__`.