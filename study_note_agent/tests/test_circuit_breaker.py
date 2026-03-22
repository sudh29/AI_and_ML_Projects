from agent import CircuitBreaker


def test_circuit_opens_after_threshold() -> None:
    cb = CircuitBreaker(failure_threshold=3)
    assert not cb.is_open
    cb.record_failure()
    cb.record_failure()
    assert not cb.is_open
    cb.record_failure()
    assert cb.is_open


def test_success_resets_failure_count() -> None:
    cb = CircuitBreaker(failure_threshold=2)
    cb.record_failure()
    cb.record_success()
    cb.record_failure()
    assert not cb.is_open
