Recipes
=======
**Learning curve**.
In our experience, it does not take long for programmers to pick up and start applying design-by-contracts.
Although only anecdotal, we observed that it takes junior programmers **one to two weeks** to get up to speed and start writing meaningful contracts in their code.

In general, writing contracts tends to be easy: while some conditions are really hard, most conditions are rather trivial.
However, it takes a bit till it "clicks" so that writing contracts becomes a second nature when writing code.
To help people with learning and training, we compiled a list of common recipes (*i.e.* patterns) that we often observed during the development.

**Benefits of the recipes**.
In our experience, oftentimes it suffices if you just write down the obvious contracts.
This will usually already substantially improve the correctness of your code and catch many bugs.
To that end, recipes help you so that you do not have to spend so much mental energy on contracts, while reaping the benefits of the low-hanging fruits.

**Suggestions**.
The following list of recipes is of course far from comprehensive.
We collected the patterns based on our every-day programming, so they are intrinsically biased towards the areas we work on.
If you developed contract patterns of your own that you do not see listed here, please feel free to suggest extensions!
The easiest way for us to organize suggestions is if you `create a new issue on our GitHub`_.

.. _create a new issue on our GitHub: https://github.com/Parquery/icontract/issues/new

**Corpus**.
We collected an extensive corpus of Python programs annotated with contracts, `Python-by-contract corpus`_,.
The corpus should serve both education purposes and as a testbed for the tools and libraries in the ecosystem.

.. _Python-by-contract corpus: https://github.com/mristin/python-by-contract-corpus

We will use the snippets from the corpus as examples for the individual recipes.
In the following, we will omit to put an explicit identifier of the corpus for brevity.


Serialize / Deserialize Pair
----------------------------
De/serialization data from different formats is a commonplace in many programs.
Whenever you have a pair (a serialization and a de-serialization function), you should make it explicit in the contract how their inputs are connected.

For example, tokenizing a text and then converting the tokens back to text should give you the original input text.

From `ethz_eprog_2019/exercise_11/problem_02.py#L159`_:

.. _ethz_eprog_2019/exercise_11/problem_02.py#L159: https://github.com/mristin/python-by-contract-corpus/blob/dbbd3b527721a9156f5c749095b18b0151cf8e95//correct_programs/ethz_eprog_2019/exercise_11/problem_02.py#L159

.. code-block:: python

    @ensure(
        lambda text, result:
        tokens_to_text(result) == text  # type: ignore
    )
    def tokenize(text: str) -> List[Token]:
        ...

    @ensure(lambda tokens, result: tokens == tokenize(result))
    def tokens_to_text(tokens: Sequence[Token]) -> str:
        ...

This is a particularly nice scenario for auto-testing tools such as `crosshair`_ and `icontract-hypothesis`_.
Since the input is usually completely defined, the auto-testing tools can be readily used and often reveal relevant bugs in practice.

.. _crosshair: https://github.com/pschanely/CrossHair
.. _icontract-hypothesis: https://github.com/mristin/icontract-hypothesis

Encapsulation of Immutable Types
--------------------------------
Certain contracts repeat throughout the code.
If they operate on immutable data types, such as `Sequence`_ or `int`_, you can encapsulate them into a new data type.
Instead of using ``__init__``, you use ``__new__`` for the construction and simply cast the input object to that new type *after* the pre-conditions were checked.

.. _int: https://docs.python.org/3/library/functions.html#int
.. _Sequence: https://docs.python.org/3/library/typing.html#typing.Sequence

Consider ``Lines``, a data structure representing an immutable sequence of strings which do not contain new-line characters.

From `common.py#L18`_:

.. _common.py#L18: https://github.com/mristin/python-by-contract-corpus/blob/dbbd3b527721a9156f5c749095b18b0151cf8e95/correct_programs/common.py#L18

.. code-block:: python

    class Lines(DBC):
    """Represent a sequence of text lines."""

        # fmt: off
        @require(
            lambda lines:
            all('\n' not in line and '\r' not in line for line in lines)
        )
        # fmt: on
        def __new__(cls, lines: Sequence[str]) -> "Lines":
            return cast(Lines, lines)

Another good example is an identifier, a string complying to a certain pattern.

From `ethz_eprog_2019/exercise_11/problem_02.py#L242`_:

.. _ethz_eprog_2019/exercise_11/problem_02.py#L242: https://github.com/mristin/python-by-contract-corpus/blob/dbbd3b527721a9156f5c749095b18b0151cf8e95/correct_programs/ethz_eprog_2019/exercise_11/problem_02.py#L242

