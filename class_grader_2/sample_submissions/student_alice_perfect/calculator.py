"""Mathematics and Statistics Utility Module."""

from typing import List, Union

Number = Union[int, float]


def add(a: Number, b: Number) -> Number:
    """Adds two numbers and returns the sum."""
    return a + b


def subtract(a: Number, b: Number) -> Number:
    """Subtracts b from a and returns the result."""
    return a - b


def multiply(a: Number, b: Number) -> Number:
    """Multiplies two numbers and returns the product."""
    return a * b


def divide(a: Number, b: Number) -> float:
    """Divides a by b. Raises ValueError on division by zero."""
    if b == 0:
        raise ValueError("Cannot divide by zero.")
    return a / b


def calculate_mean(numbers: List[Number]) -> float:
    """Computes the arithmetic mean of a list of numbers."""
    if not numbers:
        raise ValueError("Cannot calculate mean of an empty list.")
    return sum(numbers) / len(numbers)


def calculate_median(numbers: List[Number]) -> float:
    """Computes the median value of a list of numbers."""
    if not numbers:
        raise ValueError("Cannot calculate median of an empty list.")
    sorted_nums = sorted(numbers)
    n = len(sorted_nums)
    mid = n // 2
    if n % 2 == 1:
        return float(sorted_nums[mid])
    return (sorted_nums[mid - 1] + sorted_nums[mid]) / 2.0
