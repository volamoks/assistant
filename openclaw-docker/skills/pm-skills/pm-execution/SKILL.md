---
name: pm-execution
description: "Product execution skills for FinTech PMs: PRDs, OKRs, roadmaps, user stories, sprint planning. Use when documenting requirements, planning releases, or managing delivery in banking/payments/BNPL context."
---

# Product Execution for FinTech

This skill collection helps FinTech PMs execute effectively with compliance, security, and regulatory requirements integrated into standard PM practices.

## Included Skills

### 1. create-prd — Product Requirements Document
Create comprehensive PRDs with FinTech-specific sections.

**FinTech PRD Additions:**
- **Compliance Requirements:** KYC, AML, PSD2, GDPR sections
- **Security Requirements:** Encryption, tokenization, fraud prevention
- **Audit Trail:** Logging requirements for regulatory review
- **Risk Assessment:** Financial and operational risk analysis

**Example Usage:**
```
Use skill: create-prd
Args: BNPL checkout integration for merchant partners
```

**FinTech Example — Section 7.2 Key Features:**
```markdown
### 7.2 Key Features

#### Core Payment Flow
- One-click BNPL option at checkout
- Real-time eligibility check (soft credit pull)
- Split payment schedule display (4 installments)
- Auto-debit setup with bank account linking

#### Compliance Features
- KYC verification with ID document upload
- AML screening integration
- Creditworthiness assessment (internal scoring)
- Regulatory disclosure display (terms, APR, fees)

#### Security Features
- PCI DSS Level 1 compliant card handling
- Tokenization for stored payment methods
- 3D Secure authentication for high-value transactions
- Fraud detection rules engine integration

#### Audit & Reporting
- Complete transaction logging for regulatory review
- Customer consent tracking and storage
- Dispute management workflow
- Chargeback handling process
```

---

### 2. brainstorm-okrs — Team OKRs
Define ambitious, measurable OKRs for FinTech teams.

**FinTech OKR Examples:**

**Objective: Reduce fraud losses while maintaining seamless UX**
- KR1: Fraud rate < 0.5% of transaction volume
- KR2: False positive rate < 2% (legitimate transactions blocked)
- KR3: KYC completion rate > 85% within 24 hours

**Objective: Achieve regulatory compliance for EU expansion**
- KR1: Obtain PSD2 license in 3 target markets
- KR2: Pass external security audit with zero critical findings
- KR3: GDPR data handling procedures documented and trained

**Usage:**
```
Use skill: brainstorm-okrs
Args: Payments team Q2 2026
```

---

### 3. outcome-roadmap — Outcome-Focused Roadmap
Transform feature lists into outcome-focused roadmaps.

**FinTech Outcome Examples:**
- **Output:** Build fraud detection ML model
- **Outcome:** Reduce fraudulent transactions by 40% while maintaining <1% false positive rate

- **Output:** Implement 3D Secure 2.0
- **Outcome:** Reduce checkout abandonment by 25% through frictionless authentication

- **Output:** Launch virtual cards feature
- **Outcome:** Enable customers to make secure online purchases without exposing primary card details, reducing fraud disputes by 30%

**Usage:**
```
Use skill: outcome-roadmap
Args: [paste current roadmap]
```

---

### 4. user-stories — Write User Stories
Create user stories with acceptance criteria for FinTech features.

**FinTech User Story Template:**
```markdown
As a [user type], I want [goal], so that [benefit]

**Acceptance Criteria:**
- [ ] Primary flow works as expected
- [ ] Error states handled gracefully
- [ ] Security requirements met
- [ ] Compliance requirements met
- [ ] Audit logging in place

**Security Considerations:**
- Data encryption at rest and in transit
- Access controls verified
- PII handling compliant with GDPR

**Compliance Checklist:**
- [ ] KYC requirements reviewed
- [ ] Regulatory disclosures included
- [ ] Consent mechanisms implemented
```

---

### 5. sprint-plan — Sprint Planning
Plan sprints with compliance and security gates.

**FinTech Sprint Planning Additions:**
- Security review column in board
- Compliance sign-off checkpoint
- Risk assessment for high-impact changes
- Rollback plan for financial features

---

### 6. test-scenarios — Define Test Scenarios
Create comprehensive test scenarios including edge cases.

**FinTech-Specific Test Categories:**
- **Happy Path:** Standard transaction flows
- **Edge Cases:** Network timeouts, partial failures
- **Security Cases:** Injection attempts, unauthorized access
- **Compliance Cases:** KYC failures, sanction list hits
- **Fraud Cases:** Velocity limits, suspicious patterns

---

## FinTech Execution Checklist

Before shipping any FinTech feature:

- [ ] Security review completed
- [ ] Compliance requirements documented
- [ ] Audit logging implemented
- [ ] Error handling covers financial edge cases
- [ ] Rollback plan tested
- [ ] Monitoring and alerting configured
- [ ] Customer support documentation updated
- [ ] Regulatory disclosures reviewed by legal

---

## Further Reading

- [Inspired by Marty Cagan](https://www.svpg.com/)
- [PCI DSS Requirements](https://www.pcisecuritystandards.org/)
- [PSD2 Strong Customer Authentication](https://www.ecb.europa.eu/paym/integration/retail/sepa/html/index.en.html)
