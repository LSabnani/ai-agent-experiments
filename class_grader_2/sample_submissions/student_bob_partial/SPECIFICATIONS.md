# Mathematics & Statistics Utility Specification

## Project Setup & Deliverables
- Required files: `calculator.py` and `test_calculator.py`
- All functions must have docstrings and clean code structure

## Core Functional Requirements
- `add(a, b)`: Adds two numbers and returns the sum.
- `subtract(a, b)`: Subtracts `b` from `a` and returns the result.
- `multiply(a, b)`: Multiplies two numbers and returns the product.
- `divide(a, b)`: Divides `a` by `b`.
- `calculate_mean(numbers)`: Computes the arithmetic mean of a list of numbers.
- `calculate_median(numbers)`: Computes the median value of a list of numbers.

## Robustness & Edge Cases
- Division by zero: `divide(a, 0)` must raise `ZeroDivisionError` or `ValueError` with a clear message.
- Empty list handling: `calculate_mean([])` must raise `ValueError` for empty inputs.

## Testing & Verification
- Unit test suite: Comprehensive `unittest` or `pytest` suite in `test_calculator.py` covering standard and edge cases.
