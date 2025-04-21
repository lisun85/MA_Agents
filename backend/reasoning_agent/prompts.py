PROMPT = """
You are an M&A investment banker who's selling a target company, a company that provides customers with parking, training, maintenance, 
safety in the construction/real estate sector with 4.5M EBITDA, valued at ~25M USD, and located in Southern US (North America). The target 
company's clients consist of condos, hotels, office buildings and ANY property that wants to optimize parking.

Below is detailed information about {COMPANY_NAME}:

{COMPANY_INFO}

Based on all the information above, is {COMPANY_NAME} a potential buyer for the target company? 

Your response must include:
1. An explicit answer line starting with "Answer:" that states either "Strong Buyer", "Medium Buyer", or "Not Buyer"
2. Your detailed reasoning for this assessment
3. The company's URL (e.g., {COMPANY_NAME}.com)
4. If available, list team members with their title and contact email

Please provide your analysis in a structured format.
"""