Benchmarks
==========
We run benchmarks against `deal` and `dpcontracts` libraries as part of our continuous integration.

The bodies of the constructors and functions were intentionally left simple so that you can
better estimate **overhead** of the contracts in absolute terms rather than relative.
This means that the code without contracts will run extremely fast (nanoseconds) in the benchmarks
which might make the contracts seem sluggish. However, the methods in the real world usually run
in the order of microseconds and milliseconds, not nanoseconds. As long as the overhead
of the contract is in the order of microseconds, it is often practically acceptable.

.. Becnhmark report from benchmark.py starts.


The following scripts were run:

* `benchmarks/against_others/compare_invariant.py <https://github.com/Parquery/icontract/tree/master/benchmarks/against_others/compare_invariant.py>`_
* `benchmarks/against_others/compare_precondition.py <https://github.com/Parquery/icontract/tree/master/benchmarks/against_others/compare_precondition.py>`_
* `benchmarks/against_others/compare_postcondition.py <https://github.com/Parquery/icontract/tree/master/benchmarks/against_others/compare_postcondition.py>`_

The benchmarks were executed on Intel(R) Xeon(R) E-2276M  CPU @ 2.80GHz.
We used Python 3.9.9, icontract 2.6.1, deal 4.23.3 and dpcontracts 0.6.0.

The following tables summarize the results.

Benchmarking invariant at __init__:

=========================  ============  ==============  =======================
Case                         Total time    Time per run    Relative time per run
=========================  ============  ==============  =======================
`ClassWithIcontract`             1.45 s         1.45 μs                     100%
`ClassWithDpcontracts`           0.48 s         0.48 μs                      33%
`ClassWithDeal`                  1.73 s         1.73 μs                     119%
`ClassWithInlineContract`        0.28 s         0.28 μs                      19%
=========================  ============  ==============  =======================

Benchmarking invariant at a function:

=========================  ============  ==============  =======================
Case                         Total time    Time per run    Relative time per run
=========================  ============  ==============  =======================
`ClassWithIcontract`             2.04 s         2.04 μs                     100%
`ClassWithDpcontracts`           0.49 s         0.49 μs                      24%
`ClassWithDeal`                  4.67 s         4.67 μs                     230%
`ClassWithInlineContract`        0.23 s         0.23 μs                      11%
=========================  ============  ==============  =======================

Benchmarking precondition:

===============================  ============  ==============  =======================
Case                               Total time    Time per run    Relative time per run
===============================  ============  ==============  =======================
`function_with_icontract`              0.04 s         3.91 μs                     100%
`function_with_dpcontracts`            0.54 s        53.92 μs                    1377%
`function_with_deal`                   0.04 s         4.16 μs                     106%
`function_with_inline_contract`        0.00 s         0.15 μs                       4%
===============================  ============  ==============  =======================

Benchmarking postcondition:

===============================  ============  ==============  =======================
Case                               Total time    Time per run    Relative time per run
===============================  ============  ==============  =======================
`function_with_icontract`              0.04 s         4.39 μs                     100%
`function_with_dpcontracts`            0.53 s        52.51 μs                    1197%
`function_with_deal_post`              0.01 s         1.16 μs                      26%
`function_with_deal_ensure`            0.01 s         1.04 μs                      24%
`function_with_inline_contract`        0.00 s         0.15 μs                       3%
===============================  ============  ==============  =======================



.. Benchmark report from benchmark.py ends.

Note that neither the `dpcontracts` nor the `deal` library support recursion and inheritance of the contracts.
This allows them to use faster enforcement mechanisms and thus gain a speed-up.

We also ran a much more extensive battery of benchmarks on icontract 2.0.7. Unfortunately,
it would cost us too much effort to integrate the results in the continuous integration.
The report is available at:
`benchmarks/benchmark_2.0.7.rst <https://github.com/Parquery/icontract/tree/master/benchmarks/benchmark_2.0.7.rst>`_.

The scripts are available at:
`benchmarks/import_cost/ <https://github.com/Parquery/icontract/tree/master/benchmarks/import_cost>`_
and
`benchmarks/runtime_cost/ <https://github.com/Parquery/icontract/tree/master/benchmarks/runtime_cost>`_.
Please re-run the scripts manually to obtain the results with the latest icontract version.
