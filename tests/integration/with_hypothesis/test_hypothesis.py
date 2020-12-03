# pylint: disable=missing-docstring
# pylint: disable=invalid-name
# pylint: disable=unused-argument
# pylint: disable=no-value-for-parameter
import abc
import dataclasses
import datetime
import decimal
import enum
import fractions
import math
import re
import unittest
from typing import List, Optional, Any, TypedDict, NamedTuple, Union

import hypothesis.strategies
import hypothesis.errors

import icontract.integration.with_hypothesis


class TestAssumePreconditions(unittest.TestCase):
    def test_assumed_preconditions_pass(self) -> None:
        @icontract.require(lambda x: x > 0)
        def some_func(x: int) -> None:
            pass

        assume_preconditions = icontract.integration.with_hypothesis.make_assume_preconditions(some_func)

        assume_preconditions(x=100)

    def test_assumed_preconditions_fail(self) -> None:
        @icontract.require(lambda x: x > 0)
        def some_func(x: int) -> None:
            pass

        assume_preconditions = icontract.integration.with_hypothesis.make_assume_preconditions(some_func)

        unsatisfied_assumption = None  # type: Optional[hypothesis.errors.UnsatisfiedAssumption]
        try:
            assume_preconditions(x=-100)
        except hypothesis.errors.UnsatisfiedAssumption as err:
            unsatisfied_assumption = err

        self.assertIsNotNone(unsatisfied_assumption)

    def test_without_preconditions(self) -> None:
        recorded_inputs = []  # type: List[Any]

        def some_func(x: int) -> None:
            recorded_inputs.append(x)

        assume_preconditions = icontract.integration.with_hypothesis.make_assume_preconditions(some_func)

        @hypothesis.given(x=hypothesis.strategies.integers())
        def execute(x: int) -> None:
            assume_preconditions(x)
            some_func(x)

        execute()

        # 10 is an arbitrary, but plausible value.
        self.assertGreater(len(recorded_inputs), 10)

    def test_with_a_single_precondition(self) -> None:
        recorded_inputs = []  # type: List[int]

        @icontract.require(lambda x: x > 0)
        def some_func(x: int) -> None:
            recorded_inputs.append(x)

        assume_preconditions = icontract.integration.with_hypothesis.make_assume_preconditions(some_func)

        samples = [-1, 1]

        @hypothesis.given(x=hypothesis.strategies.sampled_from(samples))
        def execute(x: int) -> None:
            samples.append(x)
            assume_preconditions(x)
            some_func(x)

        execute()

        self.assertSetEqual({1}, set(recorded_inputs))

    def test_with_two_preconditions(self) -> None:
        recorded_inputs = []  # type: List[int]

        @icontract.require(lambda x: x > 0)
        @icontract.require(lambda x: x % 3 == 0)
        def some_func(x: int) -> None:
            recorded_inputs.append(x)

        assume_preconditions = icontract.integration.with_hypothesis.make_assume_preconditions(some_func)

        samples = [-1, 1, 3]

        @hypothesis.given(x=hypothesis.strategies.sampled_from(samples))
        def execute(x: int) -> None:
            samples.append(x)
            assume_preconditions(x)
            some_func(x)

        execute()

        self.assertSetEqual({3}, set(recorded_inputs))


