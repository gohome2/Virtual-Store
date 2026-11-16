# Project Specification

## 1. Store Definition

| Item | Definition |
| --- | --- |
| Store | Yeouido Riverside Café, a virtual café serving drinks and pastries. |
| Location and trade area | Near [Yeouido Hangang Park](https://english.seoul.go.kr/hangang-parks/) in Yeongdeungpo-gu, Seoul. The assumed trade area includes the park, nearby offices, and residences. |
| Replay layout | The café sits beside the Han River, with an open terrace facing the water. The office and apartment buildings sit across the street on the inland side. |
| Main customers | Assumed to be adult office workers, local residents, and park visitors. |
| Customer scale | Assumption: 100 registered customers, one per persona, all initially opted in to receive outreach. |
| Repeated decision | Each morning, choose no outreach, send a menu update with no discount, or send a coupon for that day. The coupon gives a 15% discount (assumption). |
| Decision unit and cycle | One choice per registered customer per day. Each eligible customer can receive at most one outreach item per day to limit repeated contact. Customers who have opted out receive no outreach. |
| Opening hours | 10:00–22:00 Seoul time. |
| Gain and loss | Outreach can bring customers back. Redeemed coupons reduce the café's profit per sale, and repeated outreach raises the risk of losing permission to contact the customer. |
| Episode length | Assumption: 30 days. |
| Success metric | Maximize 30-day contribution profit while keeping the share of registered customers who unsubscribe at or below 5% (assumption). For each sale, contribution is the full bill minus ingredients and any redeemed discount. Fixed costs are excluded. Opt-out rate is unique customers who opt out divided by the starting customer count. |
| External factors | Daily rainfall, day of week, and Korean public holidays. |
| Environmental data | Daily rain in millimeters from [Open-Meteo ERA5](https://open-meteo.com/en/docs/historical-weather-api) near Yeouido Hangang Park, using Seoul local dates. Korean public holidays come from [Python Holidays](https://holidays.readthedocs.io/en/latest/), including observed holidays. Weekends are calculated from the date. |
| Training and evaluation | Training uses random start dates whose 30 days fall entirely in 2016–2024. Evaluation uses twelve consecutive, non-overlapping 30-day windows starting January 1, 2025. Each window has a fixed seed based on its start date, and all policies use the same customers and seeds. |
| Price and ingredient cost | Assumptions: ₩8,000 average bill before discounts, ingredients cost 40% of the full bill, and digital outreach has no additional cash cost in the simulation. |
| Persona sample | 100 synthetic adults aged 19+ with Seoul and Yeongdeungpo-gu as their district, from [NVIDIA Nemotron-Personas-Korea](https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea) ([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)), revision `ada0f5b53a38bb5a30cce09358adde883c1ab63a`. Sorted by UUID and took 100 rows from zero-based offset 5238 with seed 42. District indicates residence. Occupation and interests are clues about customer groups. The original fields are preserved and one-line English summaries were added. |

## 2. Reaction Rules

All numerical inputs and behavior below are simulation assumptions. Each eligible customer starts with zero fatigue.

1. **Immediate — baseline demand.** With no outreach, a customer has an 8% base chance of visiting on a dry, non-holiday weekday. Each visit generates one purchase.
2. **Immediate — outreach response.** A menu message adds 3 percentage points to the base chance. A coupon adds 2–12 points, using `0.02 + 0.10 × price sensitivity` with sensitivity on a 0–1 scale. A recipient who visits that day redeems the coupon.
3. **Random factors — weather, calendar, and chance.** Multiply the visit chance by 0.75 for rainfall of at least 5 mm, by 1.25 on weekends, and by 1.15 on Korean public holidays. Apply each applicable multiplier and draw whether each customer visits. A dry weekend public holiday has about 12 expected visits without outreach and up to about 29 expected visits if all 100 receive coupons and have maximum price sensitivity. The model assumes the café can serve this modeled demand.
4. **Immediate — transaction margin.** A visit contributes ₩4,800 at full price or ₩3,600 with the coupon. A day without a visit contributes ₩0 from that customer.
5. **Accumulating — contact fatigue.** After the decision, increase fatigue by 10 for a message or 15 for a coupon, or reduce it by 8 on a day without outreach. Keep it within 0–100. An outreach action increases opt-out risk when the updated score reaches 60 or more.
6. **Accumulating — opt-out.** At the end of the day, after outreach with an updated fatigue score of at least 60, the customer has a 10% chance of opting out for the rest of the episode. Future outreach is blocked and organic visits continue.

## 3. Customer Traits

| Trait | Unit and range | Reference points | Linked rule | Target average |
| --- | --- | --- | --- | --- |
| Price sensitivity | Unitless, 0–1 | Assumptions. At 0.2, taste and quality come first. At 0.5, the customer sometimes looks for deals. At 0.8, the customer often chooses discounted options. | Rule 2, coupon response. | 0.50. A mean between 0.45 and 0.55 is acceptable for the estimated sample. |

Use spending or value clues from each synthetic profile. When the profile provides no useful clue, keep the estimate at the midpoint and record low confidence. Age and sex are excluded from estimation.

## 4. Design Card

| Component | Design |
| --- | --- |
| Agent | Café manager choosing one outreach action for each eligible customer each morning. A shared policy makes the customer-level decisions. |
| Observation at decision time | Price sensitivity, fatigue divided by 100, outreach eligibility, weekend flag, Korean public holiday flag, and the fraction of the 30-day episode remaining. All fields are in the 0–1 range. |
| Actions | Three discrete choices ordered as no outreach, menu message, and same-day coupon. After an opt-out, the environment executes no outreach. |
| Episode | One customer's 30 consecutive days. Evaluation aggregates each window across all 100 customers. |
| Success metric | Maximize 30-day contribution profit subject to at most 5% of the starting customers opting out in a window. Contribution equals sales minus ingredient costs and discounts. |
| Weather | The actual daily rain total affects visits after the decision. The policy sees the weekend and holiday flags at decision time. |
| Initial reward | PPO v1 uses daily contribution profit divided by ₩4,800. The validation runs report unscaled contribution profit. |
| Training algorithm | PPO on CPU. The observation has six normalized fields, the action has three discrete choices, and the simulation can generate experience quickly. |

## 5. Reward

| Version | Formula | Reason |
| --- | --- | --- |
| v1 | Daily contribution profit ÷ ₩4,800. | One full-price sale earns one point. This establishes a profit-only baseline so the separate 5% opt-out limit can reveal any cost of optimizing sales in isolation. |

## 6. Change Log

Record each change, why it was made, and its result.

| Date | What Changed | Why | Result |
| --- | --- | --- | --- |
| 2026-11-09 | Created the project specification outline. | Provide a design document to fill in during later conversations. | Added the requested sections and change log. |
| 2026-11-16 | Set up Git at the workspace root to track the existing Store folder. | Save the project without creating duplicate folders or files. | Kept the original project files in place for the initial commit. |
| 2026-11-16 | Added `.env` to the repository's Git ignore rules. | Keep local environment files out of Git. | Git ignores `.env` at the repository root and in the Store folder. |
| 2026-11-16 | Practiced Git synchronization using a local remote. | Verify the workflow while keeping course changes on this computer. | Verified a test change was pushed from one practice checkout and pulled into the other. |
| 2026-11-16 | Defined Yeouido Riverside Café and its six reaction rules. | Specify the daily outreach decision and how to judge it over time. | Recorded the approved assumptions, success metric, and rules for the simulation. |
| 2026-11-16 | Set up the project with Python 3.12, Gymnasium, Stable-Baselines3, and PyTorch using uv. | Provide a reproducible local environment for the simulator and training. | Verified the dependency lock, library imports, and a PyTorch calculation on the CPU. |
| 2026-11-16 | Revised the assumed pool to 100 registered customers. | Follow the course guide's one-persona-per-customer design. | Updated the busiest-day estimates for the approved customer count. |
| 2026-11-16 | Selected and summarized 100 Korean personas in `data/personas.csv`. | Give each simulated café customer one synthetic profile from the approved district. | Verified 100 unique adult profiles and an English summary for each. |
| 2026-11-16 | Changed the assumed episode length from 90 days to 30 days. | Use the shorter duration requested by the user. | Episode length and the contribution-profit metric now use 30 days. |
| 2026-11-16 | Estimated and checked price sensitivity for the 100 personas. | Connect the coupon reaction to differences among customers. | The mean was 0.4615, with 83 low-confidence estimates. Every persona has one estimate and a recorded rationale. |
| 2026-11-16 | Added rainfall, the Korean public holiday calendar, and the fixed evaluation windows. | Reuse the same outside conditions when comparing policies. | Verified 3,653 daily records and twelve non-overlapping evaluation windows in 2025. |
| 2026-11-16 | Implemented the café environment and tested four outreach rules. | Verify the visit, profit, and opt-out rules before training. | Gymnasium checks passed. Weekly outreach gave the highest mean profit among policies within the 5% opt-out limit. |
| 2026-11-16 | Added the initial contribution-profit reward and ran a short PPO trial on CPU. | Verify training before the full run. | All 2,048 trial steps completed. |
| 2026-11-16 | Added the macOS run menu and archived two validation runs. | Keep the assumptions and results available for comparisons. | Both runs have separate history entries and byte-identical action logs. |
| 2026-11-16 | Built the local Canvas replay using the 10:00–22:00 opening hours. | Show recorded visits, rainfall, and results for the four validation policies. | Verified controls and label fit in the browser with zero console errors. |
| 2026-11-16 | Stopped at the initial PPO trial. | Follow the user's choice to defer the full training run. | The run history contains the trial timing. |
| 2026-11-16 | Moved the office and apartments inland and added a café terrace on the Han River. | Give café visitors a clear view of the water. | Verified the river view and day controls in the browser with zero console errors. |
