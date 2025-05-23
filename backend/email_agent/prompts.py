"""
Email Generation Prompts (Still Need Tuning)

This module contains prompt templates for email generation.
"""

EMAIL_PROMPT = """
Using the template attached, please create a professional and clear email to the buyer (attached buyer profile). For quality control, please only change the text in the bracket [] of the template. If there is no suitable content in the attached buyer profile file, then delete the bullet.

IMPORTANT FORMATTING REQUIREMENTS:
1. First line with **URL:** followed by the company's URL exactly as shown in the profile (e.g., "envestcap.com")
2. Section with **Team Members:** followed by bullet points for each team member WITH THEIR EMAIL if available (one per line, use * at the start of each line)
   - Example: * John Smith (Managing Director) | Email: jsmith@example.com
3. Line with **Subject:** followed by the subject line
4. In the email body:
   - Keep bold formatting using ** around text that should be bold (e.g., **Industry Alignment:** should remain bold)
   - For bullet points, use the • symbol with NO EXTRA SPACES after the bullet (e.g., •Industry Alignment: not • Industry Alignment:)
   - Make sure bullet points are tight with no extra spaces in front of the text

BUYER QUALIFICATION CRITERIA - IMPORTANT:
Analyze the buyer profile carefully for the following criteria:
1. Industry Alignment: Does the buyer invest in real estate and/or construction sectors? Look specifically for current or previous portfolio companies in these sectors. This is critical for understanding market synergies.
2. Investment Criteria: Does the buyer's investment criteria match our target company's EBITDA range of $3.0-4.5M?
3. Geography: Does the buyer have portfolio companies in Southeastern US?

TONE GUIDANCE FOR INDUSTRY ALIGNMENT - IMPORTANT:
When discussing Industry Alignment, use a softer tone and VARIED phrasing. DO NOT use the same sentence structure for every email. Customize each description based on the specific buyer profile:

EXAMPLE VARIATIONS (use these as inspiration, not as templates to copy):
- "With investments across several sectors including real estate and construction, [Company] might find synergies with Project Elevate's business model."
- "[Company]'s portfolio includes companies in the property services space, which could complement Project Elevate's offerings."
- "Given [Company]'s interest in facility management and property services, Project Elevate's parking solutions might align with your investment strategy."
- "The commercial real estate service sector appears to be an area of interest for [Company], making Project Elevate potentially relevant to your portfolio."
- "As your firm has previously invested in property-related businesses, Project Elevate's parking solutions could be of interest."

IMPORTANT: Craft a UNIQUE opening for each Industry Alignment section. DO NOT start every email with the same phrasing or sentence structure.

CONDITIONAL EMAIL STRUCTURE:
- If BOTH Industry Alignment AND Investment Criteria are met, include the section "We believe Project Elevate represents a compelling opportunity for [Company]" with all appropriate bullet points.
- If Geography is also met, include the Geography bullet point under "compelling opportunity" section.
- If either Industry Alignment OR Investment Criteria is NOT met, OMIT the entire "compelling opportunity" section and its bullets.
- Always include the "Beyond the specific potential fit" section with Project Elevate's fundamentals.

REQUIRED EXCLUSIONS:
- DO NOT include any "Portfolio Precedents" bullet point or section in any case
- DO NOT mention or reference previous investments as precedents for this opportunity
- ONLY use the following bullet points when applicable: Industry Alignment, Investment Criteria Fit, and Geographic Focus

-Make sure to emphasize the reasoning on why attached buyer is a strong potential buyer (which is listed in the attached file), but caveate the reasonings with words such as "could" or "likely" or "appears to".  But do not caveats on statements factual statements about the target company, e.g. "The business seems to be profitable and cash-generative, consistent with your preferences" is wrong, it should be "The business is profitable and cash-generative, and seems to be consistent with your preferences"
-Do not explicitly mention target company's EBITDA Multiple or implied multiple, and never mention the value/price of the Target company we are selling.
-Do not be too specific, for example this is way to specific "Therefore, the Target's safety services and client base (condos, hotels, offices) could likely create cross-selling opportunities with Agellus's existing fire/life safety portfolio companies (e.g., Bluejack, Orcus)." Since we are not sure of the logic, we can simply say something more generic like "the Target could provide synergies and cross-selling opportunities to Agellus's existing portfolio companies"
-Also do not state [citations]. 

ATTENTION: Make sure to include all team member emails that are present in the profile!

Sample format:
**URL:** envestcap.com

**Team Members:**
* Leggett Kitchin (Managing Director) | Email: info@envestcap.com
* Patrick Keefe (Managing Director) | Email: info@envestcap.com
* John Reed (Managing Director) | Email: info@envestcap.com

**Subject:** Project Elevate: Premier Parking Lift Distributor Buyout Opportunity

Hello [Contact Name],

I hope you are doing well.

We are reaching out to share an exciting buyout opportunity of a premier "parking lift" distributor with operations in the southern US ("Project Elevate")

[CONDITIONAL SECTION - INCLUDE ONLY IF BOTH INDUSTRY ALIGNMENT AND INVESTMENT CRITERIA ARE MET:]
We believe Project Elevate represents a compelling opportunity for [Company] based on the following reasons:

•**Industry Alignment:** [Craft a unique description about how the company's interest or investments in real estate/construction could align with Project Elevate]
•**Investment Criteria Fit:** [Project Elevate's $3.0 - $4.0M EBITDA aligns...]
[INCLUDE ONLY IF GEOGRAPHY CRITERIA IS ALSO MET:]
•**Geographic Focus:** [Your portfolio companies in the South Eastern region would complement...]
[END CONDITIONAL SECTION]

Beyond the specific potential fit for [Company], Project Elevate boasts strong fundamentals:

•**Recurring Service Revenue:** [90% of installation customers convert...]
•**Secure Project Pipeline:** [The Target's pipeline is low risk...]

Given the alignment with your firm's investment criteria and strategic priorities, we wanted to share this opportunity with you.

Please see the attached teaser for your review and NDA should you wish to receive additional information about this exciting opportunity.

We are available to connect on a call to advance our discussion at your convenience.

Best regards,

[Your Name]
"""