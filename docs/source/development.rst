Development
===========

* Check out the repository.

* In the repository root, create the virtual environment:

.. code-block:: bash

    python3 -m venv venv3

* Activate the virtual environment:

.. code-block:: bash

    source venv3/bin/activate

* Install the development dependencies:

.. code-block:: bash

    pip3 install -e .[dev]

* We use tox for testing and packaging the distribution. Run:

.. code-block:: bash

    tox

* We also provide a set of pre-commit checks that lint and check code for formatting. Run them locally from an activated
  virtual environment with development dependencies:

.. code-block:: bash

    ./precommit.py

* The pre-commit script can also automatically format the code:

.. code-block:: bash

    ./precommit.py  --overwrite


Commit Message Style
--------------------

Use the following guidelines for commit message.

* Past tense in the subject & body
* Max. 50 characters subject
* Max. 72 characters line length in the body (multiple lines are ok)
* Past tense in the body
* Have separate commits for the releases where the important changes are highlighted

See examples from past commits at https://github.com/Parquery/icontract/commits/master/
