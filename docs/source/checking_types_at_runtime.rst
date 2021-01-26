Checking Types at Runtime
=========================
Icontract focuses on logical contracts in the code. Theoretically, you could use icontract to check the types
at runtime and condition the contracts using
`material implication <https://en.wikipedia.org/wiki/Material_implication_(rule_of_inference)>`_:

.. code-block:: python

        @icontract.require(lambda x: not isinstance(x, int) or x > 0)
        @icontract.require(lambda x: not isinstance(x, str) or x.startswith('x-'))
        def some_func(x: Any) -> None
            ...

This is a good solution if your code lacks type annotations or if you do not know the type in advance.

However, if you already annotated the code with the type annotations, re-stating the types in the contracts
breaks the `DRY principle <https://en.wikipedia.org/wiki/Don%27t_repeat_yourself>`_ and makes the code
unnecessarily hard to maintain and read:

.. code-block:: python

        @icontract.require(lambda x: isinstance(x, int))
        def some_func(x: int) -> None
            ...

Elegant runtime type checks are out of icontract's scope. We would recommend you to use one of the available
libraries specialized only on such checks such as `typeguard <https://pypi.org/project/typeguard/>`_.

The icontract's test suite explicitly includes tests to make sure that icontract and typeguard work well together and
to enforce their interplay in the future.
