# pylint: disable=missing-docstring,unnecessary-lambda
import threading
import unittest

import icontract


@icontract.require(lambda: other_func())  # type: ignore
def some_func() -> bool:
    return True


@icontract.require(lambda: some_func())
def other_func() -> bool:
    return True


class TestThreading(unittest.TestCase):
    def test_two_threads(self) -> None:
        """
        Test that icontract can run in a multi-threaded environment.

        This is a regression test. The threading.local() can be only set
        immutable values. See
        http://slinkp.com/python-thread-locals-20171201.html for more details.

        Originally, this caused the exception
        `AttributeError: '_thread._local' object has no attribute [...]`.
        """

        class Worker(threading.Thread):
            def run(self) -> None:
                some_func()

        worker, another_worker = Worker(), Worker()
        worker.start()
        another_worker.start()
        worker.join()
        another_worker.join()


if __name__ == "__main__":
    unittest.main()