class TestAssumeWeakenedPreconditions(unittest.TestCase):
    def test_with_a_single_precondition(self) -> None:
        class A(icontract.DBC):
            @icontract.require(lambda x: x % 3 == 0)
            def some_func(self, x: int) -> None:
                pass

        recorded_inputs = []  # type: List[int]

        class B(A):
            @icontract.require(lambda x: x % 7 == 0)
            def some_func(self, x: int) -> None:
                # The inputs from B.some_func need to satisfy either their own preconditions or
                # the preconditions of A.some_func ("require else").
                recorded_inputs.append(x)

        b = B()
        assume_preconditions = icontract.integration.with_hypothesis.make_assume_preconditions(b.some_func)

        @hypothesis.given(x=hypothesis.strategies.sampled_from([-14, -3, 5, 7, 9]))
        def execute(x: int) -> None:
            assume_preconditions(x)
            b.some_func(x)

        execute()

        self.assertSetEqual({-14, -3, 7, 9}, set(recorded_inputs))

    def test_with_two_preconditions(self) -> None:
        class A(icontract.DBC):
            @icontract.require(lambda x: x % 3 == 0)
            def some_func(self, x: int) -> None:
                pass

        recorded_inputs = []  # type: List[int]

        class B(A):
            @icontract.require(lambda x: x > 0)
            @icontract.require(lambda x: x % 7 == 0)
            def some_func(self, x: int) -> None:
                # The inputs from B.some_func need to satisfy either their own preconditions or
                # the preconditions of A.some_func ("require else").
                recorded_inputs.append(x)

        b = B()
        assume_preconditions = icontract.integration.with_hypothesis.make_assume_preconditions(b.some_func)

        @hypothesis.given(x=hypothesis.strategies.sampled_from([-14, 3, 7, 9, 10, 14]))
        def execute(x: int) -> None:
            assume_preconditions(x)
            b.some_func(x)

        execute()

        self.assertSetEqual({3, 7, 9, 14}, set(recorded_inputs))


