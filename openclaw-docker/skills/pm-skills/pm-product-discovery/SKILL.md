---
name: pm-product-discovery
description: "Product discovery skills for FinTech PMs: customer interviews, assumption identification and prioritization, experiment brainstorming. Use when conducting user research, validating product ideas, testing assumptions in banking/payments/BNPL context."
---

# Product Discovery for FinTech

This skill collection helps FinTech PMs conduct effective product discovery with compliance and regulatory considerations built-in.

## Included Skills

### 1. interview-script — Customer Interview Script
Create structured interview scripts following The Mom Test principles.

**FinTech Context:**
- Focus on financial behaviors, not just opinions
- Ask about past payment/borrowing decisions
- Explore trust and security concerns explicitly
- **Compliance Note:** Avoid questions that could be interpreted as financial advice

**Usage:**
```
Use skill: interview-script
Args: BNPL checkout experience for e-commerce merchants
```

---

### 2. identify-assumptions-new — Identify Risky Assumptions (New Products)
Map assumptions across 8 risk categories for new FinTech products.

**FinTech-Specific Risk Categories:**
- **Value:** Will customers trust us with their financial data?
- **Usability:** Can users complete KYC in under 3 minutes?
- **Viability:** Is our unit economics positive after fraud losses?
- **Feasibility:** Can we integrate with core banking systems?
- **Compliance/Regulatory:** Do we meet PSD2, GDPR, local banking regulations?
- **Go-to-Market:** Can we acquire customers under CAC targets with compliance costs?
- **Strategy:** Will open banking APIs remain accessible?
- **Team:** Do we have compliance expertise?

**Usage:**
```
Use skill: identify-assumptions-new
Args: Virtual card product for gig economy workers
```

---

### 3. prioritize-assumptions — Prioritize Assumptions
Triage assumptions using Impact × Risk matrix.

**FinTech Considerations:**
- Regulatory risks are always High Impact
- Fraud assumptions often High Risk
- Customer trust assumptions are foundational

**Usage:**
```
Use skill: prioritize-assumptions
Args: [paste your assumption list]
```

---

### 4. brainstorm-experiments-new — Design Experiments for New Products
Create experiments to validate assumptions for new FinTech products.

**FinTech Experiment Types:**
- Concierge tests for complex financial workflows
- Fake door tests for demand validation
- Wizard of Oz for compliance-heavy features
- Regulatory sandbox applications

**Usage:**
```
Use skill: brainstorm-experiments-new
Args: P2P lending platform for small businesses
```

---

### 5. summarize-interview — Synthesize Interview Findings
Extract patterns and insights from customer interviews.

**Usage:**
```
Use skill: summarize-interview
Args: [paste interview notes or upload file]
```

---

## FinTech Discovery Best Practices

### Compliance-First Interviewing
- Always disclose you're conducting product research, not giving advice
- Document consent for recording (GDPR requirement)
- Avoid collecting unnecessary PII during discovery
- Flag any financial hardship stories for compliance review

### Trust & Security Signals
In FinTech discovery, always explore:
- What would make them trust a new financial provider?
- What security concerns do they have?
- What would trigger them to abandon signup?
- How do they verify legitimacy of financial apps?

### Regulatory Context to Research
- PSD2 / Open Banking regulations (EU/UK)
- KYC/AML requirements for your product type
- Consumer credit regulations (if applicable)
- Data protection (GDPR, CCPA, local equivalents)
- Payment services licensing requirements

---

## Further Reading

- [Continuous Product Discovery Habits by Teresa Torres](https://www.producttalk.org/)
- [The Mom Test by Rob Fitzpatrick](http://momtestbook.com/)
- [PSD2 Regulatory Technical Standards](https://www.eba.europa.eu/regulation-and-policy/payment-services-and-electronic-money/regulation-payment-services-psd-2)
