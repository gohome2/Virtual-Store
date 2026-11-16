# Store Replay Screen Design

> Design rules for the screen that replays the store, one decision at a time. Use it as it is for any type of business, and read the store content from project_spec.md. The bakery and the fitness club in this document are only examples.
> If this document and project_spec.md disagree, follow project_spec.md.
> Below, 'section N' means a section of project_spec.md (1 Store Definition · 2 Reaction Rules · 3 Customer Traits · 4 Design Card · 5 Reward · 6 Change Log), and 'this document, section N' means a section of this document. Field names differ a little for each student, so find the field with the same meaning.
> The replay unit follows the 'decision cycle' in section 1 (one day, one hour or one week). Below, 'today' and 'one day' mean one decision.
> If there is no replay record (JSON in public/data), or a value needed below is not in the record, do not make it up. Suggest changing the simulation so that it records the value, and ask for confirmation first.

## 1. Drawing Method

- One HTML file and Canvas 2D only, with no libraries and no image files
- Isometric miniature seen from above at an angle
- One function that turns coordinates (x, y, height) into a screen position, and one box function that paints the top, front and side faces with different brightness only; every object is built by stacking these boxes
- Drawing order set so that objects in front hide the objects behind them
- No logos or characters of real companies

## 2. Screen Layout

The canvas fills the whole window, and all controls and information sit on cards floating over the canvas. No separate button row at the top of the screen.

| Position | Content |
|---|---|
| Center | Store and neighborhood (filling the center of the screen when first opened) |
| Top left | Small card : store name, date and day of week, weather icon and temperature, day number within the episode |
| Left (below the top card) | Project card (this document, 2-1) |
| Top right | Result card (this document, section 3) |
| Bottom center | Playback bar : play and pause, previous and next, speed, date bar (one cell for every decision of the episode, cell color = weather or main metric of that day, click to jump there) |

- Cards : white, slightly transparent, rounded corners, soft shadow
- No labels or important buildings in the places covered by cards (left and top right)
- The result card can be collapsed and expanded (collapsed = title line only)
- In a narrow window, the result card moves down and the neighborhood fits the remaining space

### 2-1. Project Card

So that a first-time viewer can see at a glance what this screen is, show short and tidy information read from project_spec.md. No long sentences, only 'label : value' lines.

| Line | Value (one short line) | Example |
|---|---|---|
| Project | Store name · type of business | SMIT Bakery · neighborhood bakery |
| Decision | Section 1 repeated decision | Amount of each bread to bake every morning |
| Goal | Section 1 main metric (secondary metrics in small text) | Maximum 28-day net profit |
| Agent | Section 4 agent | Store manager |
| State | Section 4 state fields in plain words, up to 3–4, the rest as '+N more' | Customer trust · leftover bread · day off · weather +3 more |
| Action | Section 4 action and range | Number of each of 3 breads to bake (0–60 · 0–150 · 0–40) |
| Reward | Section 5 formula of the current reward version | v1 : daily net profit ÷ 100,000 |
| Step · Episode | Section 1 decision cycle · episode length | One day · 28 days |

- Keep the line order and labels of the table above, and keep each value within one line (shorten it if it overflows)
- Labels in bold dark teal, values in regular text, even spacing between lines
- At the bottom of the card, one line for the record being replayed (e.g., Playing : trained policy PPO v1)
- Expanded when first opened; collapsed = one line 'ⓘ About this project'

## 3. Result Card

Show numbers that make it possible to judge whether training worked. No graphs (reward graphs, learning curves and reward version comparison come in session 3).

- Top : record selector and episode selector (two drop-downs)
- This episode : cumulative main metric up to today (section 1 success metric) · cumulative reward (section 5 reward) · secondary metrics
- Overall training result : average main metric and average secondary metrics over all evaluation episodes in the replay record (calculated on the screen)
- Reference line : one line with the average main metric of the 'my own rule' record (the test rule the user defined) under the same evaluation conditions. Green if the selected record is better, red if worse. If that record does not exist, leave out this line and say so
- One large number (average main metric of the overall training result), the rest small
- If reward values are not in the replay record, do not make them up; suggest changing the simulation so that it records the reward of every day

## 4. Store Scene