class TestWithInferredStrategies(unittest.TestCase):
    def test_fail_without_type_hints(self) -> None:
        @icontract.require(lambda x: x > 0)
        def some_func(x) -> None:  # type: ignore
            pass

        type_error = None  # type: Optional[TypeError]
        try:
            icontract.integration.with_hypothesis.test_with_inferred_strategies(some_func)
        except TypeError as err:
            type_error = err

        assert type_error is not None
        self.assertTrue(str(type_error).startswith('No strategies could be inferred for the function: '))

    def test_without_preconditions(self) -> None:
        def some_func(x: int) -> None:
            pass

        strategies = icontract.integration.with_hypothesis.infer_strategies(some_func)
        self.assertEqual("{'x': integers()}", str(strategies))

        icontract.integration.with_hypothesis.test_with_inferred_strategies(some_func)

    def test_unmatched_pattern(self) -> None:
        @icontract.require(lambda x: x > 0 and x > math.sqrt(x))
        def some_func(x: float) -> None:
            pass

        strategies = icontract.integration.with_hypothesis.infer_strategies(some_func)
        self.assertEqual("{'x': floats().filter(lambda x: x > 0 and x > math.sqrt(x))}", str(strategies))

        icontract.integration.with_hypothesis.test_with_inferred_strategies(some_func)

    def test_with_multiple_preconditions(self) -> None:
        recorded_inputs = []  # type: List[Any]

        hundred = 100

        @icontract.require(lambda x: x > 0)
        @icontract.require(lambda x: x >= 1)
        @icontract.require(lambda x: x < 100)
        @icontract.require(lambda x: x <= 90)
        @icontract.require(lambda y: 0 < y <= 100)
        @icontract.require(lambda y: 1 <= y < 90)
        @icontract.require(lambda z: 0 > z >= -math.sqrt(hundred))
        def some_func(x: int, y: int, z: int) -> None:
            pass

        strategies = icontract.integration.with_hypothesis.infer_strategies(some_func)
        self.assertEqual("{'x': integers(min_value=2, max_value=89), 'y': integers(min_value=2, max_value=89), "
                         "'z': integers(min_value=-9.0, max_value=-1)}", str(strategies))

        icontract.integration.with_hypothesis.test_with_inferred_strategies(some_func)

    def test_with_dates(self) -> None:
        SOME_DATE = datetime.date(2014, 3, 2)

        # The preconditions were picked s.t. to also test that we can recompute everything.
        @icontract.require(lambda a: a < SOME_DATE + datetime.timedelta(days=3))
        @icontract.require(lambda b: b < SOME_DATE + datetime.timedelta(days=2))
        @icontract.require(lambda c: c < max(SOME_DATE, datetime.date(2020, 1, 1)))
        @icontract.require(
            lambda d: d < (SOME_DATE if SOME_DATE > datetime.date(2020, 1, 1) else datetime.date(2020, 12, 5)))
        def some_func(a: datetime.date, b: datetime.date, c: datetime.date, d: datetime.date) -> None:
            pass

        strategies = icontract.integration.with_hypothesis.infer_strategies(some_func)
        self.assertEqual("{'a': dates(max_value=datetime.date(2014, 3, 5)), "
                         "'b': dates(max_value=datetime.date(2014, 3, 4)), "
                         "'c': dates(max_value=datetime.date(2020, 1, 1)), "
                         "'d': dates(max_value=datetime.date(2020, 12, 5))}", str(strategies))

        icontract.integration.with_hypothesis.test_with_inferred_strategies(some_func)

    def test_with_datetimes(self) -> None:
        SOME_DATETIME = datetime.datetime(2014, 3, 2, 10, 20, 30)

        @icontract.require(lambda a: a < SOME_DATETIME)
        def some_func(a: datetime.datetime) -> None:
            pass

        strategies = icontract.integration.with_hypothesis.infer_strategies(some_func)
        self.assertEqual("{'a': datetimes(max_value=datetime.datetime(2014, 3, 2, 10, 20, 30))}", str(strategies))

        icontract.integration.with_hypothesis.test_with_inferred_strategies(some_func)

    def test_with_times(self) -> None:
        SOME_TIME = datetime.time(1, 2, 3)

        @icontract.require(lambda a: a < SOME_TIME)
        def some_func(a: datetime.time) -> None:
            pass

        strategies = icontract.integration.with_hypothesis.infer_strategies(some_func)
        self.assertEqual("{'a': times(max_value=datetime.time(1, 2, 3))}", str(strategies))

        icontract.integration.with_hypothesis.test_with_inferred_strategies(some_func)

    def test_with_timedeltas(self) -> None:
        SOME_TIMEDELTA = datetime.timedelta(days=3)

        @icontract.require(lambda a: a < SOME_TIMEDELTA)
        def some_func(a: datetime.timedelta) -> None:
            pass

        strategies = icontract.integration.with_hypothesis.infer_strategies(some_func)
        self.assertEqual("{'a': timedeltas(max_value=datetime.timedelta(days=3))}", str(strategies))

        icontract.integration.with_hypothesis.test_with_inferred_strategies(some_func)

    def test_with_fractions(self) -> None:
        SOME_FRACTION = fractions.Fraction(3, 2)

        @icontract.require(lambda a: a < SOME_FRACTION)
        def some_func(a: fractions.Fraction) -> None:
            pass

        strategies = icontract.integration.with_hypothesis.infer_strategies(some_func)
        self.assertEqual("{'a': fractions(max_value=Fraction(3, 2))}", str(strategies))

        icontract.integration.with_hypothesis.test_with_inferred_strategies(some_func)

    def test_with_decimals(self) -> None:
        SOME_DECIMAL = decimal.Decimal(10)

        @icontract.require(lambda a: not decimal.Decimal.is_nan(a))
        @icontract.require(lambda a: a < SOME_DECIMAL)
        def some_func(a: decimal.Decimal) -> None:
            pass

        strategies = icontract.integration.with_hypothesis.infer_strategies(some_func)
        self.assertEqual("{'a': decimals(max_value=Decimal('10')).filter(lambda a: not decimal.Decimal.is_nan(a))}",
                         str(strategies))

        icontract.integration.with_hypothesis.test_with_inferred_strategies(some_func)

    def test_with_weakened_preconditions(self) -> None:
        class A(icontract.DBC):
            @icontract.require(lambda x: 0 < x < 20)
            @icontract.require(lambda x: x % 3 == 0)
            def some_func(self, x: int) -> None:
                pass

        class B(A):
            @icontract.require(lambda x: 0 < x < 20)
            @icontract.require(lambda x: x % 7 == 0)
            def some_func(self, x: int) -> None:
                # The inputs from B.some_func need to satisfy either their own preconditions or
                # the preconditions of A.some_func ("require else").
                pass

        b = B()

        strategies = icontract.integration.with_hypothesis.infer_strategies(b.some_func)
        self.assertEqual("{'x': one_of("
                         "integers(min_value=1, max_value=19).filter(lambda x: x % 3 == 0), "
                         "integers(min_value=1, max_value=19).filter(lambda x: x % 7 == 0))}", str(strategies))

        icontract.integration.with_hypothesis.test_with_inferred_strategies(b.some_func)


