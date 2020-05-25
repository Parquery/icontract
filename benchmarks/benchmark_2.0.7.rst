Benchmarks
==========
We evaluated the computational costs incurred by using icontract in a couple of experiments. There are basically two
types of costs caused by icontract: 1) extra parsing performed when you import the module regardless whether conditions
are switched on or off and 2) run-time cost of verifying the contract.

We assumed in all the experiments that the contract breaches are exceptionally seldom and thus need not to be analyzed.
If you are interested in these additional experiments, please do let us know and create an issue on the github page.

The source code of the benchmarks is available in
`this directory <https://github.com/Parquery/icontract/tree/master/benchmarks>`_.
All experiments were performed with Python 3.5.2+ on Intel(R) Core(TM) i7-4700MQ CPU @ 2.40GHz with 8 cores and
4 GB RAM.

We execute a short timeit snippet to bring the following measurements into context:

.. code-block:: bash

    python3 -m timeit -s 'import math' 'math.sqrt(1984.1234)'
    10000000 loops, best of 3: 0.0679 usec per loop

Important Note
--------------
The experiments were executed with icontract 2.0.7. While it would have been great to have benchmarks
re-executed on each new version, that would require substantial effort on our side.
Please run the scripts manually on your machine with the latest icontract version
to obtain the current benchmark results.

Import Cost
-----------
**Pre and post-conditions.**
We generated a module with 100 functions. For each of these functions, we introduced a variable number of conditions and
stop-watched how long it takes to import the module over 10 runs. Finally, we compared the import time of the module
with contracts against the same module without any contracts in the code.

The overhead is computed as the time difference between the total import time compared to the total import time of the
module without the contracts.

+-----------------------------------+----------------------------------+-------------------------+----------------------------------------------------+
| Number of conditions per function | Total import time [milliseconds] | Overhead [milliseconds] | Overhead per condition and function [milliseconds] |
+===================================+==================================+=========================+====================================================+
| None                              |                   795.59 ± 10.47 |                     N/A |                                                N/A |
+-----------------------------------+----------------------------------+-------------------------+----------------------------------------------------+
| 1                                 |                   919.53 ± 61.22 |                  123.93 |                                               1.24 |
+-----------------------------------+----------------------------------+-------------------------+----------------------------------------------------+
| 5                                 |                  1075.81 ± 59.87 |                  280.22 |                                               0.56 |
+-----------------------------------+----------------------------------+-------------------------+----------------------------------------------------+
| 10                                |                  1290.22 ± 90.04 |                  494.63 |                                               0.49 |
+-----------------------------------+----------------------------------+-------------------------+----------------------------------------------------+
| 1 disabled                        |                   833.60 ± 32.07 |                   37.41 |                                               0.37 |
+-----------------------------------+----------------------------------+-------------------------+----------------------------------------------------+
| 5 disabled                        |                   851.31 ± 66.93 |                   55.72 |                                               0.11 |
+-----------------------------------+----------------------------------+-------------------------+----------------------------------------------------+
| 10 disabled                       |                  897.90 ± 143.02 |                  101.41 |                                               0.10 |
+-----------------------------------+----------------------------------+-------------------------+----------------------------------------------------+

As we can see in the table above, the overhead per condition is quite minimal (1.24 milliseconds in case of a single
enabled contract). The overhead decreases as you add more conditions since the icontract has already initialized all the
necessary fields in the function objects.

When you disable the conditions, there is much less overhead (only 0.37 milliseconds, and decreasing). Since icontract
returns immediately when the condition is disabled by implementation, we assume that the overhead coming from disabled
conditions is mainly caused by Python interpreter parsing the code.


**Invariants**. Analogously, to measure the overhead of the invariants, we generated a module with 100 classes.
We varied the number of invariant conditions per class and measure the import time over 10 runs. The results
are presented in the following table.

