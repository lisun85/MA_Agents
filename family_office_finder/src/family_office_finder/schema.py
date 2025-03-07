from pydantic import BaseModel, Field
from typing import List, Optional

class FamilyOfficeSchema(BaseModel):
    name: str = Field(
        description="The official name of the family office"
    )
    
    aum: Optional[str] = Field(
        default=None,
        description="The total assets under management (AUM) in dollars or a range",
        examples=["$500 million", "$1-2 billion", "Over $3 billion"]
    )
    
    founding_year: Optional[int] = Field(
        default=None,
        description="The year the family office was founded"
    )
    
    investment_focus: Optional[str] = Field(
        default=None,
        description="The overall investment approach and sectors of focus",
        examples=["Real estate and private equity", "Technology startups and growth equity"]
    )
    
    location: Optional[str] = Field(
        default=None,
        description="The primary location of the family office",
        examples=["Chicago, IL", "New York, NY"]
    )
    
    contact_info: Optional[dict] = Field(
        default=None,
        description="Contact information for the family office",
        examples=[{"address": "123 Main St, Chicago, IL", "phone": "(312) 555-1234", "email": "info@example.com"}]
    )
    
    team_members: Optional[List[dict]] = Field(
        default=None,
        description="Key team members of the family office",
        examples=[[{"name": "John Smith", "title": "CEO"}, {"name": "Jane Doe", "title": "CIO"}]]
    )
    
    website_url: Optional[str] = Field(
        default=None,
        description="The URL of the family office's website"
    )
    @classmethod
    def get_clean_schema(cls):
        # Get the base schema
        schema = cls.model_json_schema()
        
        # Create a cleaner version
        clean_schema = {
            "type": "object",
            "properties": {},
            "required": schema.get("required", [])
        }
        
        # Process each property
        for prop_name, prop_data in schema.get("properties", {}).items():
            clean_prop = {
                "type": "string",  # Simplify all types to string
                "description": prop_data.get("description", f"The {prop_name} of the family office")
            }
            clean_schema["properties"][prop_name] = clean_prop
            
        return clean_schema
    
class SimplifiedFamilyOfficeSchema(BaseModel):
    name: str = Field(description="The name of the family office")
    description: Optional[str] = Field(description="A brief description of the family office")
    location: Optional[str] = Field(description="The location of the family office")
    investment_focus: Optional[str] = Field(description="The investment focus areas")
    
    # Custom method to create a cleaner schema
    @classmethod
    def get_clean_schema(cls):
        # Get the base schema
        schema = cls.model_json_schema()
        
        # Create a cleaner version
        clean_schema = {
            "type": "object",
            "properties": {},
            "required": schema.get("required", [])
        }
        
        # Process each property
        for prop_name, prop_data in schema.get("properties", {}).items():
            clean_prop = {
                "type": "string",  # Simplify all types to string
                "description": prop_data.get("description", f"The {prop_name} of the family office")
            }
            clean_schema["properties"][prop_name] = clean_prop
            
        return clean_schema
    
family_office_schema = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "description": "The official name of the family office"
        },
        "aum": {
            "type": "string",
            "description": "The total assets under management (AUM) in dollars or a range",
            "examples": ["$500 million", "$1-2 billion", "Over $3 billion"]
        },
        "founding_year": {
            "type": "integer",
            "description": "The year the family office was founded"
        },
        "investment_focus": {
            "type": "string",
            "description": "The overall investment approach and sectors of focus",
            "examples": ["Real estate and private equity", "Technology startups and growth equity"]
        },
        "location": {
            "type": "string",
            "description": "The primary location of the family office",
            "examples": ["Chicago, IL", "New York, NY"]
        },
        "contact_info": {
            "type": "string",
            "description": "Contact information for the family office including address, phone, and email"
        },
        "team_members": {
            "type": "string",
            "description": "Key team members of the family office including names and titles"
        },
        "website_url": {
            "type": "string",
            "description": "The URL of the family office's website"
        }
    },
    "required": ["name"]
}