Workshop materials for running LLMFlux on NCSA Delta: participant guide
(`README.md`), scripts (`workshop/`), facilitator and presenter notes.

- Every change to `workshop/` ships with tests in `tests/test_workshop.py`
  (`unittest.TestCase` style), and `python -m pytest` must pass. Add tests by
  default.
- Participants are first-time HPC users: any change to a script's output or
  behavior should be reflected in `README.md` in the same change.
- Never commit real account or reservation names into `workshop/workshop.conf`.
  The repo is public; the filled-in copy lives only on Delta.
