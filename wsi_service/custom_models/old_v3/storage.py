from typing import List

from pydantic import ConfigDict, Field, FieldValidationInfo, field_validator

from wsi_service.models.commons import RestrictedBaseModel


class StorageAddress(RestrictedBaseModel):
    """Class representing a single storage address. This address is always assosiated with a Slide ID
    and a boolean indicating if this address is the main address for access. Additionally, an internal
    Storage Address ID needs to be set."""

    address: str = Field(
        examples=["path/to/file"],
        description="Storage address, e.g. filepath, URL, that can be accessed by the WSI Service",
    )
    slide_id: str = Field(examples=["a7981525-a465-4240-8da5-e2defae6a746"], description="Slide ID")
    main_address: bool = Field(
        examples=[True],
        description="""Boolean indicating if this entry is the main address for access.
        There can only be one main address per Slide""",
    )
    storage_address_id: str = Field(
        examples=["a30b2bd7-1160-43a1-8583-8cf39d552471"], description="Unique Storage Address ID"
    )

    __hash__ = object.__hash__

    model_config = ConfigDict(from_attributes=True)


class SlideStorage(RestrictedBaseModel):
    """Class representing slide storage used to map a Slide ID to storage addresses of a certain type.
    The storage addresses could, for example, include a number of filepaths pointing the user to all
    files needed to actually open the slide."""

    slide_id: str = Field(examples=["a7981525-a465-4240-8da5-e2defae6a746"], description="Slide ID")
    storage_type: str = Field(examples=["fs"], description="Storage type, e.g. fs for filesystem")
    storage_addresses: List[StorageAddress] = Field(
        examples=[
            [
                StorageAddress(
                    address="path/to/file",
                    main_address=True,
                    slide_id="a7981525-a465-4240-8da5-e2defae6a746",
                    storage_address_id="a30b2bd7-1160-43a1-8583-8cf39d552471",
                )
            ]
        ],
        description="List of all storages addresses",
    )
    model_config = ConfigDict(from_attributes=True)

    @field_validator("storage_addresses")
    @classmethod
    def validate_storage_addresses(cls, value, info: FieldValidationInfo):
        # check matching slide ids
        for storage_address in value:
            if storage_address.slide_id != info.data["slide_id"]:
                raise ValueError("Slide ID defined by a storage address does not match overall slide ID")
        # check only one main address
        main_address_count = 0
        for storage_address in value:
            if storage_address.main_address:
                main_address_count += 1
        if main_address_count > 1:
            raise ValueError("Only one storage address can be the main address")
        return value