class TestWithInferredStrategiesOnClasses(unittest.TestCase):
    def test_no_preconditions_and_no_argument_init(self) -> None:
        class A:
            def __repr__(self) -> str:
                return "A()"

        def some_func(a: A) -> None:
            pass

        strategies = icontract.integration.with_hypothesis.infer_strategies(some_func)
        self.assertEqual("{'a': builds(A)}", str(strategies))

        icontract.integration.with_hypothesis.test_with_inferred_strategies(some_func)

    def test_no_preconditions_and_init(self) -> None:
        class A:
            def __init__(self, x: int):
                self.x = x

            def __repr__(self) -> str:
                return "A(x={})".format(self.x)

        def some_func(a: A) -> None:
            pass

        strategies = icontract.integration.with_hypothesis.infer_strategies(some_func)
        self.assertEqual("{'a': builds(A)}", str(strategies))

        icontract.integration.with_hypothesis.test_with_inferred_strategies(some_func)

    def test_preconditions_with_heuristics(self) -> None:
        class A(icontract.DBC):
            @icontract.require(lambda x: x > 0)
            def __init__(self, x: int):
                self.x = x

            def __repr__(self) -> str:
                return "A(x={})".format(self.x)

        def some_func(a: A) -> None:
            pass

        strategies = icontract.integration.with_hypothesis.infer_strategies(some_func)
        self.assertEqual("{'a': builds(A, x=integers(min_value=1))}", str(strategies))

        icontract.integration.with_hypothesis.test_with_inferred_strategies(some_func)

    def test_preconditions_without_heuristics(self) -> None:
        class A(icontract.DBC):
            @icontract.require(lambda x: x > 0)
            @icontract.require(lambda x: x > math.sqrt(x))
            def __init__(self, x: float):
                self.x = x

            def __repr__(self) -> str:
                return "A(x={})".format(self.x)

        def some_func(a: A) -> None:
            pass

        strategies = icontract.integration.with_hypothesis.infer_strategies(some_func)
        self.assertEqual("{'a': builds(A, x=floats(min_value=0, exclude_min=True).filter(lambda x: x > math.sqrt(x)))}",
                         str(strategies))

        icontract.integration.with_hypothesis.test_with_inferred_strategies(some_func)

    def test_composition(self) -> None:
        class A(icontract.DBC):
            @icontract.require(lambda x: x > 0)
            def __init__(self, x: int):
                self.x = x

            def __repr__(self) -> str:
                return "A(x={})".format(self.x)

        class B(icontract.DBC):
            @icontract.require(lambda y: y > 2020)
            def __init__(self, a: A, y: int):
                self.a = a
                self.y = y

            def __repr__(self) -> str:
                return "B(a={!r}, y={})".format(self.a, self.y)

        def some_func(b: B) -> None:
            pass

        strategies = icontract.integration.with_hypothesis.infer_strategies(some_func)
        self.assertEqual("{'b': builds(B, a=builds(A, x=integers(min_value=1)), y=integers(min_value=2021))}",
                         str(strategies))

        icontract.integration.with_hypothesis.test_with_inferred_strategies(some_func)

    def test_abstract_class(self) -> None:
        class A(icontract.DBC):
            @abc.abstractmethod
            def do_something(self) -> None:
                pass

        class B(A):
            @icontract.require(lambda x: x > 0)
            def __init__(self, x: int):
                self.x = x

            def __repr__(self) -> str:
                return "B(x={})".format(self.x)

            def do_something(self) -> None:
                pass

        def some_func(a: A) -> None:
            pass

        strategies = icontract.integration.with_hypothesis.infer_strategies(some_func)

        # The strategies inferred for B do not reflect the preconditions of A.
        # This is by design as A is automatically registered with Hypothesis, so Hypothesis
        # will instantiate a B only at run time.
        self.assertEqual("{'a': just("
                         "<class 'test_hypothesis.TestWithInferredStrategiesOnClasses.test_abstract_class.<locals>.B'>)"
                         ".flatmap(from_type)}", str(strategies))

        icontract.integration.with_hypothesis.test_with_inferred_strategies(some_func)

    def test_enum(self) -> None:
        class A(enum.Enum):
            SOMETHING = 1
            ELSE = 2

        def some_func(a: A) -> None:
            pass

        strategies = icontract.integration.with_hypothesis.infer_strategies(some_func)
        self.assertEqual("{'a': sampled_from(test_hypothesis.A)}", str(strategies))

        icontract.integration.with_hypothesis.test_with_inferred_strategies(some_func)

    def test_composition_in_data_class(self) -> None:
        class A(icontract.DBC):
            @icontract.require(lambda x: x > 0)
            def __init__(self, x: int):
                self.x = x

            def __repr__(self) -> str:
                return "A(x={})".format(self.x)


        @dataclasses.dataclass
        class B:
            a: A

        def some_func(b: B) -> None:
            pass

        strategies = icontract.integration.with_hypothesis.infer_strategies(some_func)

        # The strategies inferred for data classes do not reflect the preconditions of A.
        # This is by design as A is automatically registered with Hypothesis, so Hypothesis
        # will instantiate an A only at run time when creating B.
        self.assertEqual("{'b': builds(B)}", str(strategies))

        icontract.integration.with_hypothesis.test_with_inferred_strategies(some_func)

    def test_typed_dict(self) -> None:
        class A(icontract.DBC):
            @icontract.require(lambda x: x > 0)
            def __init__(self, x: int):
                self.x = x

            def __repr__(self) -> str:
                return "A(x={})".format(self.x)

        class B(TypedDict):
            a: A

        def some_func(b: B) -> None:
            pass

        strategies = icontract.integration.with_hypothesis.infer_strategies(some_func)
        self.assertEqual("{'b': fixed_dictionaries({'a': builds(A, x=integers(min_value=1))}, optional={})}",
                         str(strategies))

        icontract.integration.with_hypothesis.test_with_inferred_strategies(some_func)

    def test_list(self) -> None:
        class A(icontract.DBC):
            @icontract.require(lambda x: x > 0)
            def __init__(self, x: int):
                self.x = x

            def __repr__(self) -> str:
                return "A(x={})".format(self.x)

        def some_func(aa: List[A]) -> None:
            pass

        strategies = icontract.integration.with_hypothesis.infer_strategies(some_func)
        self.assertEqual("{'aa': lists(builds(A, x=integers(min_value=1)))}", str(strategies))

        icontract.integration.with_hypothesis.test_with_inferred_strategies(some_func)

    def test_named_tuples(self) -> None:
        class A(icontract.DBC):
            @icontract.require(lambda x: x > 0)
            def __init__(self, x: int):
                self.x = x

            def __repr__(self) -> str:
                return "A(x={})".format(self.x)

        class B(NamedTuple):
            a: A

        def some_func(b: B) -> None:
            pass

        strategies = icontract.integration.with_hypothesis.infer_strategies(some_func)

        # The strategies inferred for named tuples do not reflect the preconditions of A.
        # This is by design as A is automatically registered with Hypothesis, so Hypothesis
        # will instantiate an A only at run time when creating B.
        self.assertEqual("{'b': builds(B)}", str(strategies))

        icontract.integration.with_hypothesis.test_with_inferred_strategies(some_func)

    def test_union(self) -> None:
        class A(icontract.DBC):
            @icontract.require(lambda x: x > 0)
            def __init__(self, x: int):
                self.x = x

            def __repr__(self) -> str:
                return "A(x={})".format(self.x)

        class B(icontract.DBC):
            @icontract.require(lambda x: x < 0)
            def __init__(self, x: int):
                self.x = x

            def __repr__(self) -> str:
                return "B(x={})".format(self.x)

        def some_func(a_or_b: Union[A, B]) -> None:
            pass

        strategies = icontract.integration.with_hypothesis.infer_strategies(some_func)
        self.assertEqual("{'a_or_b': one_of(builds(A, x=integers(min_value=1)), builds(B, x=integers(max_value=-1)))}",
                         str(strategies))

        icontract.integration.with_hypothesis.test_with_inferred_strategies(some_func)


