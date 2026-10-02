# Contributing to epiplot

Thank you for your interest in **epiplot**. This page explains how to set up
the project and the routine for making changes.

## Set up

1. Install [Pixi](https://pixi.sh), which manages Python and all the
   project's tools.
2. Get a copy of the repository and install the environments:

```bash
git clone https://github.com/leehart3000/epiplot.git
cd epiplot
pixi install
```

3. Turn on the pre-commit hook, which checks your code on every commit.
   Do this once for each copy of the repository:

```bash
pixi run pre-commit install
```

## Making a change

1. Make your change, with tests in `tests/` for any new behaviour.
2. Tidy the code, then run all the checks (lint, formatting, types and
   tests):

```bash
pixi run fix
pixi run check
```

3. If you changed the documentation, build it and look at the result in
   `docs/_build/html`:

```bash
pixi run -e docs docs
```

4. Commit. The pre-commit hook runs the Ruff checks; if it stops the
   commit, run `pixi run fix`, `git add` the changes and commit again.

GitHub Actions runs the same checks on every push, including the tests
against Google Colab's package versions (`pixi run -e colab test`).

## Good practice

**epiplot** aims to make standard epidemiological plots easy, and hard to get
wrong. New features should follow the same approach: label what the data
mean, never drop missing data silently, and use colour-blind-safe colours.

## Case study data

The data used in the case studies are in `docs/case-studies/data`, with a
README giving each source and licence, and the scripts that prepared them.
Only keep the columns a case study needs.

## Releasing

See [RELEASING.md](RELEASING.md).