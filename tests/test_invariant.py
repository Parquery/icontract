# pylint: disable=missing-docstring
# pylint: disable=invalid-name
# pylint: disable=unused-argument
# pylint: disable=no-member

import time
import unittest
from typing import Optional  # pylint: disable=unused-import

import icontract
import tests.error
import tests.mock


class TestOK(unittest.TestCase):
    def test_init(self):
        @icontract.invariant(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

        inst = SomeClass()
        self.assertEqual(100, inst.x)

    def test_instance_method(self):
        @icontract.invariant(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            def some_method(self) -> None:
                self.x = 1000

        inst = SomeClass()
        inst.some_method()
        self.assertEqual(1000, inst.x)

    def test_magic_method(self):
        @icontract.invariant(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            def __call__(self) -> None:
                self.x = 1000

        inst = SomeClass()
        inst()

        self.assertEqual(1000, inst.x)

    def test_class_method(self):
        @icontract.invariant(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            @classmethod
            def some_class_method(cls) -> None:
                pass

        inst = SomeClass()
        self.assertEqual(100, inst.x)

    def test_protected_method_may_violate_inv(self):
        @icontract.invariant(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            # A protected method is allowed to break the invariant.
            def _some_protected_method(self) -> None:
                self.x = -1

            def some_method(self) -> None:
                self._some_protected_method()
                self.x = 10

        inst = SomeClass()
        inst.some_method()

        self.assertEqual(10, inst.x)

    def test_inv_broken_before_protected_method(self):
        @icontract.invariant(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            # A protected method can not expect the invariant to hold.
            def _some_protected_method(self) -> None:
                pass

            def some_method(self) -> None:
                self.x = -1
                self._some_protected_method()
                self.x = 10

        inst = SomeClass()
        inst.some_method()
        self.assertEqual(10, inst.x)

    def test_private_method_may_violate_inv(self):
        @icontract.invariant(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            # A private method is allowed to break the invariant.
            def __some_private_method(self) -> None:
                self.x = -1

            def some_method(self) -> None:
                self.__some_private_method()
                self.x = 10

        inst = SomeClass()
        inst.some_method()
        self.assertEqual(10, inst.x)

    def test_inv_broken_before_private_method(self):
        @icontract.invariant(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            # A private method can not expect the invariant to hold.
            def __some_private_method(self) -> None:
                pass

            def some_method(self) -> None:
                self.x = -1
                self.__some_private_method()
                self.x = 10

        inst = SomeClass()
        inst.some_method()
        self.assertEqual(10, inst.x)

    def test_inv_with_empty_arguments(self):  # pylint: disable=no-self-use
        z = 42

        @icontract.invariant(lambda: z == 42)
        class A:
            pass

        _ = A()


class TestViolation(unittest.TestCase):
    def test_init(self):
        @icontract.invariant(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self, x: int) -> None:
                self.x = x

            def __repr__(self) -> str:
                return "some instance"

        _ = SomeClass(x=1)

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = SomeClass(x=0)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('self.x > 0:\n'
                         'self was some instance\n'
                         'self.x was 0', tests.error.wo_mandatory_location(str(icontract_violation_error)))

    def test_inv_as_precondition(self):
        @icontract.invariant(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            def some_method(self) -> None:
                self.x = 10

            def __repr__(self) -> str:
                return "some instance"

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            inst = SomeClass()
            inst.x = -1
            inst.some_method()
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual("self.x > 0:\n"
                         "self was some instance\n"
                         "self.x was -1", tests.error.wo_mandatory_location(str(icontract_violation_error)))

    def test_method(self):
        @icontract.invariant(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            def some_method(self) -> None:
                self.x = -1

            def __repr__(self) -> str:
                return "some instance"

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            inst = SomeClass()
            inst.some_method()
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual("self.x > 0:\n"
                         "self was some instance\n"
                         "self.x was -1", tests.error.wo_mandatory_location(str(icontract_violation_error)))

    def test_magic_method(self):
        @icontract.invariant(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            def __call__(self) -> None:
                self.x = -1

            def __repr__(self) -> str:
                return "some instance"

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            inst = SomeClass()
            inst()
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual("self.x > 0:\n"
                         "self was some instance\n"
                         "self.x was -1", tests.error.wo_mandatory_location(str(icontract_violation_error)))

    def test_multiple_invs_first_violated(self):
        @icontract.invariant(lambda self: self.x > 0)
        @icontract.invariant(lambda self: self.x < 10)
        class SomeClass:
            def __init__(self) -> None:
                self.x = -1

            def __repr__(self) -> str:
                return "some instance"

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = SomeClass()
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual("self.x > 0:\n"
                         "self was some instance\n"
                         "self.x was -1", tests.error.wo_mandatory_location(str(icontract_violation_error)))

    def test_multiple_invs_last_violated(self):
        @icontract.invariant(lambda self: self.x > 0)
        @icontract.invariant(lambda self: self.x < 10)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            def __repr__(self) -> str:
                return "some instance"

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = SomeClass()
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual("self.x < 10:\n"
                         "self was some instance\n"
                         "self.x was 100", tests.error.wo_mandatory_location(str(icontract_violation_error)))

    def test_inv_violated_after_pre(self):
        @icontract.invariant(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            @icontract.require(lambda y: y > 0)
            def some_method(self, y: int) -> None:
                self.x = -1

            def __repr__(self) -> str:
                return "some instance"

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            inst = SomeClass()
            inst.some_method(y=-1)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual("y > 0: y was -1", tests.error.wo_mandatory_location(str(icontract_violation_error)))

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            inst = SomeClass()
            inst.some_method(y=100)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual("self.x > 0:\n"
                         "self was some instance\n"
                         "self.x was -1", tests.error.wo_mandatory_location(str(icontract_violation_error)))

    def test_inv_ok_but_post_violated(self):
        @icontract.invariant(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            @icontract.ensure(lambda result: result > 0)
            def some_method(self) -> int:
                self.x = 10
                return -1

            def __repr__(self) -> str:
                return "some instance"

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            inst = SomeClass()
            inst.some_method()
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual("result > 0: result was -1", tests.error.wo_mandatory_location(str(icontract_violation_error)))

    def test_inv_violated_but_post_ok(self):
        @icontract.invariant(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            @icontract.ensure(lambda result: result > 0)
            def some_method(self) -> int:
                self.x = -1
                return 10

            def __repr__(self) -> str:
                return "some instance"

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            inst = SomeClass()
            inst.some_method()
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual("self.x > 0:\n"
                         "self was some instance\n"
                         "self.x was -1", tests.error.wo_mandatory_location(str(icontract_violation_error)))

    def test_inv_with_empty_arguments(self):
        z = 42

        @icontract.invariant(lambda: z != 42)
        class A:
            pass

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = A()
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual("z != 42: z was 42", tests.error.wo_mandatory_location(str(icontract_violation_error)))


class TestProperty(unittest.TestCase):
    def test_property_getter(self):
        @icontract.invariant(lambda self: not self.toggled)
        class SomeClass:
            def __init__(self) -> None:
                self.toggled = False

            @property
            def some_prop(self) -> int:
                self.toggled = True
                return 0

            def __repr__(self):
                return self.__class__.__name__

        some_inst = SomeClass()

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = some_inst.some_prop
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('not self.toggled:\n'
                         'self was SomeClass\n'
                         'self.toggled was True', tests.error.wo_mandatory_location(str(icontract_violation_error)))

    def test_property_setter(self):
        @icontract.invariant(lambda self: not self.toggled)
        class SomeClass:
            def __init__(self) -> None:
                self.toggled = False

            @property
            def some_prop(self) -> int:
                return 0

            @some_prop.setter
            def some_prop(self, value: int) -> None:
                self.toggled = True

            def __repr__(self):
                return self.__class__.__name__

        some_inst = SomeClass()

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_inst.some_prop = 0
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('not self.toggled:\n'
                         'self was SomeClass\n'
                         'self.toggled was True', tests.error.wo_mandatory_location(str(icontract_violation_error)))

    def test_property_deleter(self):
        @icontract.invariant(lambda self: not self.toggled)
        class SomeClass:
            def __init__(self) -> None:
                self.toggled = False

            @property
            def some_prop(self) -> int:
                return 0

            @some_prop.deleter
            def some_prop(self) -> None:
                self.toggled = True

            def __repr__(self):
                return self.__class__.__name__

        some_inst = SomeClass()

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            del some_inst.some_prop
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('not self.toggled:\n'
                         'self was SomeClass\n'
                         'self.toggled was True', tests.error.wo_mandatory_location(str(icontract_violation_error)))


class TestError(unittest.TestCase):
    def test_as_type(self):
        @icontract.invariant(lambda self: self.x > 0, error=ValueError)
        class A:
            def __init__(self) -> None:
                self.x = 0

            def __repr__(self) -> str:
                return self.__class__.__name__

        value_error = None  # type: Optional[ValueError]
        try:
            _ = A()
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertIsInstance(value_error, ValueError)
        self.assertEqual('self.x > 0:\n'
                         'self was A\n'
                         'self.x was 0', tests.error.wo_mandatory_location(str(value_error)))

    def test_as_function(self):
        @icontract.invariant(
            lambda self: self.x > 0, error=lambda self: ValueError("x must be positive, but got: {}".format(self.x)))
        class A:
            def __init__(self) -> None:
                self.x = 0

            def __repr__(self) -> str:
                return self.__class__.__name__

        value_error = None  # type: Optional[ValueError]
        try:
            _ = A()
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertIsInstance(value_error, ValueError)
        self.assertEqual('x must be positive, but got: 0', str(value_error))

    def test_as_function_with_empty_args(self):
        @icontract.invariant(lambda self: self.x > 0, error=lambda: ValueError("x must be positive"))
        class A:
            def __init__(self) -> None:
                self.x = 0

            def __repr__(self) -> str:
                return self.__class__.__name__

        value_error = None  # type: Optional[ValueError]
        try:
            _ = A()
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertIsInstance(value_error, ValueError)
        self.assertEqual('x must be positive', str(value_error))


class TestToggling(unittest.TestCase):
    def test_disabled(self):
        @icontract.invariant(lambda self: self.x > 0, enabled=False)
        class SomeClass:
            def __init__(self) -> None:
                self.x = -1

        inst = SomeClass()
        self.assertEqual(-1, inst.x)


class TestBenchmark(unittest.TestCase):
    @unittest.skip("Skipped the benchmark, execute manually on a prepared benchmark machine.")
    def test_benchmark_when_disabled(self):
        @icontract.invariant(lambda self: bool(time.sleep(5)), enabled=False)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

        class AnotherClass:
            def __init__(self) -> None:
                self.x = 100

        start = time.time()
        _ = SomeClass()
        duration_with_inv = time.time() - start

        start = time.time()
        _ = AnotherClass()
        duration_wo_inv = time.time() - start

        self.assertLess(duration_with_inv / duration_wo_inv, 1.2)


class TestInvalid(unittest.TestCase):
    def test_with_invalid_arguments(self):
        val_err = None  # type: Optional[ValueError]
        try:

            @icontract.invariant(lambda self, z: self.x > z)
            class _:
                def __init__(self) -> None:
                    self.x = 100

        except ValueError as err:
            val_err = err

        self.assertIsNotNone(val_err)
        self.assertEqual("Expected an invariant condition with at most an argument 'self', but got: ['self', 'z']",
                         str(val_err))

    def test_no_boolyness(self):
        @icontract.invariant(lambda self: tests.mock.NumpyArray([True, False]))
        class A:
            def __init__(self) -> None:
                pass

        value_error = None  # type: Optional[ValueError]
        try:
            _ = A()
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertEqual('Failed to negate the evaluation of the condition.',
                         tests.error.wo_mandatory_location(str(value_error)))
