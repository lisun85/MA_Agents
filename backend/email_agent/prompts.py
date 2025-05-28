"""
Email Generation Prompts (Still Need Tuning)

This module contains prompt templates for email generation.
"""

EMAIL_PROMPT = """
Using the information provided, please create a professional email to the buyer based on this EXACT template. Do not deviate from this structure.

Required format:
Subject: Project Elevate: Premier Parking Lift Distributor Buyout Opportunity

Dear [Name],

I hope you are doing well.

We are reaching out to share an exciting buyout opportunity of a premier "parking lift" distributor with operations in the southern US ("Project Elevate").

We believe Project Elevate presents a compelling investment opportunity, supported by the following strong fundamentals:

• Recurring Service Revenue: 90% of installation customers convert into contractual service agreements; service revenue has grown at a 23% CAGR over the last four years, with a 75% gross margin.
• Secure Project Pipeline: The Target's pipeline is low risk, with $12-15M in contracted sales forecasted for 2025 and 2026.
• Proven Financial Performance: Core installation revenue has grown at a 16% CAGR, with an adjusted EBITDA margin of 30.5% over the last four years.
• High Switching Costs: Exclusive distribution rights, strong customer relationships, and best-in-class service contribute to exceptional customer retention.
• Exclusive Territory Rights: The Company holds exclusive distribution rights in the southeastern US and is well positioned for continued expansion.
• Competitive Market Position: The Target competes against three international suppliers and benefits from minor tariffs, supporting its market position.

Given the alignment with your firm's investment criteria, we wanted to share this opportunity with you.

Please see the attached teaser for your review and NDA should you wish to receive additional information about this exciting opportunity.

We are available to connect on a call to advance our discussion at your convenience.

Best regards,

[Your Name]

INSTRUCTIONS:
1. Replace [Name] with the recipient's first name or appropriate greeting based on available contact information.
2. MAINTAIN EXACT format with bullet points (•) and spacing as shown.
3. DO NOT customize or change any details about Project Elevate - use the exact text provided.
4. DO NOT add any additional sections or paragraphs not in the template.
5. DO NOT create custom or dynamic bullet points - use only those provided.
6. DO NOT mention buyer qualifications or assessment criteria in the email.
7. The subject line must always be exactly: "Project Elevate: Premier Parking Lift Distributor Buyout Opportunity"
"""