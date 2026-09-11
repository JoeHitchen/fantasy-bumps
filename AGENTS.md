# Repository Agent Instructions

Project tooling & documentation can be found at: [README.md](./README.md)

## Specific Instructions

- When creating a new development environment, before any code edits:
  - You must check if the remote and local versions of your base branch match.
    If one is simply ahead of the other, start from whichever is more advanced.
    If they have diverged (both have unique commits), use the local branch.
    - You must re-read your instructions if the above step resulted in a change in starting point.
  - You must install the pre-commit hooks using the command described in the tooling documentation.
    You should validate that these run correctly using the method described in the project documentation.
  - You should run the quality control checks to identify any known failures.
- If your instructions reference an issue/pull request number (e.g. "issue #123"), you must read the Github reference in full before beginning any planning.
- If your instructions reference an issue/pull request number (e.g. "issue #123"), you must also name your branch using the convention `issue<num>/____`.
- When making any file changes you must always commit all changes before declaring your task complete.
- If your instructions indicate the user expects a delivery on GitHub, you must also push your changes to GitHub and have a green workflow run on your branch for your task to be completed.
- When running commands:
  - Avoid anything which tries to change the working directory used to run a command (e.g. `cd`, `Set-Location`, `git -C`) unless strictly necessary.
  - Run commands individually and in sequence rather than batching or parallelising them, even where that would otherwise be possible. This includes waiting commands like `Start-Sleep`.

## General Instructions

- Always use British English in all code, documentation, and responses, except where required to interact with external package interfaces.
- Read all project and tooling documentation before undertaking tasks.
  This is described in [README.md](./README.md)
- Appraise existing documentation for writing style & tone before contributing, and ensure that your contributions match this existing style.
  Keep contributions brief and consciously avoid recency bias in your contributions.