class TestMatchingRegex(unittest.TestCase):
    def test_re_match(self) -> None:
        @icontract.require(lambda s: re.match(r'^Start.*End$', s, flags=0))
        def some_func(s: str) -> None:
            pass

        strategies = icontract.integration.with_hypothesis.infer_strategies(some_func)
        self.assertEqual("{'s': from_regex(re.compile(r'^Start.*End$', re.UNICODE))}", str(strategies))

    def test_re_renamed_match(self) -> None:
        import re as rerenamed

        @icontract.require(lambda s: rerenamed.match(r'^Start.*End$', s, flags=0))
        def some_func(s: str) -> None:
            pass

        strategies = icontract.integration.with_hypothesis.infer_strategies(some_func)
        self.assertEqual("{'s': from_regex(re.compile(r'^Start.*End$', re.UNICODE))}", str(strategies))

    def test_multiple_re_match(self) -> None:
        @icontract.require(lambda s: re.match(r'^Start.*End$', s, flags=0))
        @icontract.require(lambda s: re.match(r'^.*something.*$', s, flags=0))
        def some_func(s: str) -> None:
            pass

        strategies = icontract.integration.with_hypothesis.infer_strategies(some_func)
        self.assertEqual(("{'s': from_regex(re.compile(r'^.*something.*$', re.UNICODE))"
                          ".filter(lambda s: re.match(r'^Start.*End$', s, flags=0))}"), str(strategies))

    def test_compiled_re(self) -> None:
        START_END_RE = re.compile(r'^Start.*End$')

        @icontract.require(lambda s: START_END_RE.match(s))
        def some_func(s: str) -> None:
            pass

        strategies = icontract.integration.with_hypothesis.infer_strategies(some_func)
        self.assertEqual("{'s': from_regex(re.compile(r'^Start.*End$', re.UNICODE))}", str(strategies))

    def test_compiled_re_with_logic(self) -> None:
        START_END_RE = re.compile(r'^Start.*End$')
        PREFIX_SUFFIX_RE = re.compile(r'^Prefix.*Suffix')

        SWITCH = False

        # This pre-condition also tests a bit more complicated logic so that we are sure that
        # the recomputation is executed successfully.
        @icontract.require(lambda s: (START_END_RE if SWITCH else PREFIX_SUFFIX_RE).match(s))
        def some_func(s: str) -> None:
            pass

        strategies = icontract.integration.with_hypothesis.infer_strategies(some_func)
        self.assertEqual("{'s': from_regex(re.compile(r'^Prefix.*Suffix', re.UNICODE))}", str(strategies))


if __name__ == '__main__':
    unittest.main()
