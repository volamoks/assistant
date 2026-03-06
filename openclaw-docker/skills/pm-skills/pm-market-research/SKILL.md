---
name: pm-market-research
description: "Market research skills for FinTech PMs: competitor analysis, market sizing, user personas, customer journey mapping. Use when researching markets, understanding competition, or defining target customers in banking/payments/BNPL context."
---

# Market Research for FinTech

This skill collection helps FinTech PMs conduct market research with attention to regulatory landscapes, financial customer behaviors, and competitive dynamics.

## Included Skills

### 1. competitor-analysis — Competitive Analysis
Analyze competitors in the FinTech space.

**FinTech Competitor Analysis Framework:**

**Direct Competitors:**
- Same product category (e.g., other BNPL providers)
- Same target segment
- Similar value proposition

**Indirect Competitors:**
- Traditional alternatives (credit cards, bank loans)
- Adjacent solutions (different approach to same problem)
- Future entrants (big tech, banks)

**Analysis Dimensions:**

| Dimension | What to Analyze |
|-----------|-----------------|
| **Product** | Features, UX, integration options |
| **Pricing** | Fee structure, interest rates, hidden costs |
| **Distribution** | Channels, partnerships, geographic reach |
| **Regulatory** | Licenses, compliance posture, legal issues |
| **Financial** | Funding, valuation, unit economics (if known) |
| **Brand** | Positioning, trust signals, customer sentiment |

**FinTech-Specific Competitor Factors:**
- Regulatory licenses held
- Banking partnerships
- Fraud/loss rates (if public)
- Credit underwriting approach
- API/developer experience

**Example Usage:**
```
Use skill: competitor-analysis
Args: BNPL market in Germany — analyze Klarna, PayPal Pay Later, Ratepay
```

---

### 2. market-sizing — Market Sizing
Estimate Total Addressable Market (TAM).

**FinTech Market Sizing Approaches:**

**Top-Down:**
```
TAM = Total e-commerce GMV × BNPL penetration × take rate
Example: $5T GMV × 5% BNPL × 5% take rate = $12.5B
```

**Bottom-Up:**
```
TAM = # of target merchants × avg GMV × take rate
Example: 100K merchants × $1M GMV × 5% = $5B
```

**Value-Based:**
```
TAM = Value created × willingness to pay
Example: 2% conversion lift × avg order value × merchant count
```

**FinTech Sizing Considerations:**
- Regulatory constraints by market
- Credit penetration rates
- Digital payment adoption
- Competitive intensity

---

### 3. user-personas — User Personas
Create personas for FinTech users.

**FinTech Persona Dimensions:**

**Merchant Personas:**
- SMB owner (low technical sophistication)
- Enterprise PM (complex requirements)
- Developer (API-first)

**Consumer Personas:**
- Budget-conscious (BNPL for control)
- Cash-flow constrained (BNPL for access)
- Rewards-seeker (credit card alternative)

**Trust & Risk Profile:**
- Early adopter vs. mainstream
- Risk tolerance
- Financial literacy level
- Technology comfort

**Example Persona:**
```markdown
## Persona: Sarah, E-commerce Founder

**Demographics:**
- Age: 32
- Company: $2M revenue fashion brand
- Platform: Shopify

**Goals:**
- Increase checkout conversion
- Reduce cart abandonment
- Maintain healthy cash flow

**Frustrations:**
- Current payment processor fees too high
- Limited payment options for customers
- Complex integration requirements

**Trust Factors:**
- Needs PCI compliance assurance
- Wants transparent pricing
- Values responsive support

**Quote:** "I need a payment solution that just works and doesn't surprise me with hidden fees."
```

---

### 4. customer-journey-map — Customer Journey Mapping
Map the end-to-end customer journey.

**FinTech Journey Stages:**

**Awareness:**
- How do they discover the solution?
- What triggers the search?
- What content influences them?

**Consideration:**
- What alternatives do they evaluate?
- What trust signals matter?
- What concerns do they have?

**Onboarding:**
- KYC/verification process
- First transaction experience
- Activation milestones

**Usage:**
- Regular transaction patterns
- Feature adoption
- Support interactions

**Advocacy:**
- Referral behavior
- Review/feedback
- Expansion/upsell

**FinTech Journey Friction Points:**
- KYC abandonment
- First transaction anxiety
- Security concerns
- Support response time

---

### 5. sentiment-analysis — Sentiment Analysis
Analyze customer sentiment from reviews, social, support tickets.

**FinTech Sentiment Sources:**
- App store reviews
- Trustpilot/G2 reviews
- Social media mentions
- Support ticket themes
- NPS feedback

**Key Themes to Track:**
- Trust and security
- Ease of use
- Customer service
- Pricing transparency
- Reliability/uptime

---

## FinTech Research Best Practices

### Regulatory Research
- Monitor regulatory announcements
- Track license applications
- Understand compliance requirements
- Follow industry associations

### Customer Research Ethics
- Clear consent for data collection
- Transparent about research purpose
- No financial advice during interviews
- Secure handling of financial information

### Competitive Intelligence
- Public sources (filings, press releases)
- Customer reviews and forums
- Job postings (indicate strategy)
- Patent filings
- Conference presentations

---

## Further Reading

- [Jobs to Be Done by Clayton Christensen](https://www.christenseninstitute.org/)
- [The Mom Test for Customer Research](http://momtestbook.com/)
- [CB Insights Fintech Research](https://www.cbinsights.com/research/fintech/)
