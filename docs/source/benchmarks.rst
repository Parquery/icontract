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
We used Python 3.8.5, icontract 2.4.1, deal 4.1.0 and dpcontracts 0.6.0.

The following tables summarize the results.

Benchmarking invariant at __init__:

=========================  ============  ==============  =======================
Case                         Total time    Time per run    Relative time per run
=========================  ============  ==============  =======================
`ClassWithIcontract`             1.33 s         1.33 μs                     100%
`ClassWithDpcontracts`           0.45 s         0.45 μs                      34%
`ClassWithDeal`                  2.62 s         2.62 μs                     197%
`ClassWithInlineContract`        0.27 s         0.27 μs                      20%
=========================  ============  ==============  =======================

Benchmarking invariant at a function:

=========================  ============  ==============  =======================
Case                         Total time    Time per run    Relative time per run
=========================  ============  ==============  =======================
`ClassWithIcontract`             1.98 s         1.98 μs                     100%
`ClassWithDpcontracts`           0.46 s         0.46 μs                      23%
`ClassWithDeal`                  7.13 s         7.13 μs                     360%
`ClassWithInlineContract`        0.23 s         0.23 μs                      12%
=========================  ============  ==============  =======================

Benchmarking precondition:

===============================  ============  ==============  =======================
Case                               Total time    Time per run    Relative time per run
===============================  ============  ==============  =======================
`function_with_icontract`              0.04 s         3.71 μs                     100%
`function_with_dpcontracts`            0.51 s        50.52 μs                    1361%
`function_with_deal`                   0.13 s        12.64 μs                     341%
`function_with_inline_contract`        0.00 s         0.15 μs                       4%
===============================  ============  ==============  =======================

Benchmarking postcondition:

===============================  ============  ==============  =======================
Case                               Total time    Time per run    Relative time per run
===============================  ============  ==============  =======================
`function_with_icontract`              0.04 s         3.97 μs                     100%
`function_with_dpcontracts`            0.51 s        50.51 μs                    1274%
`function_with_deal_post`              0.01 s         0.90 μs                      23%
`function_with_deal_ensure`            0.01 s         1.23 μs                      31%
`function_with_inline_contract`        0.00 s         0.15 μs                       4%
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
