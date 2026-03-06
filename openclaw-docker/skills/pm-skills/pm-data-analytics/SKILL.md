---
name: pm-data-analytics
description: "Data analytics skills for FinTech PMs: cohort analysis, A/B testing, SQL queries. Use when analyzing user behavior, measuring feature impact, or making data-driven decisions in banking/payments/BNPL context."
---

# Data Analytics for FinTech

This skill collection helps FinTech PMs analyze data with attention to financial metrics, fraud patterns, and regulatory reporting requirements.

## Included Skills

### 1. cohort-analysis — Cohort Analysis & Retention
Analyze user engagement and retention by cohort.

**FinTech Cohort Applications:**
- **Onboarding Cohorts:** KYC completion rates by signup week
- **Transaction Cohorts:** Repeat purchase behavior
- **Credit Cohorts:** Repayment rates for BNPL/lending products
- **Fraud Cohorts:** Identify high-risk signup periods

**FinTech-Specific Metrics:**
- Time to first transaction
- Activation rate (first successful payment)
- 30/60/90-day retention by product
- Cohort LTV (lifetime value)
- Cohort fraud rate

**Example Usage:**
```
Use skill: cohort-analysis
Args: Analyze retention for users who completed BNPL signup in Q4 2025
```

**FinTech Cohort Analysis Output:**
```markdown
## BNPL User Retention Cohorts

### Key Findings
- Users completing KYC within 24h have 2.3x higher 30-day retention
- November 2025 cohort showed 15% lower retention (holiday shopping spike)
- Users with failed first transaction: 60% churn within 7 days

### Retention Heatmap
| Cohort | Week 1 | Week 2 | Week 4 | Week 8 |
|--------|--------|--------|--------|--------|
| Oct 2025 | 85% | 72% | 65% | 58% |
| Nov 2025 | 78% | 65% | 58% | 52% |
| Dec 2025 | 82% | 70% | 62% | - |
| Jan 2026 | 88% | 75% | - | - |

### Recommended Actions
1. Implement KYC progress nudges for users stuck >24h
2. Add first-transaction incentive to reduce post-signup drop
3. Investigate November cohort quality (acquisition channel mix)
```

---

### 2. ab-test-analysis — A/B Test Analysis
Evaluate experiments with statistical rigor for FinTech contexts.

**FinTech A/B Test Considerations:**
- **Guardrail Metrics:** Fraud rate, chargeback rate, support tickets
- **Sample Size:** Often larger due to lower conversion rates
- **Duration:** Must cover full billing cycles (30+ days for subscription)
- **Ethical Constraints:** Cannot randomize credit limits unfairly

**FinTech-Specific Test Types:**
- Checkout flow variations
- Pricing/interest rate displays
- KYC friction vs completion trade-offs
- Fraud rule adjustments
- Collection message timing

**Example Usage:**
```
Use skill: ab-test-analysis
Args: Test: 3-step vs 5-step KYC flow. Primary metric: completion rate.
```

**Important:** Financial product tests may require:
- Legal/compliance review before launch
- Equal treatment considerations (fair lending laws)
- Documentation for regulatory examination

---

### 3. sql-queries — SQL for Product Analytics
Write SQL queries for common FinTech analysis needs.

**Common FinTech Queries:**

**Transaction Metrics:**
```sql
-- Daily transaction volume and GMV
SELECT 
    DATE(created_at) as date,
    COUNT(*) as transaction_count,
    SUM(amount) as gmv,
    AVG(amount) as avg_transaction
FROM transactions
WHERE status = 'completed'
GROUP BY 1
ORDER BY 1 DESC;
```

**Fraud Analysis:**
```sql
-- Fraud rate by cohort
SELECT 
    DATE_TRUNC('month', u.created_at) as cohort_month,
    COUNT(DISTINCT u.id) as total_users,
    COUNT(DISTINCT CASE WHEN t.is_fraud THEN u.id END) as fraud_users,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN t.is_fraud THEN u.id END) / 
          COUNT(DISTINCT u.id), 2) as fraud_rate_pct
FROM users u
LEFT JOIN transactions t ON u.id = t.user_id
GROUP BY 1
ORDER BY 1;
```

**Cohort Retention:**
```sql
-- Monthly cohort retention
WITH cohorts AS (
    SELECT 
        id as user_id,
        DATE_TRUNC('month', created_at) as cohort_month
    FROM users
),
activity AS (
    SELECT 
        c.user_id,
        c.cohort_month,
        DATE_TRUNC('month', t.created_at) - c.cohort_month as periods_active
    FROM cohorts c
    JOIN transactions t ON c.user_id = t.user_id
    GROUP BY 1, 2, 3
)
SELECT 
    cohort_month,
    COUNT(DISTINCT user_id) as cohort_size,
    COUNT(DISTINCT CASE WHEN periods_active = 0 THEN user_id END) as month_0,
    COUNT(DISTINCT CASE WHEN periods_active = 1 THEN user_id END) as month_1,
    -- ... continue for more periods
FROM activity
GROUP BY 1
ORDER BY 1;
```

---

## FinTech Analytics Best Practices

### Data Privacy & Security
- Never include PII in analysis exports
- Use hashed/ tokenized identifiers for joins
- Follow data retention policies
- Document data lineage for regulatory audits

### Key Financial Metrics to Track

**Payment Products:**
- Transaction success rate
- Authorization rate
- Chargeback rate
- Fraud rate (by value and count)
- Average transaction value
- Payment method mix

**Lending/BNPL Products:**
- Application approval rate
- Default rate / delinquency
- Collection rate
- Average loan size
- Time to first repayment
- Customer acquisition cost (CAC)

**Wallet/Account Products:**
- Activation rate
- Funding rate
- Transaction frequency
- Average balance
- Cash-in/cash-out ratio

### Regulatory Reporting
Maintain analytics for:
- Transaction monitoring (AML)
- Suspicious activity reporting
- Capital adequacy calculations
- Consumer protection metrics

---

## Further Reading

- [The Product Analytics Playbook](https://www.productcompass.pm/)
- [SQL for Data Analysis](https://mode.com/sql-tutorial/)
- [Fraud Analytics Best Practices](https://www.acams.org/)
