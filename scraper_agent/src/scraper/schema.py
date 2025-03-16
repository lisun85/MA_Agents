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
        examples=["Real estate and private equity",
                  "Technology startups and growth equity"]
    )

    location: Optional[str] = Field(
        default=None,
        description="The primary location of the family office",
        examples=["Chicago, IL", "New York, NY"]
    )

    contact_info: Optional[dict] = Field(
        default=None,
        description="Contact information for the family office",
        examples=[{"address": "123 Main St, Chicago, IL",
                   "phone": "(312) 555-1234", "email": "info@example.com"}]
    )

    team_members: Optional[List[dict]] = Field(
        default=None,
        description="Key team members of the family office",
        examples=[[{"name": "John Smith", "title": "CEO"},
                   {"name": "Jane Doe", "title": "CIO"}]]
    )

    website_url: Optional[str] = Field(
        default=None,
        description="The URL of the family office's website"
    )

    media_news_coverage: Optional[List[str]] = Field(
        default=None,
        description="List of Media or news coverage summary of this family office from the last 10 years til present",
        examples=[["Company A buys B for 10 million dollars",
                   "Wall Street Journal rates company C as a buy", "Financial Times reports on company D's IPO"]]
    )

    @classmethod
    def get_clean_schema(cls):
        """
        Creates a clean JSON schema that preserves proper data types
        while removing Pydantic-specific complexities.

        This method intelligently determines types based on the field definitions
        rather than hardcoding specific field names.
        """
        # Get the base schema
        schema = cls.model_json_schema()

        # Create a cleaner version
        clean_schema = {
            "type": "object",
            "properties": {},
            "required": schema.get("required", [])
        }

        # Get the original field types from the model
        field_types = {field_name: field.annotation for field_name,
                       field in cls.model_fields.items()}

        # Process each property
        for prop_name, prop_data in schema.get("properties", {}).items():
            # Get the description
            description = prop_data.get("description", f"The {prop_name}")

            # Determine the field type from the annotation
            field_type = field_types.get(prop_name, None)

            # Check if it's a List type
            is_list = False
            list_item_type = None
            if hasattr(field_type, "__origin__") and field_type.__origin__ is list:
                is_list = True
                list_item_type = field_type.__args__[
                    0] if field_type.__args__ else None

            # Check if it's a dict type
            is_dict = False
            if hasattr(field_type, "__origin__") and field_type.__origin__ is dict:
                is_dict = True

            # Handle different property types based on the field type
            if is_list:
                # It's a list/array type
                if hasattr(list_item_type, "__annotations__"):
                    # List of objects with known structure
                    item_properties = {}
                    for item_field, item_type in list_item_type.__annotations__.items():
                        item_properties[item_field] = {
                            "type": "string",
                            "description": f"The {item_field} of the {prop_name} item"
                        }

                    clean_prop = {
                        "type": "array",
                        "description": description,
                        "items": {
                            "type": "object",
                            "properties": item_properties
                        }
                    }
                else:
                    # List of simple types or unknown structure
                    clean_prop = {
                        "type": "array",
                        "description": description,
                        "items": {
                            "type": "string"
                        }
                    }
            elif is_dict:
                # It's a dictionary/object type
                clean_prop = {
                    "type": "object",
                    "description": description,
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": f"A key in the {prop_name} object"
                        },
                        "value": {
                            "type": "string",
                            "description": f"A value in the {prop_name} object"
                        }
                    }
                }
            elif field_type is int:
                # Integer type
                clean_prop = {
                    "type": "integer",
                    "description": description
                }
            elif field_type is float:
                # Float type
                clean_prop = {
                    "type": "number",
                    "description": description
                }
            elif field_type is bool:
                # Boolean type
                clean_prop = {
                    "type": "boolean",
                    "description": description
                }
            else:
                # Default to string for other properties
                clean_prop = {
                    "type": "string",
                    "description": description
                }

            # Add examples if available
            if "examples" in prop_data:
                clean_prop["examples"] = prop_data["examples"]

            # Add the property to the schema
            clean_schema["properties"][prop_name] = clean_prop

        return clean_schema


class SimplifiedFamilyOfficeSchema(BaseModel):
    name: str = Field(description="The name of the family office")
    description: Optional[str] = Field(
        description="A brief description of the family office")
    location: Optional[str] = Field(
        description="The location of the family office")
    investment_focus: Optional[str] = Field(
        description="The investment focus areas")

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
            "type": "object",
            "description": "Contact information for the family office",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "The physical address of the family office"
                },
                "phone": {
                    "type": "string",
                    "description": "The phone number of the family office"
                },
                "email": {
                    "type": "string",
                    "description": "The email address of the family office"
                }
            }
        },
        "team_members": {
            "type": "array",
            "description": "Key team members of the family office",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the team member"
                    },
                    "title": {
                        "type": "string",
                        "description": "The title or role of the team member"
                    }
                }
            }
        },
        "website_url": {
            "type": "string",
            "description": "The URL of the family office's website"
        },
        "media_urls": {
            "type": "array",
            "description": "URLs to pages containing media coverage about the family office, including dedicated media/press pages on the company website, news articles, press releases, and award announcements. These URLs should point to pages that compile past coverage or individual media items about the organization's activities, investments, acquisitions, leadership changes, or industry recognition.",
            "items": {
                "type": "string"
            }
        }
    },
    "required": ["name"]
}
