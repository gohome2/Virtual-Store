# Initial PPO evaluation

All policies use the same twelve 30-day windows, customers, and seeds in 2025.
The opt-out limit is 5% in every window. Actions shown are the choices the café executed.

| Policy | Mean 30-day profit (KRW) | Mean opt-outs | Worst opt-outs | Meets limit | Mean daily visitors | Nothing | Messages | Coupons |
| --- | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: |
| PPO v1 | 1,406,000 | 75.8% | 81.0% | No | 10.1 | 17,579 | 15,033 | 3,388 |
| Do nothing | 1,184,800 | 0.0% | 0.0% | Yes | 8.2 | 36,000 | 0 | 0 |
| Request a coupon every day | 1,377,000 | 93.8% | 98.0% | No | 11.1 | 21,026 | 0 | 14,974 |
| Random outreach | 1,382,800 | 74.0% | 81.0% | No | 10.4 | 19,749 | 8,130 | 8,121 |
| Selective weekly outreach | 1,255,100 | 0.0% | 0.0% | Yes | 9.1 | 30,000 | 1,920 | 4,080 |

Difference from selective weekly outreach in mean 30-day profit: +150,900 KRW.
Reward v1 uses contribution profit alone. Actual opt-outs are evaluated against the separate limit.

## Results by season

Seasons follow Seoul's calendar. Spring is March–May, summer June–August, autumn September–November, and winter December–February.
Each 30-day window is grouped by its midpoint date. Each season contains three evaluation windows. Some windows span the transition between seasons.

| Season | PPO mean profit (KRW) | Weekly rule mean profit (KRW) | PPO worst opt-outs | Weekly rule worst opt-outs |
| --- | ---: | ---: | ---: | ---: |
| Winter | 1,440,400 | 1,274,000 | 79.0% | 0.0% |
| Spring | 1,390,000 | 1,256,000 | 77.0% | 0.0% |
| Summer | 1,354,000 | 1,228,800 | 76.0% | 0.0% |
| Autumn | 1,439,600 | 1,261,600 | 81.0% | 0.0% |
