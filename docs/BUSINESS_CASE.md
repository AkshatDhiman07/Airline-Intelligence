# 💼 Business Case — Travel Intelligence Platform

> **Monetization strategy and go-to-market plan for a B2B aviation analytics SaaS**

---

## 🎯 Executive Summary

The Travel Intelligence Platform is a B2B SaaS that exposes flight delay predictions, route reliability metrics, and operational intelligence via REST API and dashboard subscriptions. The platform serves online travel agencies, corporate travel managers, travel insurance providers, and aviation operations teams.

**Pricing model:** Tiered API subscriptions + affiliate booking commissions.
**Target ACV (Annual Contract Value):** $1,200 – $60,000 depending on tier.
**Break-even:** ~25 paying customers at $499/month tier.

---

## 🧭 Market Opportunity

### Total Addressable Market (TAM)
- **Global travel technology market:** ~$11.6B (2026, est.)
- **Aviation analytics / disruption management sub-segment:** ~$500M
- **Annual U.S. flight delay economic cost:** $32.9B (FAA, 2023)

### Why the Market Needs This
1. Travel agencies lose customers to delays they could have predicted
2. Corporate travel managers spend hours manually researching reliability
3. Insurance providers price products without granular route-level risk data
4. OTAs miss conversion opportunities by not surfacing "best time to fly" guidance

The data exists (public BTS records, live flight APIs). What's missing is the **packaged intelligence layer**.

---

## 👥 Target Customers

| Segment | Profile | Pain Point | Willingness to Pay |
|---|---|---|---|
| **Mid-tier OTAs** | Booking.com competitors, regional players | Need to differentiate on reliability scoring | 🟢 High |
| **Corporate Travel Platforms** | Egencia, TripActions, SAP Concur | Want to optimize employee travel costs | 🟢 High |
| **Travel Insurance Providers** | Allianz, AIG, World Nomads | Need granular risk pricing | 🟡 Medium |
| **B2B Travel Agencies** | Mid-size agencies booking 1K+ trips/mo | Want competitive edge | 🟡 Medium |
| **Aviation Ops Teams** | Smaller airlines, charter operators | Benchmark themselves vs. industry | 🟡 Medium |

---

## 💰 Pricing Strategy

### Subscription Tiers

| Tier | Price | API Calls | Dashboard Access | Target Customer |
|---|---|---|---|---|
| **Free** | $0/mo | 100/day | View only | Hobbyists, evaluation |
| **Starter** | $99/mo | 10,000/day | 1 user, full features | Small agencies, indie consultants |
| **Pro** | $499/mo | 100,000/day | 5 users, custom reports | Mid-tier OTAs, growing platforms |
| **Enterprise** | Custom ($2K–$5K/mo) | Unlimited | Unlimited users, SLA, dedicated support, on-prem option | Large OTAs, Fortune 500 corporate travel |

### Affiliate Revenue (Secondary)
For consumer-facing integrations, the platform redirects users to partner booking sites with affiliate links:
- **Standard commission:** 2-5% of booking value
- **Average booking value:** $400
- **Per-conversion revenue:** $8-20
- Compounds well with API revenue from the same platforms

---

## 📊 Unit Economics

### Cost Structure (per 1K API calls)

| Component | Cost |
|---|---|
| AWS infrastructure (S3 + Lambda + Athena) | $0.20 |
| Data storage amortization | $0.05 |
| Bandwidth | $0.02 |
| **Total COGS** | **$0.27** |

### Revenue per 1K API Calls

| Tier | Revenue per 1K calls |
|---|---|
| Starter | $0.33 |
| Pro | $0.17 |
| Enterprise | $0.07-$0.15 |

### Gross Margin Analysis

| Tier | Gross Margin |
|---|---|
| Starter | **~17%** (acquisition tier, low margin) |
| Pro | **~38%** (sweet spot) |
| Enterprise | **~60-80%** (volume discount but fixed COGS scaled down) |

---

## 🛤️ Go-To-Market Roadmap

### Phase 1: Self-Serve Launch (Months 1-3)
- Deploy free tier + Starter tier on AWS
- Stripe integration for billing
- Developer-focused launch: ProductHunt, Hacker News, Dev.to
- **Target:** 100 free users → 10 paying (Starter)

