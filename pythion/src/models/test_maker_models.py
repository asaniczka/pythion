"""
This module defines Pydantic models for handling test case data.

- ItemImport: Models item imports.
- Mocks: Represents objects to be mocked in tests.
- SingleTestCase: Defines individual test case properties.
- CombinedTests: Encompasses details for multiple tests.
"""

from typing import Literal

from pydantic import BaseModel


class ItemImport(BaseModel):
    """pythion:ignore"""

    item_to_import: str | None = None
    path_of_item: str | None = None


class Mocks(BaseModel):
    """pythion:ignore"""

    what_needs_to_be_patched_or_mocked: str | list[str] | None = None
    location_of_the_object_to_mock: str | list[str] | None = None


class SingleTestCase(BaseModel):
    """pythion:ignore"""

    what_will_be_tested: str
    what_assertions_will_be_made: str | list[str]
    mocks: list[Mocks] | None
    test_case_source_code: str
    doc_string_of_the_test_case: str


class CombinedTests(BaseModel):
    """pythion:ignore"""

    type_of_test_to_build: Literal["unit test", "intergration test"]
    number_of_test_cases_required_for_full_coverage: int
    tests: list[SingleTestCase]
    imports: list[ItemImport] | None
    mocks: list[Mocks] | None
    all_test_cases_combined_to_a_single_file: str
