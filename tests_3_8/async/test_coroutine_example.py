# pylint: disable=missing-docstring

import dataclasses
import unittest
from typing import List

import asyncstdlib as a

import icontract


class TestCoroutines(unittest.IsolatedAsyncioTestCase):
    async def test_mock_backend_example(self) -> None:
        # This is an example of a backend system.
        # This test demonstrates how contracts can be used with coroutines.

        async def has_author(identifier: str) -> bool:
            return identifier in ["Margaret Cavendish", "Jane Austen"]

        async def has_category(category: str) -> bool:
            return category in await get_categories()

        async def get_categories() -> List[str]:
            return ["sci-fi", "romance"]

        @dataclasses.dataclass
        class Book:
            identifier: str
            author: str

        @icontract.require(lambda categories: a.map(has_category, categories))
        @icontract.ensure(
            lambda result: a.all(
                a.await_each(has_author(book.author) for book in result)
            )
        )
        async def list_books(categories: List[str]) -> List[Book]:
            result = []  # type: List[Book]
            for category in categories:
                if category == "sci-fi":
                    result.extend(
                        [
                            Book(
                                identifier="The Blazing World",
                                author="Margaret Cavendish",
                            )
                        ]
                    )
                elif category == "romance":
                    result.extend(
                        [Book(identifier="Pride and Prejudice", author="Jane Austen")]
                    )
                else:
                    raise AssertionError(category)

            return result

        sci_fi_books = await list_books(categories=["sci-fi"])
        self.assertListEqual(
            ["The Blazing World"], [book.identifier for book in sci_fi_books]
        )