### Phase 2: B2B Outbound (Months 4-9)
- Hire 1 founding sales/BD
- LinkedIn outbound to mid-tier OTAs and corporate travel platforms
- Conference presence (Travel Tech Summit, Phocuswright)
- **Target:** 25 paying customers across Starter/Pro/Enterprise

### Phase 3: Enterprise Expansion (Months 10-18)
- Land 3-5 enterprise contracts at $30K+ ACV
- Build dedicated integrations (Salesforce, SAP Concur)
- SOC 2 compliance (required for enterprise procurement)
- **Target:** $500K ARR

### Phase 4: Platform Expansion (Year 2+)
- International flight data (Aviationstack paid tier, OpenSky)
- Geopolitical risk scoring
- Real-time disruption alerts (Step 9)
- White-label dashboards for OTA partners
- **Target:** $2M ARR, Series A readiness

---

## 🏆 Competitive Landscape

| Competitor | Strength | Weakness | Our Edge |
|---|---|---|---|
| **FlightAware** | Real-time tracking | Consumer-focused, expensive enterprise | Better B2B pricing, ML predictions |
| **OAG** | Industry-standard schedule data | Static data, $$$$ | Modern API, affordable, ML-driven |
| **Cirium** | Comprehensive aviation analytics | Enterprise-only, slow integration | Self-serve API, fast onboarding |
| **In-house data teams** | Custom-fit | High build cost (6-12 months) | Drop-in solution, 10-day integration |

**Defensibility:** First-mover ML predictions for mid-tier B2B is unclaimed; large players ignore this segment.

---

## ⚖️ Risk Analysis

| Risk | Likelihood | Mitigation |
|---|---|---|
| Aviationstack API pricing change | Medium | Diversify: OpenSky, FlightAware as backup feeds |
| BTS data becomes paywalled | Low | Already public domain (US Code 49); unlikely |
| ML model drift | Medium | Schedule monthly retraining via CloudWatch Events |
| AWS pricing increase | Low | Multi-cloud abstraction in v2 (GCP BigQuery as alt warehouse) |
| Customer churn | Medium-High | Strong onboarding, dashboard stickiness, multi-year contracts |
| Compliance (PII in flight data) | Low | No PII handled; only aggregate operational metrics |

---

## 💡 Strategic Optionality

Beyond direct subscription revenue, the platform creates several strategic options:

1. **Acquisition target:** Aviation data companies (Cirium, FlightAware) actively acquire startups in this space
2. **Insurance partnership:** Co-develop pricing models with travel insurers in exchange for data revenue share
3. **Government/Regulator licensing:** FAA, DOT pay for aggregate industry analytics
4. **Media licensing:** Aviation publications (FlightGlobal, AINOnline) pay for trend reports

---

## 📈 3-Year Financial Projection

| Metric | Year 1 | Year 2 | Year 3 |
|---|---|---|---|
| Paying customers | 25 | 120 | 400 |
| ARR | $120K | $850K | $3.2M |
| Gross margin | 35% | 55% | 70% |
| Burn rate | $80K/mo | $120K/mo | $200K/mo |
| Headcount | 3 (founder + 2) | 8 | 20 |

*Assumes seed round at end of Year 1 ($1.5M), Series A end of Year 2 ($6M).*

---

## ✅ Why This MVP Validates the Business Case

The MVP demonstrates:

1. **The data exists and is queryable** — 3M historical records, ingested and analyzed end-to-end
2. **ML predictions are feasible** — AUC 0.67 at the published-paper baseline; productionizable
3. **The architecture is cost-efficient** — $0.40/month sustained operating cost demonstrates strong unit economics
4. **The insights are real** — *"Morning flights are 3-4x more reliable than evening"* is the kind of actionable intelligence customers will pay for
5. **The integration path is short** — REST API + JSON responses = drop-in for any modern platform

A paying customer could realistically integrate the v1 API in **< 2 days** of engineering work.

---

## 🎯 Ask (for hypothetical investors or partners)

**$500K seed round** to:
- Build dedicated REST API + production-grade dashboard
- Hire 1 founding engineer + 1 sales/BD
- Achieve $250K ARR within 12 months
- Position for $3M Series A in 18 months

**Or, equally valid:**
- Bootstrap to $50K MRR on a single founder's time
- Stay capital-efficient, retain full equity
- Focus on the Starter/Pro tiers, defer Enterprise

Both paths are viable. The data layer is now built.

---

*Built as a Master's project at Northeastern University, May 2026.*