.. code-block:: python

    IDENTIFIER_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9]*")


    class Identifier(DBC, str):

        @require(lambda value: IDENTIFIER_RE.fullmatch(value))
        def __new__(cls, value: str) -> "Identifier":
            return cast(Identifier, value)

This pattern is very efficient — the underlying structure is left as-is and reaps all the benefits of efficient implementation — while it gives you additional static and runtime guarantees.

.. note::

    If you use this pattern with `icontract-hypothesis`_, you can not directly inherit from types such as ``Sequence`` as this will cause problems with the underlying `Hypothesis`_ library.
    Please see `Hypothesis issue #2951`_.

    For the time being (2021-07-01), the best approach is to annotate your data structure with all the methods that you actually need.
    See the class ``Lines`` at `common.py#L18`_ for a full example.

.. _Hypothesis: https://hypothesis.readthedocs.io/en/latest/
.. _Hypothesis issue #2951: https://github.com/HypothesisWorks/hypothesis/issues/2951

Unique Elements in a Sequence
-----------------------------
If you want to assert that the elements of a sequence are unique, you can use `Pigeonhole Principle`_.
Namely, if the elements in a collection are unique, the size of the corresponding set is equal to the size of the collection:

.. code-block:: python

    some_collection = list(...)
    is_unique = len(set(some_collection)) == some_collection

.. _Pigeonhole Principle: https://en.wikipedia.org/wiki/Pigeonhole_principle

From `aoc2020/day_22_crab_combat.py#L40`_:

.. _aoc2020/day_22_crab_combat.py#L40: https://github.com/mristin/python-by-contract-corpus/blob/dbbd3b527721a9156f5c749095b18b0151cf8e95/correct_programs/aoc2020/day_22_crab_combat.py#L40

.. code-block:: python

    class Deck(DBC):
        """Represent a deck of cards."""

        @require(
            lambda cards:
            len(set(cards)) == len(cards),
            "Unique cards"
        )
        def __init__(self, cards: Sequence[int]) -> None:
            ...

Contracts on Elements of a Collection
-------------------------------------
We can use built-in functions `all`_ and `any`_ to model the contracts on the elements of a collection.
Coupled with `generator expressions`_, this gives very readable and elegant conditions.

.. _all: https://docs.python.org/3/library/functions.html#all
.. _any: https://docs.python.org/3/library/functions.html#all
.. _generator expressions: https://www.python.org/dev/peps/pep-0289/

From `aoc2020/day_11_seating_system.py#L52`_:

.. _aoc2020/day_11_seating_system.py#L52: https://github.com/mristin/python-by-contract-corpus/blob/dbbd3b527721a9156f5c749095b18b0151cf8e95/correct_programs/aoc2020/day_11_seating_system.py#L52

.. code-block:: python

    import re

    class Layout:
        """Represent a seat layout."""

        @require(
            lambda table:
            len(table) > 0
            and len(table[0]) > 0
            and all(
                len(row) == len(table[0])
                for row in table
            )
        )
        @require(
            lambda table:
            all(
                re.fullmatch(r"[L#.]", cell)
                for row in table
                for cell in row
            )
        )
        def __init__(self, table: List[List[str]]) -> None:
            """Initialize with the given values."""
            ...


Elements of a Sequence Sorted
-----------------------------

If we need to assert that the elements of a sequence are sorted, we can used the built-in function `sorted`_ to succinctly formulate the condition:

.. _sorted: https://docs.python.org/3/library/functions.html#sorted

.. code-block:: python

    some_collection = list(...)
    is_sorted = sorted(some_collection) == some_collection


From `ethz_eprog_2019/exercise_03/problem_04.py#L38`_:

.. _ethz_eprog_2019/exercise_03/problem_04.py#L38: https://github.com/mristin/python-by-contract-corpus/blob/dbbd3b527721a9156f5c749095b18b0151cf8e95/correct_programs/ethz_eprog_2019/exercise_03/problem_04.py#L38

.. code-block:: python

    assert all("".join(sorted(key)) == key for key in TO_NUMBER)

Non-overlapping Sorted Ranges
-----------------------------
Ranges (also called intervals) are usually defined with a start and an end.
In many problems they are given in a sorted sequence where no overlap is expected.
For example, if you have to model tags of a text, where the tags do not overlap.

Before we formulate the condition, let us first introduce a helper function to iterate over two consecutive elements in a sequence.

From `common.py#L88`_:

.. _common.py#L88: https://github.com/mristin/python-by-contract-corpus/blob/dbbd3b527721a9156f5c749095b18b0151cf8e95/correct_programs/common.py#L88

.. code-block:: python

    def pairwise(iterable: Iterable[T]) -> Iterable[Tuple[T, T]]:
        """Iterate over ``(s0, s1, s2, ...)`` as ``((s0, s1), (s1, s2), ...)``."""
        previous = None  # type: Optional[T]
        for current in iterable:
            if previous is not None:
                yield previous, current

            previous = current

