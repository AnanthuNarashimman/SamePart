# Start here

Plain-language summary of the whole project and everything we found. No jargon. If you read
one file in this folder, read this one. Every other file goes deeper on one piece of it.

---

## 1. What problem are we solving?

Four government companies each keep a list of every part they buy. The same steel bolt sits
on all four lists. But each company wrote it down differently.

```
CPCL:  HEX BOLT M16X80 A2-70 ISO 4014
IOCL:  Bolt, Hexagon Head, M16 x 80mm, Property Class A2-70
BPCL:  BLT HEX HD M16X80MM SS304 A2-70
NTPC:  BOLT HEX HEAD; DIA 16MM; LG 80MM; GRADE A2-70
```

Same bolt. Four different codes. No computer can tell they are the same thing.

So each company buys it separately, at a different price. One has a thousand sitting unused
in a warehouse while another orders more. Nobody can see any of this.

**That invisibility is the problem.** Not the messy text. The messy text is why the problem
exists, but the cost is the duplicate buying and the dead stock.

---

## 2. What does SamePart do?

It reads all four lists and works out which entries are secretly the same part. Then it
gives that part **one national code**, while every company keeps its own code as well.

Four things make our version different from a search engine that finds similar text.

1. **It pulls out real facts, not just words.** From `HEX BOLT M16X80 A2-70` it extracts
   diameter 16mm, length 80mm, grade A2-70, and it records which words in the description
   proved each fact. A reviewer can check our working.
2. **It gives one of four answers, not yes or no.**
   - Same part
   - Different part
   - Possibly a substitute, and here is when that substitution is safe
   - **Not enough information to decide** — so it asks instead of guessing
3. **Hard safety rules sit outside the AI and can overrule it.** If two bolts have different
   strength grades, they are different, full stop. The AI does not get a vote. These rules
   are written in a plain file a plant engineer can read and check.
4. **It never changes anyone's existing codes.** It only adds a note saying "these are the
   same part."

That last one matters more than it sounds. See section 6.

---

## 3. Where we are right now

| When | What |
|---|---|
| Around 20 September 2026 | Idea submission. **Six slides, as a PDF.** Read in 2 to 3 minutes |
| 30 September 2026 | Our college nominates teams on the portal |
| December 2026 | Grand finale. 36 hours of building |

**The thing due first is a six-slide PDF, not working software.** Our project plan is
written as a 36-hour build guide. That guide is for December. Nothing we have written so
far is shaped for the thing due in September.

Teams are exactly six people, at least one of them female. Our current plan splits work
across six to eight people, so that needs fixing.

Scoring, roughly: a quarter on technical approach, a quarter on the build plan, a fifth on
impact, a fifth on understanding the problem, a tenth on how clearly we present.

**We are strong on technical approach, weak on impact, and silent on scale.** That is two
of the five scored areas with nothing in them.

---

## 4. What our plan gets right

Do not lose these while fixing everything else.

- We record **evidence for every fact**, so decisions can be checked
- We allow the system to say **"I don't know"** instead of forcing an answer
- Safety rules live **outside** the AI where they can be audited
- We **never overwrite** anyone's existing codes
- We stop duplicates **at the moment someone creates a new part**, which is the cheapest
  place to fix the problem
- We are honest that our data is simulated

---

## 5. What is missing

The problem statement lists eight things it wants. We cover two well. Four partly. **Two
not at all.**

The two missing ones are a **dashboard showing the impact** and **connecting to their
existing SAP system**. Both are named in the problem statement, and judges treat that list
as a checklist.

Two more gaps worth knowing:

- **Units are ignored.** One company counts bolts one at a time. Another buys boxes of a
  hundred. A third buys by weight. Until you convert them, you cannot compare prices at all.
  The problem statement mentions this twice. Our design does not handle it.
- **No money anywhere.** The problem statement's benefits section is almost entirely about
  saving money. We do not calculate a single rupee. Impact is a fifth of our score.

There is a real number we can use. A government audit report on SAIL, presented to
Parliament in July 2025, found ₹12,743 crore of losses over seven years from poor
procurement and inventory management. That is an official, audited, Indian figure about a
real public sector company.

---

## 6. Three questions that can end our run

**"Will this work on our real list?"**
Our demo has 150 fake parts. Real companies have millions. Comparing everything to
everything is trillions of comparisons, which is impossible. We need to explain how we avoid
that. Right now we say nothing, and silence sounds like we never thought about it.

Our real answer is reassuring: the big cleanup happens **once**. After that we only check
each new part as it is created, which is almost free.

**"Does our data leave our building?"**
Right now our system sends part descriptions to an AI service over the internet. Oil
refineries treat this data as confidential. If that is our answer, we lose regardless of how
good the technology is.

The fix: the AI can run on their own computers. Tested on a large public benchmark, an AI
that runs locally scored 98.2 out of 100 against 99.0 for the big internet one. Almost
nobody trades privacy for that difference.

**"We already own SAP software that does this. Why do we need you?"**
Dangerous because CPCL really does run SAP, and someone in the room knows it. Do not claim
we match better. Say the true thing: their tool only works **inside one company**. It cannot
compare CPCL's list against IOCL's list. That gap is exactly our project. We work alongside
their software, not instead of it.

---

## 7. Our strongest card, which we are currently hiding

Every company that sells this kind of cleanup **deletes and merges records inside the
customer's system**. That is permanent. If they get it wrong, real data is gone. It is why
these projects frighten plant teams and stall for years.

Ours never touches anything. Every company keeps its code exactly as it was. We only add a
note saying two things are the same. If we get one wrong, **we delete the note.** Nothing is
lost.

No competitor can say that. It is already true of our design. It should be one of the first
things we say, not a technical footnote.

---

## 8. What to do next, in order

1. **Add money to the demo.** Put price and quantity on the records. Once we know which
   parts are the same, showing "four companies bought this at three different prices" is a
   simple calculation. It produces the one number a judge remembers.
2. **Handle units.** Each, box of 100, by weight. Required before any price comparison is
   even valid.
3. **Add manufacturer and part number.** If two records share a maker and a part number,
   they are the same, with no AI needed at all.
4. **Generate a clean standard description** for each part. Named in the problem statement,
   currently missing.
5. **Prepare the three answers in section 6** before anyone asks them.

---

## 9. Two ways teams lose that have nothing to do with technology

- **A live demo that needs the internet.** It will fail at the worst possible moment. Keep
  the demo path offline.
- **Presenting fake data as real.** Unrecoverable if noticed. Write "simulated data" on the
  slide ourselves, before anyone asks.

---

## Where to go next

| File | What it covers |
|---|---|
| [01](01-sih-2026-format-and-timeline.md) | Dates, slide format, scoring, team rules |
| [02](02-problem-statement-coverage.md) | The eight capabilities, scored honestly |
| [03](03-gaps-and-judge-questions.md) | All seven gaps and fourteen judge questions |
| [04](04-standards-and-precedent.md) | Codification standards, and the India precedent |
| [05](05-incumbents-and-positioning.md) | Who already sells this |
| [06](06-entity-resolution-literature.md) | The research that backs up our approach |
| [07](07-datasets.md) | What real data we can get |
| [08](08-ranked-additions.md) | What to build next, with time estimates |
| [09](09-open-decisions.md) | Decisions the team still has to make |