+--------------------------------+----------------------------------+-------------------------+-------------------------------------------------+
| Number of conditions per class | Total import time [milliseconds] | Overhead [milliseconds] | Overhead per condition and class [milliseconds] |
+================================+==================================+=========================+=================================================+
| None                           |                   843.61 ± 28.21 |                     N/A |                                             N/A |
+--------------------------------+----------------------------------+-------------------------+-------------------------------------------------+
| 1                              |                  3409.71 ± 95.78 |                  2566.1 |                                           25.66 |
+--------------------------------+----------------------------------+-------------------------+-------------------------------------------------+
| 5                              |                 4005.93 ± 131.97 |                 3162.32 |                                            6.32 |
+--------------------------------+----------------------------------+-------------------------+-------------------------------------------------+
| 10                             |                 4801.82 ± 157.56 |                 3958.21 |                                            3.96 |
+--------------------------------+----------------------------------+-------------------------+-------------------------------------------------+
| 1 disabled                     |                   885.88 ± 44.24 |                   42.27 |                                            0.42 |
+--------------------------------+----------------------------------+-------------------------+-------------------------------------------------+
| 5 disabled                     |                  912.53 ± 101.91 |                   68.92 |                                            0.14 |
+--------------------------------+----------------------------------+-------------------------+-------------------------------------------------+
| 10 disabled                    |                  963.77 ± 161.76 |                  120.16 |                                            0.12 |
+--------------------------------+----------------------------------+-------------------------+-------------------------------------------------+

Similar to pre and post-conditions, there is decreasing cost per condition as number of conditions increases since the
icontract has all set up the fields in the class metadata. However, invariants are much more costly compared to pre and
postconditions and their overhead should be considered if import time needs to be kept minimal.

The overhead of the disabled invariants is attributed to the overhead of parsing the source file as icontract
immediately returns from disabled invariants by implementation.

Run-time Cost
-------------
We constructed four modules around a function which computes a square root. We used ``timeit`` module to measure the
performance. Each module was imported as part of the setup.

**No precondition**. This module does not check any preconditions and serves as a baseline.

.. code-block: python

    import math
    def my_sqrt(x: float) -> float:
        return math.sqrt(x)

**Pre-condition as assert**. We check pre-conditions by an assert statement.

.. code-block:: python

    def my_sqrt(x: float) -> float:
        assert x >= 0
        return math.sqrt(x)

**Pre-condition as separate function**. To mimick a more complex pre-condition, we encapsulate the assert in a separate
function.

.. code-block:: python

    import math

    def check_non_negative(x: float) -> None:
        assert x >= 0

    def my_sqrt(x: float) -> float:
        check_non_negative(x)
        return math.sqrt(x)

**Pre-condition with icontract**. Finally, we compare against a module that uses icontract.

.. code-block:: python

    import math
    import icontract

    @icontract.require(lambda x: x >= 0)
    def my_sqrt(x: float) -> float:
        return math.sqrt(x)

**Pre-condition with icontract, disabled**. We also perform a redundant check to verify that a disabled condition
does not incur any run-time cost.

The following table sumarizes the timeit results (10000000 loops, best of 3). The run time of the baseline is computed
as:

.. code-block: bash

    $ python3 -m timeit -s 'import my_sqrt' 'my_sqrt.my_sqrt(1984.1234)'

The run time of the other functions is computed analogously.

+---------------------+-------------------------+
| Precondition        | Run time [microseconds] |
+=====================+=========================+
| None                |                   0.168 |
+---------------------+-------------------------+
| As assert           |                   0.203 |
+---------------------+-------------------------+
| As function         |                   0.274 |
+---------------------+-------------------------+
| icontract           |                    2.78 |
+---------------------+-------------------------+
| icontract, disabled |                   0.165 |
+---------------------+-------------------------+

The overhead of icontract is substantial. While this may be prohibitive for points where computational efficiency is
more important than correctness, mind that the overhead is still in order of microseconds. In most practical scenarios,
where a function is more complex and takes longer than a few microseconds to execute, such a tiny overhead is
justified by the gains in correctness, development and maintenance time.
