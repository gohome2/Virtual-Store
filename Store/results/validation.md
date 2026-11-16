# Environment validation

Each rule used all 100 customers in 12 fixed 30-day windows in 2025.
Profit is the mean total café contribution per window. Opt-out shares are the mean and highest shares among the windows. Coupon redemptions are the total across all windows.

| Rule | Mean 30-day profit (KRW) | Mean opt-outs | Worst opt-outs | Meets opt-out limit in every window | Mean daily visitors | Busiest day | Coupon redemptions |
| --- | ---: | ---: | ---: | :---: | ---: | ---: | ---: |
| Do nothing | 1,184,800 | 0.0% | 0.0% | Yes | 8.2 | 18 | 0 |
| Request a coupon every day | 1,377,000 | 93.8% | 98.0% | No | 11.1 | 27 | 2,226 |
| Random outreach | 1,382,800 | 74.0% | 81.0% | No | 10.4 | 22 | 1,148 |
| Selective weekly outreach | 1,255,100 | 0.0% | 0.0% | Yes | 9.1 | 26 | 621 |

The weekly rule contacts opted-in customers once every seven days and rests on the other days. It chooses a coupon when its predicted contribution exceeds the contribution from a full-price visit prompted by a message.
The daily coupon rule requests a coupon for every customer. The environment executes no outreach for customers who opt out.

## Checks

- Highest mean profit: Random outreach. Highest mean profit within the 5% opt-out limit in every window: Selective weekly outreach.
- Pass: the busiest rule averaged 11.1 visitors per day. The assumed upper bound on expected daily visits is 28.7. Individual days can exceed that expectation by chance.
- Pass: under no outreach, the mean modeled visit chance on rainy weekdays was 6.0%, compared with 8.0% on dry weekdays.
- Pass: under no outreach, the mean modeled visit chance on dry weekends was 10.0%, compared with 8.0% on dry weekdays.
- Pass: under no outreach, the mean modeled visit chance on dry weekday holidays was 9.2%, compared with 8.0% on dry weekdays.
