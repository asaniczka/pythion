"""
Tests for the TestManager class in the make_tests module.

- Uses pytest for testing framework.
- Covers initialization and method functionality.
- Includes handling of errors for non-existent source code.
"""

import pytest
from wrapworks import cwdtoenv

cwdtoenv()

from pythion.src.make_tests import TestManager


def test_test_manager_initialization_default(mocker):
    """
    Test initializing `TestManager` with default parameters.

    Args:
        mocker: pytest mocker object to mock dependencies.

    Asserts:
        - `root_dir` is set correctly.
        - `folders_to_ignore` is initialized with `.venv` and `.mypy_cache`.
        - `indexer` is an instance of `NodeIndexer`.
    """
    root_dir = "/some/path"
    MockNodeIndexer = mocker.patch("pythion.src.make_tests.NodeIndexer")
    test_manager = TestManager(root_dir)

    assert test_manager.root_dir == root_dir
    assert test_manager.folders_to_ignore == [".venv", ".mypy_cache"]
    assert test_manager.indexer is not None
    MockNodeIndexer.assert_called_once_with(root_dir, folders_to_ignore=None)


@pytest.mark.parametrize(
    ["style", "test_type"],
    [
        ("pytest", "unit"),
        ("pytest", "intergration"),
        ("unittest", "unit"),
        ("unittest", "intergration"),
    ],
)
def test_make_tests_valid_inputs(mocker, style: str, test_type: str):
    """
    Test `make_tests` method with valid inputs.

    Args:
        mocker: pytest mocker object to mock dependencies.

    Asserts:
        - `_handle_test_generation` is called with correct parameters.
        - `pyperclip.copy` is called with the expected test case.
    """
    func_name = "some_function"
    custom_instruction = None
    test_cases = mocker.MagicMock()
    test_cases.all_test_cases_combined_to_a_single_file = "some_test_code"

    mock_input = mocker.patch("builtins.input", return_value=func_name)
    mock_handle = mocker.patch(
        "pythion.src.make_tests.TestManager._handle_test_generation",
        return_value=test_cases,
    )
    mock_copy = mocker.patch("pyperclip.copy")

    root_dir = "/some/path"
    test_manager = TestManager(root_dir)
    test_manager.make_tests(
        style=style, test_type=test_type, custom_instruction=custom_instruction
    )

    mock_input.assert_called_once_with("Enter a function or class name: ")
    mock_handle.assert_called_once_with(
        func_name, test_type, style, custom_instruction=custom_instruction
    )
    mock_copy.assert_called_once_with("some_test_code")


def test_handle_test_generation_source_code_not_found(mocker):
    """
    Test handling of error when source code cannot be located in `_handle_test_generation`.

    Args:
        mocker: pytest mocker object to mock dependencies.

    Asserts:
        - System exits with code 1 when unable to locate object in index.
    """
    function_name = "unknown_function"
    test_type = "unit"
    style = "pytest"
    custom_instruction = None

    mock_get_source = mocker.patch(
        "pythion.src.indexer.NodeIndexer.get_source_code_from_name", return_value=None
    )
    mock_generate_test = mocker.patch(
        "pythion.src.make_tests.TestManager._generate_test"
    )
    mock_generate_test = mocker.patch(
        "pythion.src.make_tests.NodeIndexer.get_dependencies",
        return_value=mocker.Mock(),
    )

    root_dir = "/some/path"
    test_manager = TestManager(root_dir)
    with pytest.raises(SystemExit):
        test_manager._handle_test_generation(
            function_name, test_type, style, custom_instruction
        )

    mock_get_source.assert_called_once_with(test_manager.indexer.index, function_name)
    mock_generate_test.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__])
