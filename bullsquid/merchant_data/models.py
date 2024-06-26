"""Defines the base model class with a default configuration."""

from pydantic import BaseModel as PydanticBaseModel, ConstrainedStr


class BaseModel(PydanticBaseModel):
    """Custom Pydantic model base class."""

    class Config:
        """
        Global pydantic model configuration options go here.
        https://pydantic-docs.helpmanual.io/usage/model_config/#options
        """

        # perform validation even on omitted fields
        validate_all = True


class Slug(ConstrainedStr):
    regex = "^[a-z0-9]+(?:-[a-z0-9]+)*$"
