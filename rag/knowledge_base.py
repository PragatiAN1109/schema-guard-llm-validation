"""
SchemaGuard RAG — Knowledge Base
==================================
Synthetic-but-realistic clinical and financial reference documents used
as the retrieval corpus for RAG-enhanced explanations.

Structure:
    Each document has:
        - doc_id       : unique identifier
        - domain       : "healthcare_intake" | "financial_loan_application" | "general"
        - rule_id      : which SchemaGuard rule this primarily informs (or None)
        - title        : short descriptive title
        - content      : the actual text (will be chunked)
        - source       : mock citation
"""

KNOWLEDGE_BASE = [

    # ══════════════════════════════════════════════════════════════════
    # HEALTHCARE — HC-001: Age consistency
    # ══════════════════════════════════════════════════════════════════
    {
        "doc_id": "HC-001-a",
        "domain": "healthcare_intake",
        "rule_id": "HC-001",
        "title": "Patient Age Verification in Clinical Documentation",
        "source": "CMS Conditions of Participation §482.24(c)",
        "content": """
Clinical documentation standards require that a patient's stated age be consistent with
their recorded date of birth and the date of service. The Joint Commission standard
RC.02.01.01 mandates that patient identification data — including date of birth and age —
must be reconciled at every point of care.

Age discrepancies in electronic health records (EHRs) are a recognized patient-safety
risk. A 2019 JAMA study found that age-field errors contributed to 4.7% of medication
dosing errors in paediatric and geriatric populations, where weight- and age-based
dosing is critical.

The correct formula for age at admission:
    patient_age = floor((admission_date − date_of_birth) / 365.25)

A tolerance of ±1 year is permitted to account for birthday boundary conditions
(a patient admitted the day before their birthday has not yet turned that age).
Discrepancies exceeding 2 years must be flagged for clinical review and corrected
before the record enters any downstream billing or analytics system.

Common causes of age mismatch errors:
- Manual data entry transposing birth year (1987 entered as 1978)
- Copy-paste errors from a previous admission record
- Wrong patient record selected at registration
- LLM hallucination when generating synthetic training data

Recommended remediation: cross-reference the patient's government-issued ID,
recompute age from date of birth, and update the patient_age field accordingly.
"""
    },
    {
        "doc_id": "HC-001-b",
        "domain": "healthcare_intake",
        "rule_id": "HC-001",
        "title": "Age-Based Clinical Decision Support Guidelines",
        "source": "American Health Information Management Association (AHIMA), 2022",
        "content": """
Clinical decision support (CDS) systems use patient age as a primary trigger for
age-specific care pathways. Examples include:

Paediatric dosing (<18 years): Many medications — including analgesics, antibiotics,
and anticoagulants — are dosed by weight-per-kilogram with strict age-dependent upper
bounds. An incorrect age in the 30s or 40s for a child could bypass paediatric dosing
alerts entirely.

Geriatric screening (≥65 years): CDS systems automatically trigger Beers Criteria
screening, fall-risk assessment, and polypharmacy review for patients aged 65 or older.
An under-reported age would suppress these critical safety checks.

Cancer screening thresholds: Colorectal cancer screening begins at 45 per current USPSTF
guidelines; mammography at 40–45 depending on risk. Age errors could delay or inappropriately
trigger these screenings.

For data validation purposes: if the computed age from dates differs from the stated age
by more than 1 year, the record must be treated as potentially erroneous. The stated age
field should not be used for any clinical calculations until reconciled.
"""
    },

    # ══════════════════════════════════════════════════════════════════
    # HEALTHCARE — HC-002: Temporal integrity (admit after birth)
    # ══════════════════════════════════════════════════════════════════
    {
        "doc_id": "HC-002-a",
        "domain": "healthcare_intake",
        "rule_id": "HC-002",
        "title": "Temporal Integrity Requirements for Healthcare Records",
        "source": "HL7 FHIR R4 Base Specification — Encounter Resource",
        "content": """
Healthcare record systems are required to enforce basic temporal logic across all
date fields. The HL7 FHIR standard defines the Encounter resource with mandatory
temporal constraints: the period.start (admission date) must be a valid date that
occurs after the patient's birthDate.

A record with an admission date preceding the patient's date of birth is a categorical
impossibility — it implies a patient received care before they were born. This type of
error is classified as a critical data integrity violation under ICD-10-CM Official
Guidelines for Coding and Reporting.

Common causes in EHR systems:
- Year digit transposition (e.g., 2024 → 2004 for a recent admission)
- Century rollover errors in legacy systems (00 interpreted as 1900 vs 2000)
- LLM generation artifacts where date constraints are not strictly enforced

Impact on downstream systems:
- Billing systems will reject claims with impossible dates
- Epidemiological reporting will produce negative patient-years
- Age-cohort analytics will place the patient in the wrong birth decade

Remediation: verify date_of_birth against a primary source document, correct
admission_date if the year is clearly transposed, and revalidate all date-dependent
derived fields (patient_age, length_of_stay) before reprocessing.
"""
    },

    # ══════════════════════════════════════════════════════════════════
    # HEALTHCARE — HC-003: Discharge / admission ordering
    # ══════════════════════════════════════════════════════════════════
    {
        "doc_id": "HC-003-a",
        "domain": "healthcare_intake",
        "rule_id": "HC-003",
        "title": "Discharge Date Sequencing and Length-of-Stay Calculations",
        "source": "CMS Medicare Claims Processing Manual, Chapter 1 §30.2",
        "content": """
The discharge date (also called the 'end date' in FHIR Encounter.period.end) must be
on or after the admission date (Encounter.period.start). This is a fundamental constraint
enforced by all major hospital billing systems, including Medicare's Integrated Outpatient
Code Editor (IOCE) and Inpatient Prospective Payment System (IPPS) grouper.

Length of stay (LOS) is calculated as:
    LOS = discharge_date − admission_date (in days)

A negative LOS is mathematically impossible and triggers automatic claim rejection.
Under Medicare's DRG payment system, LOS directly determines reimbursement — an LOS
error affects the geometric mean LOS used to assign the MS-DRG and its base payment rate.

In a 2021 audit of LLM-generated clinical documentation, discharge-before-admission
errors were among the top-3 most common semantic errors, occurring in approximately
12% of naively generated records that lacked explicit date-ordering constraints in
their generation prompts.

Quality indicators affected by incorrect LOS:
- Hospital-acquired condition (HAC) windows
- 30-day readmission rate calculations
- Sepsis bundle compliance tracking (requires precise time-of-admission)

Correction protocol: if discharge_date precedes admission_date, treat both dates as
suspect. Cross-reference with nursing notes, medication administration records (MARs),
and the procedure log to reconstruct the correct timeline before correcting the record.
"""
    },
    {
        "doc_id": "HC-003-b",
        "domain": "healthcare_intake",
        "rule_id": "HC-003",
        "title": "Same-Day Discharge: Valid vs Invalid Patterns",
        "source": "AHRQ Healthcare Cost and Utilization Project (HCUP) Coding Guidelines",
        "content": """
A discharge date equal to the admission date (same-day discharge) is a legitimate and
common pattern for outpatient observation stays, day surgeries, and emergency department
encounters that do not result in inpatient admission. These are not errors.

Valid same-day discharge scenarios:
- Outpatient surgical procedures (e.g., laparoscopic cholecystectomy)
- Emergency department observation without inpatient admission
- Cardiac catheterization with same-day discharge
- Chemotherapy infusion visits

Invalid patterns (requiring investigation):
- Discharge date set to a date earlier than admission date (even by one day)
- Discharge date inconsistent with documented nursing notes or medication records
- Discharge recorded as occurring before any documented diagnostic procedures

Distinction for validation systems: the validation rule should permit
discharge_date == admission_date (LOS = 0) but must reject discharge_date < admission_date
(negative LOS). The error message should clearly distinguish these two cases to avoid
false flagging of legitimate same-day discharges.
"""
    },

    # ══════════════════════════════════════════════════════════════════
    # HEALTHCARE — HC-004: Age-appropriate diagnoses
    # ══════════════════════════════════════════════════════════════════
    {
        "doc_id": "HC-004-a",
        "domain": "healthcare_intake",
        "rule_id": "HC-004",
        "title": "Age-Restricted ICD-10 Diagnosis Codes",
        "source": "ICD-10-CM FY2024 Official Guidelines for Coding and Reporting",
        "content": """
Certain ICD-10-CM diagnosis codes have explicit age restrictions defined in the
Tabular List. These are enforced by the Medicare Code Editor (MCE) and commercial
claim scrubbers.

Adult-only conditions (age ≥ 18 required):
- M81.0 (Age-related osteoporosis without pathological fracture): by definition occurs
  in individuals with age-related bone mineral density loss. Diagnosing in a child under
  18 is clinically implausible.
- E11.x (Type 2 diabetes mellitus): while Type 2 DM is increasingly diagnosed in
  adolescents, the ICD-10-CM edit for 'adult' Type 2 DM applies to patients with
  acquired insulin resistance typically seen in those ≥18.
- I25.x (Chronic ischaemic heart disease): atherosclerotic coronary artery disease
  sufficient to produce angina or ischaemia at rest is virtually absent in patients
  under 18 without genetic lipid disorders.
- N40.0 (Benign prostatic hyperplasia): by anatomy, this diagnosis applies only to
  adult males. Presence in a paediatric record indicates either a wrong diagnosis code
  or a wrong patient record.
- C61 (Malignant neoplasm of prostate): prostate cancer in males under 18 is
  exceptionally rare (<0.1% of cases) and requires pathological confirmation.

Paediatric-only/neonatal codes (age ≤ 28 days):
- P07.x (Disorders related to prematurity): P-codes are by definition perinatal.
- P59.x (Neonatal jaundice): applies only to the neonatal period.

Validation implication: assigning adult-only codes to paediatric patients (age < 18)
constitutes a diagnosis coding error that will cause claim denial and may trigger
fraud and abuse review under the False Claims Act. The record must be corrected by
either updating the diagnosis code to the age-appropriate equivalent or verifying
patient age is correctly recorded.
"""
    },

    # ══════════════════════════════════════════════════════════════════
    # HEALTHCARE — HC-005: Medication plausibility
    # ══════════════════════════════════════════════════════════════════
    {
        "doc_id": "HC-005-a",
        "domain": "healthcare_intake",
        "rule_id": "HC-005",
        "title": "Medication-Diagnosis Concordance in Clinical Documentation",
        "source": "Institute for Safe Medication Practices (ISMP), 2023 Annual Report",
        "content": """
Medication-diagnosis concordance is the principle that prescribed medications should
be clinically appropriate for the documented diagnosis. Discordance — where the
medication has no therapeutic relationship to the diagnosis — is a patient-safety
signal and a documentation quality issue.

Established diagnosis-medication pairings:
- Pneumonia (J18.x): antibiotics such as Azithromycin, Amoxicillin-clavulanate,
  Levofloxacin, or Ceftriaxone. Antifungals, antidiabetics, or cardiac medications
  are not standard treatment.
- Type 2 Diabetes (E11.x): Metformin (first-line), insulin, GLP-1 agonists, SGLT-2
  inhibitors. Antibiotics, antihypertensives, or NSAIDs do not treat hyperglycaemia.
- Hypertension (I10): ACE inhibitors, ARBs, calcium channel blockers, thiazide
  diuretics. Prescribing an antibiotic for hypertension indicates a documentation error.
- GERD (K21.x): proton pump inhibitors (Omeprazole, Pantoprazole), H2 blockers.
  Cardiovascular drugs or antibiotics do not treat acid reflux.

Common causes of medication-diagnosis mismatch in records:
- Copy-paste from a different patient encounter
- LLM generation that assigns random medications without domain-specific knowledge
- Template-filling errors in structured documentation systems

Clinical impact: a medication not matched to any active diagnosis may indicate
a missing diagnosis code (the medication is being used for an uncoded condition)
or a documentation error. Either way, the record requires clinical review before
it can be used for billing, quality reporting, or research.
"""
    },

    # ══════════════════════════════════════════════════════════════════
    # FINANCE — FN-001: Approval / application date ordering
    # ══════════════════════════════════════════════════════════════════
    {
        "doc_id": "FN-001-a",
        "domain": "financial_loan_application",
        "rule_id": "FN-001",
        "title": "Loan Approval Temporal Integrity and Regulatory Requirements",
        "source": "Regulation Z (Truth in Lending Act), 12 CFR Part 1026",
        "content": """
Under Regulation Z (12 CFR §1026.2(a)(3)), a credit decision is defined as the
creditor's decision to extend, deny, or condition credit based on a completed
application. A credit decision cannot logically precede the submission of the
application on which it is based.

Federal law (Equal Credit Opportunity Act, ECOA, 15 U.S.C. §1691) requires that
lenders notify applicants of a credit decision within 30 days of receiving a complete
application. An approval date that precedes the application date would imply:
1. The decision was made before the application was evaluated (impossible under standard
   underwriting), or
2. The date fields were entered in reverse order (data entry error), or
3. The record was retroactively created or modified after the fact.

Regulatory implications of backdated approvals:
- Violations of TILA disclosure timing requirements (3-day right of rescission)
- Potential evidence of predatory lending or fraud (approval before creditworthiness assessed)
- SEC reporting issues for publicly traded lenders (materiality of loan origination date)

Data validation requirement: approval_date must be NULL (pending) or a date ≥ application_date.
Records where approval_date < application_date must be quarantined and reviewed by
the compliance team before any downstream processing (loan booking, HMDA reporting,
or securitization).
"""
    },

    # ══════════════════════════════════════════════════════════════════
    # FINANCE — FN-002: Loan-to-income ratio
    # ══════════════════════════════════════════════════════════════════
    {
        "doc_id": "FN-002-a",
        "domain": "financial_loan_application",
        "rule_id": "FN-002",
        "title": "Loan-to-Income Ratio Guidelines and Ability-to-Repay Standards",
        "source": "CFPB Ability-to-Repay and Qualified Mortgage Standards, 12 CFR §1026.43",
        "content": """
The Consumer Financial Protection Bureau (CFPB) Ability-to-Repay (ATR) rule requires
lenders to make a reasonable, good-faith determination that a consumer has the ability
to repay a mortgage before originating the loan. Central to this determination is the
debt-to-income (DTI) ratio and the loan-to-income (LTI) ratio.

Standard industry loan-to-income benchmarks:
- Conforming mortgages (Fannie/Freddie): maximum 4–6x annual income
- Qualified Mortgage (QM) safe harbour: DTI ≤ 43% of gross monthly income
- Personal loans: 1–3x annual income for unsecured; up to 5x for secured
- Business loans: typically 2–5x documented business income
- Maximum LTI across all products: lenders rarely approve above 8–10x annual income
  without additional collateral, guarantors, or compensating factors

Extreme LTI ratios (above 15x) are categorically suspect in automated systems:
they indicate either a data entry error (comma vs period in income field), a
currency conversion error, or deliberate inflation of the loan amount. LTI ratios
above 30x are virtually never approved by regulated financial institutions.

Risk implications of extreme LTI in datasets:
- Training ML models on uncorrected extreme-LTI records biases default probability models
- Reporting extreme LTI records to HMDA creates regulatory examination risk
- Automated underwriting systems will reject these applications immediately

Remediation: verify annual_income against tax returns or pay stubs. Verify loan_amount
against the loan purpose (a $2.5M personal loan for an applicant with $45K income
is almost certainly a data entry error of magnitude, not a legitimate application).
"""
    },
    {
        "doc_id": "FN-002-b",
        "domain": "financial_loan_application",
        "rule_id": "FN-002",
        "title": "Responsible Lending Standards and Income Verification",
        "source": "OCC Comptroller's Handbook — Retail Lending, 2023",
        "content": """
Responsible lending practice requires that loan amounts be commensurate with the
borrower's demonstrated ability to repay based on verified income. The OCC
Comptroller's Handbook on Retail Lending identifies excessive loan-to-income ratios
as a concentration risk indicator.

Income verification methods by loan type:
- W-2 employees: last 2 years of W-2 forms + recent pay stubs
- Self-employed: 2 years of business and personal tax returns + YTD P&L
- Retirees: Social Security award letters + pension/IRA statements
- Students: typically require co-signer; income = $0 is permissible for student loans

Key policy thresholds by loan product:
Product               | Max LTI  | Income Verification
Conforming mortgage   | 4–6×     | Full documentation
FHA mortgage          | 4.5×     | Full documentation
VA mortgage           | 4.1×     | Full documentation
Auto loan             | 2–3×     | Often stated (W-2 verification recommended)
Unsecured personal    | 1–2×     | Stated for small amounts; full doc for >$25K
Student loan (federal)| No limit  | Need-based, not income-based

When a loan record shows LTI > 10x (SchemaGuard's maximum threshold), it almost
certainly represents a data quality error rather than a legitimate application, and
should be quarantined for manual review before any credit decision processing.
"""
    },

    # ══════════════════════════════════════════════════════════════════
    # FINANCE — FN-003: Debt-to-income ratio
    # ══════════════════════════════════════════════════════════════════
    {
        "doc_id": "FN-003-a",
        "domain": "financial_loan_application",
        "rule_id": "FN-003",
        "title": "Debt-to-Income Ratio in Consumer Lending",
        "source": "Fannie Mae Selling Guide B3-6-02, 2024",
        "content": """
The debt-to-income (DTI) ratio is the percentage of a borrower's gross monthly income
that goes toward paying debts. It is the primary underwriting metric used by
mortgage lenders to assess repayment capacity.

DTI = (total monthly debt obligations / gross monthly income) × 100%

Fannie Mae maximum DTI by product:
- Conventional: 45% (up to 50% with compensating factors such as high credit score,
  large reserves, or significant equity)
- FHA: 43% (up to 57% with certain compensating factors)
- VA: 41% guideline (no hard cap but residual income requirement applies)

SchemaGuard's threshold of 60% for existing-debt-to-annual-income represents a
conservative but reasonable upper bound for pre-application debt load. Borrowers
with existing debt already exceeding 60% of annual income are highly unlikely to
qualify for additional credit, and records showing this pattern warrant review.

High-DTI risk indicators:
- Borrower may be unable to service current obligations without new credit
- Potential for cascading default if income decreases even modestly
- Lender may have failed to verify total debt obligations (missing accounts)

Documentation required to justify high DTI:
- Detailed debt schedule with creditor names, balances, and monthly payments
- Evidence of compensating factors: high credit score (≥720), large cash reserves
  (12+ months PITI), or substantial equity in other assets
"""
    },

    # ══════════════════════════════════════════════════════════════════
    # FINANCE — FN-004: Employment length vs age
    # ══════════════════════════════════════════════════════════════════
    {
        "doc_id": "FN-004-a",
        "domain": "financial_loan_application",
        "rule_id": "FN-004",
        "title": "Employment History Verification and Child Labour Laws",
        "source": "CFPB Examination Procedures — Mortgage Origination, 2023",
        "content": """
Lenders are required under the Truth in Lending Act (TILA) and the CFPB's ATR rule
to verify employment history as part of the income verification process. Employment
length is used to assess income stability and job security.

Key employment duration constraints:
- US federal child labour law (Fair Labour Standards Act, 29 U.S.C. §212) prohibits
  employment of children under 14 for most occupations, and restricts hours for
  14–15 year olds. Full-time adult employment cannot begin before age 16.
- A 24-year-old applicant (born in 2000) cannot have more than 8 years of employment
  history (age 24 - minimum working age 16 = 8 years maximum).
- Employment beginning at age 6 or earlier is impossible under any interpretation
  of US or international labour law.

Impact on underwriting:
- Employment length directly feeds income stability scoring
- Overstated employment tenure inflates the stability score and may result in
  a better risk grade than deserved
- Employment length > (age - 16) is a categorical data integrity violation that
  should trigger immediate manual review

Common causes in datasets:
- LLM generation assigning employment_length_years without checking date_of_birth
- Copy-paste errors from a different applicant's record
- Unit errors (months entered as years, e.g., 180 months → 15 years misread as 150 years)

Remediation: verify employment history against employer verification letters (VOE forms),
tax transcripts (4506-C), and social security earnings records. Update employment_length_years
to reflect only verifiable work history.
"""
    },

    # ══════════════════════════════════════════════════════════════════
    # FINANCE — FN-005: Approved amount vs requested amount
    # ══════════════════════════════════════════════════════════════════
    {
        "doc_id": "FN-005-a",
        "domain": "financial_loan_application",
        "rule_id": "FN-005",
        "title": "Loan Approval Amounts and Counter-Offer Requirements",
        "source": "ECOA / Regulation B, 12 CFR Part 1002.9 — Adverse Action Notices",
        "content": """
Under standard lending practice and ECOA Regulation B, a lender may:
1. Approve the exact amount requested
2. Approve a lesser amount (counter-offer / conditional approval)
3. Deny the application

A lender may not approve more than was requested without the borrower explicitly
applying for a higher amount. An approved_amount exceeding loan_amount represents
one of:
(a) A data entry error (digits transposed or an extra digit added), or
(b) A system error where approval and request fields were swapped, or
(c) Evidence of predatory lending (extending more credit than requested, potentially
    without proper disclosure of the additional terms and conditions).

Regulatory implications:
- TILA requires disclosure of all credit terms before consummation; offering more
  credit than requested without redisclosure violates the right of rescission
- Under RESPA, the Loan Estimate (LE) reflects the requested amount; an approval
  above the requested amount would require a revised LE and potentially restart the
  3-day waiting period
- If the borrower is unaware that approved > requested, they may execute loan
  documents without understanding total obligations

Validation rule: approved_amount must be NULL (not yet approved), zero (fully denied),
or a value between 0 and loan_amount (inclusive). Any value exceeding loan_amount
indicates a data integrity error and the record must be quarantined.
"""
    },

    # ══════════════════════════════════════════════════════════════════
    # GENERAL: LLM output validation principles
    # ══════════════════════════════════════════════════════════════════
    {
        "doc_id": "GEN-001",
        "domain": "general",
        "rule_id": None,
        "title": "Common Failure Modes in LLM-Generated Structured Data",
        "source": "SchemaGuard Internal Technical Reference v2.0",
        "content": """
Large language models generating structured JSON data exhibit characteristic
failure modes that differ from human data-entry errors. Understanding these
patterns helps calibrate validation rules and remediation guidance.

Category 1 — Temporal consistency failures
LLMs often generate dates independently without enforcing ordering constraints.
This produces records where discharge_date < admission_date, approval_date <
application_date, or admission_date < date_of_birth. These errors are absent in
real-world data (which has real-world temporal constraints) but common in synthetic
data generated without explicit date-ordering instructions.

Category 2 — Cross-field ratio violations
Numeric fields like age, loan amounts, and employment years are generated from
independent distributions without cross-checking ratios. This produces extreme
loan-to-income values, impossible employment tenures, and age-income inconsistencies.

Category 3 — Categorical inconsistencies
Fields with semantic dependencies (diagnosis code + medication, employment status +
employer name) may be generated independently, producing implausible combinations
that pass JSON schema validation but fail semantic checks.

Category 4 — Format compliance with semantic incorrectness
LLMs reliably produce type-correct JSON (correct string formats, valid enums, proper
nulls) while failing cross-field semantic constraints. This is the core problem
SchemaGuard addresses: JSON Schema validation catches Category 0 (malformed JSON)
but misses Categories 1–3.

Downstream impact of undetected failures:
- Biased ML models trained on semantically incorrect synthetic data
- Incorrect billing claims from LLM-assisted medical coding
- Regulatory violations from AI-generated loan documents with impossible dates
- Patient safety events from incorrect medication assignments
"""
    },
]
