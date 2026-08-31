import unittest
from calculator import add, subtract, multiply, divide, calculate_mean, calculate_median


class TestCalculator(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)
        self.assertEqual(add(-1, 1), 0)

    def test_subtract(self):
        self.assertEqual(subtract(5, 2), 3)

    def test_multiply(self):
        self.assertEqual(multiply(4, 3), 12)

    def test_divide(self):
        self.assertEqual(divide(10, 2), 5.0)
        with self.assertRaises(ValueError):
            divide(5, 0)

    def test_mean(self):
        self.assertEqual(calculate_mean([2, 4, 6]), 4.0)
        with self.assertRaises(ValueError):
            calculate_mean([])

    def test_median(self):
        self.assertEqual(calculate_median([1, 3, 2]), 2.0)
        self.assertEqual(calculate_median([1, 2, 3, 4]), 2.5)


if __name__ == "__main__":
    unittest.main()