- Neighborhood : for a store that is not a physical store (delivery, online, etc.), change to a scene that fits section 1 (e.g., delivery = delivery motorbikes moving over a neighborhood map). For a physical store, draw the place in the location and trade area of section 1 as a street model of one block. Choose the nearby buildings (e.g., offices, apartments, university, park) by the trade area written there, and add roads, crosswalks, sidewalks and street trees. No real building names or logos, only general labels such as 'Office' and 'Apartments'
- Widen the ground to fit the screen ratio. Put tall buildings behind the store, and let the sky appear naturally behind those buildings (no separate sky band)
- Focus : the eye goes to the store. The store stands out most on the screen, and nearby buildings and roads stay in the background without hiding or overwhelming the store
- Scale : when first opened, view from far enough to see the whole neighborhood. The store takes about 1/3 of the screen width, and people are about as tall as the shelves (people never look larger than the shelves)
- Store : one building in the center of the neighborhood, roof removed to show the inside, a different floor color for each area. The sign is attached to the store wall with the store name (not replaced by a floating label)
- Customer paths : customers walk in from where the main customers of section 1 live or work, enter the store and leave (e.g., weekday office workers from the office side, weekend residents from the apartment side)
- Products and facilities : the products and facilities in section 1 (type of business, action options, price and cost, etc.) and in the section 2 reaction rules. Make the amount that changes with the decision visible (e.g., bakery = bread left on the shelves, fitness club = machines in use, free machines and a waiting line), with the label 'current amount/prepared amount'
- People : small miniatures with natural body proportions (no oversized heads)
- Customer appearance : drawn to match the customer persona file named in section 1 (e.g., data/personas.csv) and the section 3 customer traits. Use the fields of the persona file (e.g., sex, age, occupation, family type) to choose height, hairstyle, clothes and items (e.g., office worker in their 20s = shirt, ID badge, coffee; working parent in their 40s = casual clothes, shopping bag, holding a child's hand; resident in their 60s = vest, walking stick). Pick the customers on the screen from the personas, and never place the same look side by side. If the replay record has the number of customers per group, use it; if not, set the ratio by the group multipliers in the section 2 rules; if there are no multipliers either, pick evenly
- Customer results : show the kinds of customer results in the section 2 rules with a small mark above the head and a speech bubble, not with clothing color (e.g., bakery = bought what they wanted · bought something else · could not buy; fitness club = used right away · used after waiting · left)
- Staff : clothes that fit the type of business in section 1 (e.g., bakery = apron and baker's hat, fitness club = trainer sportswear)
- Speech bubbles : a short line that fits the customer's result, skipped when overlapping, up to 7 at a time

## 5. Weather

Draw weather only when it affects the store.

- Condition : only when a section 2 reaction rule has a line in which weather changes customer numbers, purchases or rewards, and the public/data replay record has weather values. If either is missing, add no weather effects and always draw a clear sky
- Location check : before drawing weather, check that the location of the weather data (latitude and longitude in the code that downloads the weather) is in the same area as the location and trade area of section 1, and report the result. If they differ, do not fix it, only report it
- Use only the weather types and thresholds written in project_spec.md (section 1 external factors and the weather thresholds of the section 2 reaction rules; never invent new thresholds). All other days are clear
- Classify the weather of each day by the real weather record in public/data
- When several weather types overlap, draw only the one with the larger effect on customers in the section 2 reaction rules
- Make what the weather changes in section 2 visible on the screen (e.g., customers ×0.8 on bad-weather days = fewer customers visible that day, and weather talk in the speech bubbles)
- Effect examples (draw only the types in the specification; other types in the same way) :
  - Rain : rain streaks, puddles on the ground, customers with umbrellas
  - Snow : snowflakes, white layers on the ground, roofs and trees
  - Heat wave : yellowish sky, heat haze
  - Cold wave : visible breath, thick clothes
  - Dust : hazy sky, masks
  - Clear : a few clouds drifting slowly

## 6. Day and Night

Make the passing of time visible as the replay of one day goes on.

- Turn the replay progress of the day (0–1) into a time of day : start = morning opening, end = night after closing (use the opening hours in project_spec.md if they exist; if not, ask the user before building, write them into section 1, and then use them)
- Time moves in 1-minute steps (no jumps of 5 or 10 minutes). 1× speed = 1 store minute per screen second; speed chosen from 1×, 10×, 30× and 60× (at 60×, one day takes about 15 seconds)
- Sky : light orange in the morning → blue at midday → sunset in the evening (orange and pink) → navy at night, with smooth color changes
- Sun and moon : the sun rises and sets in the sky behind the buildings, and the moon and stars come out after sunset. Even when buildings hide the sun, tint the whole scene so that the time can be felt (morning pale orange, midday clear, evening sunset pink and orange, night dark navy)
- Scene brightness : at night, darken the whole scene, and light up windows, signs and street lights
- With weather (only when the conditions of this document, section 5 are met) : on rainy and snowy days, clouds cover the sun and the sky turns grayer
- Show the current time on the top-left card, and let the weather icon follow the time (the moon on clear days after sunset)

## 7. Colors and Text

- Except for the sky, calm colors : dark teal (trained policy, emphasis), warm wood (furniture), cream (floor)
- Result colors : got what they wanted = green, second best = orange, failure or loss = red (same colors for graphs and marks above heads)
- All text in English, system sans-serif font, labels as small white tags

## 8. Check

Check only once to save usage. The user asks separately for further fixes after looking at the screen.

- Save 1 screenshot in results/screenshots/
- In that screenshot, look for cut-off text (including text in cards), overlaps, items outside the screen and empty areas, and fix them once
- No new screenshot after the fix
- At the end, report the file path, the number of browser console errors and any problems left unfixed
