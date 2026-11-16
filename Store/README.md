# Yeouido Riverside Café

A virtual café near Yeouido Hangang Park, Seoul. A manager decides each morning whether to send each customer a menu message, a same-day coupon, or no outreach. The objective is to maximize contribution profit over 30 days while keeping opt-outs within 5% in each evaluation window.

From this folder in VS Code, run `uv sync --locked` to install the Python 3.12 environment. Double-click `run.command` on macOS or run `uv run run.py` in the terminal.

| Menu | Task |
| --- | --- |
| 1 | Run environment validation with four test policies. |
| 2 | Run a short PPO trial and report its speed. |
| 3 | Train and evaluate the initial PPO policy. |
| 4 | Re-evaluate the saved v1 policy on the same windows. |

Use `uv run check.py` to verify customer traits. After menu item 1, run `uv run python -m http.server 8000 --bind 127.0.0.1 --directory public` and open [the local replay](http://127.0.0.1:8000) in a browser.

`project_spec.md` records the model and assumptions. The `data/` folder contains the synthetic customer profiles, their price sensitivity estimates, and daily rain and calendar inputs. `results/` contains the latest summaries, action logs, and run history. `public/` contains the replay and the data used to draw it.

The 100 synthetic profiles come from [NVIDIA Nemotron-Personas-Korea](https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea) under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), with English summaries added. Rainfall comes from [Open-Meteo's ERA5 archive](https://open-meteo.com/en/docs/historical-weather-api). [Python Holidays](https://holidays.readthedocs.io/en/latest/) supplies the Korean public holiday calendar. Use `uv run make_external_factors.py` to rebuild the daily inputs.
