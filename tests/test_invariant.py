# pylint: disable=missing-docstring
# pylint: disable=invalid-name
# pylint: disable=unused-argument
# pylint: disable=no-member
import textwrap
import time
import unittest
from typing import Dict, Iterator, Mapping, Optional, Any, NamedTuple  # pylint: disable=unused-import

import icontract
import tests.error
import tests.mock


class TestOK(unittest.TestCase):
    def test_init(self) -> None:
        @icontract.invariant(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

        inst = SomeClass()
        self.assertEqual(100, inst.x)

    def test_instance_method(self) -> None:
        @icontract.invariant(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            def some_method(self) -> None:
                self.x = 1000

        inst = SomeClass()
        inst.some_method()
        self.assertEqual(1000, inst.x)

    def test_unbound_instance_method_with_self_as_kwarg(self) -> None:
        @icontract.invariant(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            def some_method(self) -> None:
                self.x = 1000

        inst = SomeClass()

        func = inst.some_method.__func__  # type: ignore

        func(self=inst)

    def test_magic_method(self) -> None:
        @icontract.invariant(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            def __call__(self) -> None:
                self.x = 1000

        inst = SomeClass()
        inst()

        self.assertEqual(1000, inst.x)

    def test_class_method(self) -> None:
        @icontract.invariant(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            @classmethod
            def some_class_method(cls) -> None:
                pass

        inst = SomeClass()
        self.assertEqual(100, inst.x)

    def test_static_method(self) -> None:
        # Adapted from https://github.com/Parquery/icontract/issues/186
        @icontract.invariant(lambda self: A.some_static_method(self.x))
        @icontract.invariant(lambda self: self.some_instance_method())
        class A:
            def __init__(self) -> None:
                self.x = 10

            def some_instance_method(self) -> bool:
                # We need this instance method for easier debugging.
                return self.x < 100

            @staticmethod
            def some_static_method(x: int) -> bool:
                return x > 0

        _ = A()

    def test_inherited_static_method(self) -> None:
        @icontract.invariant(lambda self: A.some_static_method(self.x))
        @icontract.invariant(lambda self: self.some_instance_method())
        class A:
            def __init__(self) -> None:
                self.x = 10

            def some_instance_method(self) -> bool:
                # We need this instance method for easier debugging.
                return self.x < 100

            @staticmethod
            def some_static_method(x: int) -> bool:
                return x > 0

        # We need to test for inheritance.
        # See https://stackoverflow.com/questions/14187973/#comment74562120_37147128
        class B(A):
            pass

        _ = B()

    def test_protected_method_may_violate_inv(self) -> None:
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

    def test_inv_broken_before_protected_method(self) -> None:
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

    def test_private_method_may_violate_inv(self) -> None:
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

    def test_inv_broken_before_private_method(self) -> None:
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

    def test_inv_with_empty_arguments(self) -> None:  # pylint: disable=no-self-use
        z = 42

        @icontract.invariant(lambda: z == 42)
        class A:
            pass

        _ = A()

    def test_no_dict_pollution(self) -> None:
        testSelf = self

        @icontract.invariant(lambda self: self.mustHold())
        class A:
            def mustHold(self) -> bool:
                testSelf.assertDictEqual({}, self.__dict__)
                return True

        _ = A()

    def test_new_exempted(self) -> None:
        # This test is related to the issue #167.
        new_call_counter = 0
        init_call_counter = 0

        @icontract.invariant(lambda self: True)
        class Foo:
            def __new__(cls, *args, **kwargs) -> 'Foo':  # type: ignore
                nonlocal new_call_counter
                new_call_counter += 1
                return super(Foo, cls).__new__(cls)  # type: ignore

            def __init__(self) -> None:
                nonlocal init_call_counter
                init_call_counter += 1

        _ = Foo()
        self.assertEqual(1, new_call_counter)
        self.assertEqual(1, init_call_counter)

    def test_subclass_of_generic_mapping(self) -> None:
        # This test is related to the issue #167.
        counter = 0

        def increase_counter(self: Any) -> bool:
            nonlocal counter
            counter += 1
            return True

        @icontract.invariant(increase_counter)
        class Foo(Mapping[str, int]):
            def __init__(self, table: Dict[str, int]) -> None:
                self._table = table

            def __getitem__(self, key: str) -> int:
                return self._table[key]

            def __iter__(self) -> Iterator[str]:
                return iter(self._table)

            def __len__(self) -> int:
                return len(self._table)

            def __str__(self) -> str:
                return '{}({})'.format(self.__class__.__name__, self._table)

        f = Foo({'a': 1})  # test the constructor
        _ = f['a']  # test __getitem__
        _ = iter(f)  # test __iter__
        _ = len(f)  # test __len__
        _ = str(f)  # test __str__

        # 1 invariant check after the constructor +
        # 4 checks before the methods +
        # 4 checks after the methods.
        self.assertEqual(9, counter)


class TestViolation(unittest.TestCase):
    def test_init(self) -> None:
        @icontract.invariant(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self, x: int) -> None:
                self.x = x

            def __repr__(self) -> str:
                return "some instance"

        _ = SomeClass(x=1)

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = SomeClass(x=0)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual('self.x > 0:\n'
                         'self was some instance\n'
                         'self.x was 0', tests.error.wo_mandatory_location(str(violation_error)))

    def test_inv_as_precondition(self) -> None:
        @icontract.invariant(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            def some_method(self) -> None:
                self.x = 10

            def __repr__(self) -> str:
                return "some instance"

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            inst = SomeClass()
            inst.x = -1
            inst.some_method()
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual("self.x > 0:\n"
                         "self was some instance\n"
                         "self.x was -1", tests.error.wo_mandatory_location(str(violation_error)))

    def test_method(self) -> None:
        @icontract.invariant(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            def some_method(self) -> None:
                self.x = -1

            def __repr__(self) -> str:
                return "some instance"

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            inst = SomeClass()
            inst.some_method()
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual("self.x > 0:\n"
                         "self was some instance\n"
                         "self.x was -1", tests.error.wo_mandatory_location(str(violation_error)))

    def test_magic_method(self) -> None:
        @icontract.invariant(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            def __call__(self) -> None:
                self.x = -1

            def __repr__(self) -> str:
                return "some instance"

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            inst = SomeClass()
            inst()
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual("self.x > 0:\n"
                         "self was some instance\n"
                         "self.x was -1", tests.error.wo_mandatory_location(str(violation_error)))

    def test_multiple_invs_first_violated(self) -> None:
        @icontract.invariant(lambda self: self.x > 0)
        @icontract.invariant(lambda self: self.x < 10)
        class SomeClass:
            def __init__(self) -> None:
                self.x = -1

            def __repr__(self) -> str:
                return "some instance"

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = SomeClass()
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual("self.x > 0:\n"
                         "self was some instance\n"
                         "self.x was -1", tests.error.wo_mandatory_location(str(violation_error)))

    def test_multiple_invs_last_violated(self) -> None:
        @icontract.invariant(lambda self: self.x > 0)
        @icontract.invariant(lambda self: self.x < 10)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            def __repr__(self) -> str:
                return "some instance"

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = SomeClass()
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual("self.x < 10:\n"
                         "self was some instance\n"
                         "self.x was 100", tests.error.wo_mandatory_location(str(violation_error)))

    def test_inv_violated_after_pre(self) -> None:
        @icontract.invariant(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            @icontract.require(lambda y: y > 0)
            def some_method(self, y: int) -> None:
                self.x = -1

            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            inst = SomeClass()
            inst.some_method(y=-1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent("""\
                y > 0:
                self was an instance of SomeClass
                y was -1"""), tests.error.wo_mandatory_location(str(violation_error)))

        violation_error = None
        try:
            inst = SomeClass()
            inst.some_method(y=100)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent("""\
                self.x > 0:
                self was an instance of SomeClass
                self.x was -1"""), tests.error.wo_mandatory_location(str(violation_error)))

    def test_inv_ok_but_post_violated(self) -> None:
        @icontract.invariant(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            @icontract.ensure(lambda result: result > 0)
            def some_method(self) -> int:
                self.x = 10
                return -1

            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            inst = SomeClass()
            inst.some_method()
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent("""\
                result > 0:
                result was -1
                self was an instance of SomeClass"""), tests.error.wo_mandatory_location(str(violation_error)))

    def test_inv_violated_but_post_ok(self) -> None:
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

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            inst = SomeClass()
            inst.some_method()
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual("self.x > 0:\n"
                         "self was some instance\n"
                         "self.x was -1", tests.error.wo_mandatory_location(str(violation_error)))

    def test_inv_with_empty_arguments(self) -> None:
        z = 42

        @icontract.invariant(lambda: z != 42)
        class A:
            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = A()
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent("""\
                z != 42:
                self was an instance of A
                z was 42"""), tests.error.wo_mandatory_location(str(violation_error)))

    def test_condition_as_function(self) -> None:
        def some_condition(self: 'A') -> bool:
            return self.x > 0

        @icontract.invariant(some_condition)
        class A:
            def __init__(self) -> None:
                self.x = 100

            def some_method(self) -> None:
                self.x = -1

            def __repr__(self) -> str:
                return "A(x={})".format(self.x)

        # Valid call
        a = A()

        # Invalid call
        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            a.some_method()
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual('some_condition: self was A(x=-1)', tests.error.wo_mandatory_location(str(violation_error)))

    def test_condition_as_function_with_default_argument_value(self) -> None:
        def some_condition(self: 'A', y: int = 0) -> bool:
            return self.x > y

        @icontract.invariant(some_condition)
        class A:
            def __init__(self) -> None:
                self.x = 100

            def some_method(self) -> None:
                self.x = -1

            def __repr__(self) -> str:
                return "A(x={})".format(self.x)

        # Valid call
        a = A()

        # Invalid call
        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            a.some_method()
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual('some_condition: self was A(x=-1)', tests.error.wo_mandatory_location(str(violation_error)))


class TestProperty(unittest.TestCase):
    def test_property_getter(self) -> None:
        @icontract.invariant(lambda self: not self.toggled)
        class SomeClass:
            def __init__(self) -> None:
                self.toggled = False

            @property
            def some_prop(self) -> int:
                self.toggled = True
                return 0

            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        some_inst = SomeClass()

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = some_inst.some_prop
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent("""\
                not self.toggled:
                self was an instance of SomeClass
                self.toggled was True"""), tests.error.wo_mandatory_location(str(violation_error)))

    def test_property_setter(self) -> None:
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

            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        some_inst = SomeClass()

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_inst.some_prop = 0
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent("""\
                not self.toggled:
                self was an instance of SomeClass
                self.toggled was True"""), tests.error.wo_mandatory_location(str(violation_error)))

    def test_property_deleter(self) -> None:
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

            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        some_inst = SomeClass()

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            del some_inst.some_prop
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent("""\
                not self.toggled:
                self was an instance of SomeClass
                self.toggled was True"""), tests.error.wo_mandatory_location(str(violation_error)))


class TestError(unittest.TestCase):
    def test_as_type(self) -> None:
        @icontract.invariant(lambda self: self.x > 0, error=ValueError)
        class A:
            def __init__(self) -> None:
                self.x = 0

            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        value_error = None  # type: Optional[ValueError]
        try:
            _ = A()
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertIsInstance(value_error, ValueError)
        self.assertEqual(
            textwrap.dedent("""\
                self.x > 0:
                self was an instance of A
                self.x was 0"""), tests.error.wo_mandatory_location(str(value_error)))

    def test_as_function(self) -> None:
        @icontract.invariant(
            lambda self: self.x > 0, error=lambda self: ValueError("x must be positive, but got: {}".format(self.x)))
        class A:
            def __init__(self) -> None:
                self.x = 0

            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        value_error = None  # type: Optional[ValueError]
        try:
            _ = A()
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertIsInstance(value_error, ValueError)
        self.assertEqual('x must be positive, but got: 0', str(value_error))

    def test_as_function_with_empty_args(self) -> None:
        @icontract.invariant(lambda self: self.x > 0, error=lambda: ValueError("x must be positive"))
        class A:
            def __init__(self) -> None:
                self.x = 0

            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        value_error = None  # type: Optional[ValueError]
        try:
            _ = A()
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertIsInstance(value_error, ValueError)
        self.assertEqual('x must be positive', str(value_error))


class TestToggling(unittest.TestCase):
    def test_disabled(self) -> None:
        @icontract.invariant(lambda self: self.x > 0, enabled=False)
        class SomeClass:
            def __init__(self) -> None:
                self.x = -1

        inst = SomeClass()
        self.assertEqual(-1, inst.x)


class TestBenchmark(unittest.TestCase):
    @unittest.skip("Skipped the benchmark, execute manually on a prepared benchmark machine.")
    def test_benchmark_when_disabled(self) -> None:
        def some_long_condition() -> bool:
            time.sleep(5)
            return True

        @icontract.invariant(lambda self: some_long_condition(), enabled=False)
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
    def test_with_invalid_arguments(self) -> None:
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

    def test_no_boolyness(self) -> None:
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


if __name__ == '__main__':
    unittest.main()
