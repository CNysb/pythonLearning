import os
from types import new_class
from pathlib import Path
import unittest
from unittest import TestCase
from unittest.mock import patch, MagicMock, Mock
import prod


class test_prod(TestCase):
    def test_set_location(self):
        prod.set_location()
        self.assertIsNotNone(prod.BASE_LOCATION)
        self.assertIsNotNone(prod.TEST_LOCATION)

    @patch("prod.Path")
    @patch("prod.os.path.join")
    def test_get_dir(self, mock_join, mock_path):
        mock_base_location = MagicMock()
        mock_path.return_value.parent.parent = mock_base_location
        mock_path.return_value.parent = MagicMock()

        mock_join.return_value = "/test/demo"

        mock_dir1 = MagicMock()
        mock_dir1.name = "test1"
        mock_dir1.is_dir.return_value = True
        mock_dir2 = MagicMock()
        mock_dir2.name = ".idea"
        mock_dir2.is_dir.return_value = True

        mock_path.return_value.iterdir.return_value = [mock_dir1, mock_dir2]
        prod.get_dir()
        self.assertEqual(len(prod.DEMO_LIST), 1)

    def test_show(self):
        with patch("builtins.print") as mock_print:
            prod.set_location()
            prod.get_dir()
            prod.show()
            self.assertTrue(mock_print.called)


if __name__ == "__main__":
    unittest.main()
