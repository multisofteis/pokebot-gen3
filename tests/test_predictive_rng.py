from modules.predictive_rng import Gen3Rng, is_shiny_pid, shiny_value


def test_rng_advance_matches_repeated_calls():
    for calls in (0, 1, 2, 7, 64, 1000):
        iterative = Gen3Rng(0x12345678)
        fast_forwarded = Gen3Rng(0x12345678)

        for _ in range(calls):
            iterative.next_u16()

        assert fast_forwarded.advance(calls) == iterative.state
        assert fast_forwarded.state == iterative.state


def test_next_u32_consumes_two_rng_calls():
    combined = Gen3Rng(0x12345678)
    separate = Gen3Rng(0x12345678)

    pid = combined.next_u32()
    expected = (separate.next_u16() << 16) | separate.next_u16()

    assert pid == expected
    assert combined.state == separate.state


def test_generation_three_shiny_pid_math():
    trainer_id = 1234
    secret_id = 5678
    pid = ((trainer_id ^ secret_id) << 16)

    assert shiny_value(pid, trainer_id, secret_id) == 0
    assert is_shiny_pid(pid, trainer_id, secret_id)
    assert not is_shiny_pid(0, 0, 100)