Assuming the ranges are sorted and non-overlapping, with inclusive start and exclusive end, the end of the ``previous`` range must equal the start of the ``current`` range.

From `ethz_eprog_2019/exercise_12/problem_01.py#L88`_:

.. _ethz_eprog_2019/exercise_12/problem_01.py#L88: https://github.com/mristin/python-by-contract-corpus/blob/dbbd3b527721a9156f5c749095b18b0151cf8e95/correct_programs/ethz_eprog_2019/exercise_12/problem_01.py#L88

.. code-block:: python

    class Token(DBC):
        @require(lambda start, end: start < end)
        def __init__(self, ..., start: int, end: int, ...) -> None:
            ...

and from `ethz_eprog_2019/exercise_12/problem_01.py#L147`_:

.. _ethz_eprog_2019/exercise_12/problem_01.py#L147: https://github.com/mristin/python-by-contract-corpus/blob/dbbd3b527721a9156f5c749095b18b0151cf8e95/correct_programs/ethz_eprog_2019/exercise_12/problem_01.py#L147

.. code-block:: python

    @ensure(
        lambda result:
        all(
            token1.end == token2.start
            for token1, token2 in common.pairwise(result)
        ),
        "Tokens consecutive"
    )
    def tokenize(text: str) -> List[Token]:
        """Tokenize the given ``text``."""
        ...

If you want to allow "holes" between the ranges, just change the equality to the less comparison:

.. code-block:: python

    token1.end < token2.start

Material Conditional ("If ... then ...")
----------------------------------------
You can toggle contracts at load time of a module using ``enabled`` argument (see :ref:`Toggling Contracts`).
This mechanism can not be used at runtime as we need toggling to be efficient and performed only once.

However, some contracts depend on the runtime values.
For example, a condition on some value might apply only if the value is negative, or if a value is not ``None``.

We can use the `material conditional`_ to formulate "if ... then ..." conditioning in the contracts.
The implication, ``A ⇒ B``, means that the logical statement ``B`` must hold if the logical statement ``A`` holds.

.. _material conditional: https://en.wikipedia.org/wiki/Material_conditional

Unlike `Eiffel Programming Language`_, Python does not provide the implication operator, but we can rewrite the material implication as: ``¬A ∨ B``.
In Python, this is written as: ``not A or B``.

.. _Eiffel Programming Language: https://en.wikipedia.org/wiki/Eiffel_(programming_language)

From `ethz_eprog_2019/exercise_05/problem_03.py#L217`_:

.. code-block:: python

    class Range:
        start: Final[float]
        end: Final[float]

        ...

    @ensure(
        lambda ranges, value, result:
        not (value < ranges[0].start) or result == -1,
        "Value not covered in ranges => bin not found"
    )
    def bin_index(ranges: BinRanges, value: float) -> int:
        """Find the index of the bin range among ``ranges`` corresponding to ``value``."""
        ...

.. _ethz_eprog_2019/exercise_05/problem_03.py#L217: https://github.com/mristin/python-by-contract-corpus/blob/dbbd3b527721a9156f5c749095b18b0151cf8e95/correct_programs/ethz_eprog_2019/exercise_05/problem_03.py#L217

This pattern also nicely plays with `sphinx-icontract`_ which renders the material implication with the proper symbol ``⇒``.
See `the generated documentation of bin_index`_.

.. _sphinx-icontract: https://github.com/Parquery/sphinx-icontract

.. _the generated documentation of bin_index: https://python-by-contract-corpus.readthedocs.io/en/latest/correct_programs/ethz_eprog_2019/exercise_05/problem_03.html#correct_programs.ethz_eprog_2019.exercise_05.problem_03.bin_index

Compare against a Redundant Implementation
------------------------------------------
When you need to get a complex algorithm right, a common approach is to provide multiple redundant implementations.
The hope is that the bugs will not replicate across the implementations.
For example, the same task is given to different teams, or the same problem is tackled with different algorithms.

We observe often in practice that only two implementations are sufficient:

1) An optimized complex one, which has a high probability of bugs, and
2) A naïve inefficient one. This implementation takes substantially longer to run or does not scale with the large input at all.
   However, it is much easier to read and verify, and the probability of bugs is much smaller.

You assert then in code that the output of the optimized implementation matches the naïve one.

From `ethz_eprog_2019/exercise_04/problem_01.py#L39`_, where we compute the `Sieve of Eratosthenes`_:

.. _ethz_eprog_2019/exercise_04/problem_01.py#L39: https://github.com/mristin/python-by-contract-corpus/blob/dbbd3b527721a9156f5c749095b18b0151cf8e95/correct_programs/ethz_eprog_2019/exercise_04/problem_01.py#L39
.. _Sieve of Eratosthenes: https://en.wikipedia.org/wiki/Sieve_of_Eratosthenes

.. code-block:: python

    @ensure(
        lambda result:
        all(
            naive_is_prime(number)
            for number in result
        )
    )
    def sieve(limit: int) -> List[int]:
        """
        Apply the Sieve of Eratosthenes on the numbers up to ``limit``.
        :return: list of prime numbers till ``limit``
        """
        ...

Usually you toggle this contract using ``enabled`` argument at load time so that it is only applied in the testing environments where you know that the input is small enough for the naïve implementation (see :ref:`Toggling Contracts`):

.. code-block:: python

    IN_TESTING_ENVIRONMENT = ...

    @ensure(
        lambda result:
        all(
            naive_is_prime(number)
            for number in result
        ),
        enabled=IN_TESTING_ENVIRONMENT
    )


Alternatively, you can use material conditional to limit the contract on small inputs at runtime (see the recipe :ref:`Material Conditional ("If ... then ...")`):

.. code-block:: python

    IN_TESTING_ENVIRONMENT = ...

    @ensure(
        lambda result:
        not (max(result) < 100 and len(result) <= 10)
        or all(
            naive_is_prime(number)
            for number in result
        )
    )

Exclusive Or ("Either ... or ...")
----------------------------------
Python already provides an exclusive or operator (``^``), so we can directly use it to model exclusive properties in the contracts.
For example, a function returns either a valid result *or* an error message (but not both).
Another example is if a function expects either one or the other argument to be specified (but, again, not both).

From `ethz_eprog_2019/exercise_08/problem_05.py#L59`_:

.. _ethz_eprog_2019/exercise_08/problem_05.py#L59: https://github.com/mristin/python-by-contract-corpus/blob/dbbd3b527721a9156f5c749095b18b0151cf8e95/correct_programs/ethz_eprog_2019/exercise_08/problem_05.py#L59

.. code-block:: python

    @ensure(
        lambda pos, result:
        all(
            (next_pos.x == pos.x and next_pos.y != pos.y)
            ^ (next_pos.x != pos.x and next_pos.y == pos.y)
            for next_pos in result
        ),
        "Next is either in x- or in y-direction"
    )
    def list_next_positions(pos: Position) -> Sequence[Position]:
        """List all the possible next positions based on the current position ``pos``."""
        ...

Intermediate Variables
----------------------
Long and complex contracts can become unwieldy, especially if certain expressions are re-used throughout the condition.
Python's `Assignment Expressions`_ (a.k.a. walrus operator, ``:=``) is particularly useful in such situations as it allows you to introduce a bit of "procedural" programming into the generally declarative conditions.

.. _Assignment Expressions: https://www.python.org/dev/peps/pep-0572/

From `ethz_eprog_2019/exercise_02/problem_03.py#L53`_:

.. _ethz_eprog_2019/exercise_02/problem_03.py#L53: https://github.com/mristin/python-by-contract-corpus/blob/dbbd3b527721a9156f5c749095b18b0151cf8e95/correct_programs/ethz_eprog_2019/exercise_02/problem_03.py#L53

.. code-block:: python

    @ensure(
        lambda result:
        all(
            (
                    center := len(line) // 2,
                    line[:center] == line[center + 1:][::-1]
                    if len(line) % 2 == 1
                    else line[:center] == line[center:][::-1]
            )[1]
            for line in result
        ),
        "Horizontal symmetry"
    )
    def draw(width: int, height: int) -> Lines:
        """Draw the pattern of the size ``width`` x ``height`` and return the text lines."""
        ...

.. note::

    The walrus operator assigns the computed value to a variable *and* evaluates the value back.
    Hence we use a tuple to make the code "procedural" and re-use the assigned variable in the second element of the tuple.

.. note::

    The introduction of the walrus operator (`PEP 572`_) did spark some controversy and even lead to resigning of Guido van Rossum as Benevolent Dictator For Life (see `this article about PEP 572 on lwn.net`_).
    With that said, you have to be careful not to abuse the feature.

    For example, if the condition becomes *too* complex, it may be worth considering refactoring the code into a separate function (and testing it independently as well).
    Putting contract condition in a separate function has a disadvantage, though, that you do not get as informative violation messages (see Section :ref:`Usage`) and they hinder the tools like `icontract-hypothesis`_.

.. _PEP 572: https://www.python.org/dev/peps/pep-0572/
.. _this article about PEP 572 on lwn.net: https://lwn.net/Articles/759558/
