"""Only these IDs changed — one comparison both domains call.
changed_ids(expected, changed) -> dict(extras, misses, changed): `extras` are IDs that changed but were not expected to (named), `misses` are IDs
expected to change that did not (named); the comparison passes only when both are empty. IDs are whatever the domain uses: NFL kit column numbers,
Healix (A#, B#) pair tuples. status_changes(before, after) -> the IDs whose status differs between two dicts keyed by ID (an ID absent from `after`
counts as changed). Self-test: `python3 checks/changed_ids.py` injects one extra, one miss, and both, and requires each to be named exactly; exit 1 otherwise."""
import sys

def changed_ids(expected, changed):
    expected_set, changed_set = set(expected), set(changed)
    return dict(extras=sorted(changed_set - expected_set), misses=sorted(expected_set - changed_set), changed=sorted(changed_set))

def status_changes(before, after):
    return [k for k in before if k not in after or before[k] != after[k]]

if __name__ == "__main__":
    ok = True
    def expect(name, result, extras, misses):
        global ok; hit = result["extras"] == extras and result["misses"] == misses; ok &= hit
        print(f"  {name}: {'PASS' if hit else 'FAIL'} | extras {result['extras']} misses {result['misses']}")
    exp = [3, 30, 60]
    expect("clean: the expected IDs and only they changed", changed_ids(exp, [60, 30, 3]), [], [])
    expect("injected extra: 61 also changed -> named", changed_ids(exp, [3, 30, 60, 61]), [61], [])
    expect("injected miss: 30 did not change -> named", changed_ids(exp, [3, 60]), [], [30])
    expect("injected both -> both named", changed_ids(exp, [3, 60, 61]), [61], [30])
    pairs = [("A#1000", "B#11000"), ("A#1001", "B#11001")]
    before = {pairs[0]: "SUPPORTED", pairs[1]: "SUPPORTED"}; after = {pairs[0]: "never proposed", pairs[1]: "SUPPORTED"}
    expect("pair IDs: status change on one pair -> that pair only", changed_ids([pairs[0]], status_changes(before, after)), [], [])
    expect("pair IDs: injected second change -> named", changed_ids([pairs[0]], status_changes(before, {pairs[0]: "never proposed"})), [pairs[1]], [])
    print(f"CHANGED_IDS SELF-TEST: {'PASS' if ok else 'FAIL'}"); sys.exit(0 if ok else 1)
