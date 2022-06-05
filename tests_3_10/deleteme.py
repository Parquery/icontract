from icontract import ensure

@ensure(
    lambda a, b, result: 
    result == myadd(b, a),  # type: ignore
    "Commutativity violated!"
)
def myadd(a: int, b: int) -> int:
    return a + b