# EpiControl AI research prototype

This repository accompanies the IEEE-style Word manuscript, **EpiControl AI: A Reproducible Two-Cohort SEIR Framework for Adaptive Intervention Analysis**, in `paper/`. It is a synthetic scenario simulator. Its hospital demand and restriction cost outputs are proxies, and it is not calibrated to a specific disease or region.

## What is implemented

- `research_model.py`: a two-cohort SEIR environment with reciprocal cross-cohort contacts, RK4 integration, weekly actions, cohort conservation, and explicit reward terms.
- `q_agent.py` and `train.py`: tabular Q-learning with epsilon-greedy exploration. The three study seeds are 11, 22, and 33; each uses 1,200 training episodes.
- `run_research.py`: 40 held-out scenarios paired across fixed, threshold, and learned policies, plus parameter and numerical checks.
- `additional_checks.py`: follow-up to day 365 after removal of restrictions at day 180.
- `app.py` and `templates/index.html`: a small Flask interface for a single scenario and side-by-side strategy comparison.
- `results/`: complete raw trajectories, evaluation rows, training logs, sensitivity outputs, Q-tables, and parameter manifest from the recorded run. Re-running the scripts overwrites these outputs.
- `tests/test_research.py`: numerical, invariance, policy, learning, and API checks.

The research implementation is based on the original [EpiControl_AI repository](https://github.com/Partha81-star/Epicontrol_AI) at commit `8d5cf6a964f2c008a163cbbbac40d8fda04cfaad`. The original repository preserves earlier project files. The revised implementation and recorded outputs in this repository are the basis of the manuscript; the named authors should review them before submission.

## Run

Use Python 3.12 or a compatible recent Python version. In a fresh virtual environment:

```powershell
python -m pip install -r requirements.txt
python run_research.py
python additional_checks.py
python app.py
```

Open `http://127.0.0.1:5000/`. The learned-policy option loads `results/q_table_seed11.npy`. Run the research script first if that file is missing. The API has `GET /health`, `POST /run_simulation`, and `POST /compare_strategies`. Parameter validation returns HTTP 400 for malformed or unsupported inputs. Example:

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:5000/run_simulation' -Method Post -ContentType 'application/json' -Body '{"population":49000,"beta":0.3,"days":180,"policy":"threshold"}'
```

Optional tests:

```powershell
python -m pip install pytest
python -m pytest tests -q
```

## Interpretation

The population of 49,000 is represented by eight aggregate compartment values, not 49,000 individual agents. The contact matrix, population shares, intervention effects, hospital-demand fraction, capacity, and reward weights are illustrative. The training experiment uses parameter variation across episodes but deterministic dynamics within each episode. There is no PPO controller, live geographic surveillance, patient data, or calibration to India. The web interface displays synthetic scenario outputs only.

The three learned controllers differ substantially, and the day-365 follow-up demonstrates rebound when restrictions end. Reuse requires authors to examine the equations, results, bibliography, and disclosure. Public-health application would require new data, clinical modelling, uncertainty analysis, independent validation, and ethical review where applicable.

The paper's three figures were rendered from CSV files in `results/`; the figure files are supplied in `paper/figures/` alongside the Word manuscript. The manuscript cites the original repository and 50 research papers. It should only be submitted after the named authors confirm their contributions, affiliations, and approval.
