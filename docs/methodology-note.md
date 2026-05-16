# GCC Analyst Market Tracker - Methodology Note

## Short Version

GCC Analyst Market Tracker uses sampled online job-market data to create directional career intelligence for analyst roles across the Gulf.

It should not be read as a complete count of every analyst job in the market.

## What The Tracker Measures

The tracker converts reviewed job-market samples into aggregate signals, including:

- city and country distribution
- analyst role categories
- skill mentions
- posting freshness where available
- salary coverage where available
- dated snapshot movement after repeated pulls
- source confidence at an aggregate level

The current core tracker focuses on the UAE and Saudi Arabia. Wider Gulf coverage is being tested separately before it becomes part of the main market read.

## What The Tracker Does Not Measure

The tracker does not claim to measure the exact number of open analyst jobs in the Gulf.

Online postings can be duplicated, reposted, stale, incomplete, missing from public job boards, or displayed differently across platforms. Some hiring also happens through internal referrals, recruiters, direct outreach, offline networks, or company career pages that may not appear in sampled data.

For that reason, the dashboard should be read as directional demand intelligence, not as an official labor-market count.

## Pipeline

The current pipeline follows this flow:

1. Pull sampled job-market data from selected providers.
2. Normalize fields into consistent local CSV files.
3. Review whether each role is relevant to the analyst-market scope.
4. Remove or avoid public display of private/contact-style fields.
5. Deduplicate where possible.
6. Categorize roles by country, city, role type, and skill mentions.
7. Publish only aggregate dashboard outputs.
8. Write dated snapshot files for trend tracking.

The dashboard does not display full job listings, full job descriptions, recruiter names, emails, phone numbers, or direct application links.

## Current Snapshot

Latest core snapshot:

- Snapshot date: May 16, 2026
- Unique reviewed roles: 633
- Core countries: 2
- Core cities: 5
- Tracked skills: 31
- Previous comparison snapshot: May 9, 2026

Wider Gulf discovery is being tracked separately and should be treated as early coverage testing until repeated samples are collected.

## Movement Language

Movement labels mean newly observed reviewed roles since the previous snapshot. They should not be described as exact job-market growth.

Preferred wording:

- "newly observed since the previous snapshot"
- "in this reviewed sample"
- "appears to be"
- "directional signal"
- "reviewed roles"
- "skill mentions"
- "not a complete market count"

Avoid wording such as:

- "the most in-demand skill in the Gulf"
- "there are exactly X analyst jobs"
- "complete market view"
- "this skill guarantees a job"
- "fully representative of the market"

## Public Positioning

Best current positioning:

"GCC Analyst Market Tracker tracks sampled analyst-role demand across the Gulf and turns it into simple weekly career intelligence updates."

