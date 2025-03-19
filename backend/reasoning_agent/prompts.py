PROMPT = """
You are an expert in analyzing companies and matching a specific set of criteria to determine if a company fits that profile. Given the information below of a company determine if the user's criteria such the sector, check size and geographical location matches this company. The top criteria's are sector and check size. The output should be yes or no.

Criteria
Sector: {sector}
Check Size: {check_size}
Geographical Location: {geographical_location}

Company Info: 
{company_info}
"""