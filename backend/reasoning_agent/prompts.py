PROMPT = """
You are an M&A investment banker evaluating potential buyers for a target company.

TARGET COMPANY INFORMATION:
- Industry: {sector}
- Services: Parking, training, maintenance, safety in the construction/real estate sector
- EBITDA: {check_size}
- Valuation: ~$25M USD
- Location: {geographical_location}

POTENTIAL BUYER INFORMATION:
{company_info}

Based on this information, is this buyer a good match for our target company?
Answer 'yes' if this buyer appears to be a potential match, or 'no' if not.
Provide only a single word answer: 'yes' or 'no'.
"""