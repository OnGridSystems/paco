# -*- coding: utf-8 -*-
import time
import pytest
import asyncio
from paco import concurrent
from .helpers import sleep_coro, run_in_loop


@asyncio.coroutine
def run_test(limit=3, times=10, timespan=0.1):
    p = concurrent(limit)
    for i in range(times):
        p.add(sleep_coro, timespan)
    return (yield from p.run())


def test_concurrent_single():
    @asyncio.coroutine
    def coro(num):
        return num * 2

    p = concurrent(10)
    p.add(coro, 2)
    assert len(p) == 1
    assert p.__len__() == 1
    assert len(p.pool) == 1

    done, pending = run_in_loop(p.run())

    assert len(done) == 1
    assert len(pending) == 0

    for future in done:
        assert future.result() == 4


def test_concurrent():
    timespan, times, limit = 0.1, 10, 3
    start = time.time()
    done, pending = run_in_loop(
        run_test(limit=limit, times=times, timespan=timespan)
    )
    assert time.time() - start >= (times * timespan / limit)
    assert len(done) == times
    assert len(pending) == 0

    for future in done:
        assert future.result() >= 0.1


def test_concurrent_high_limit():
    timespan, times, limit = 0.1, 1000, 100
    start = time.time()
    done, pending = run_in_loop(
        run_test(limit=limit, times=times, timespan=timespan)
    )
    assert time.time() - start >= (times * timespan / limit)
    assert len(done) == times
    assert len(pending) == 0

    for future in done:
        assert future.result() >= 0.1


def test_concurrent_sequential():
    timespan, times, limit = 0.05, 10, 1
    start = time.time()
    done, pending = run_in_loop(
        run_test(limit=limit, times=times, timespan=timespan)
    )
    assert time.time() - start >= (times * timespan / limit)
    assert len(done) == times
    assert len(pending) == 0

    for future in done:
        assert future.result() >= 0.05


def test_concurrent_ignore_empty():
    runner = concurrent(ignore_empty=True)
    done, pending = run_in_loop(runner.run())
    assert len(done) == 0
    assert len(pending) == 0

    runner = concurrent()
    done, pending = run_in_loop(runner.run(ignore_empty=True))
    assert len(done) == 0
    assert len(pending) == 0


def test_concurrent_empty_error():
    with pytest.raises(ValueError):
        run_in_loop(concurrent().run())


def test_concurrent_observe():
    start = []
    finish = []

    @asyncio.coroutine
    def coro(num):
        return num * 2

    @asyncio.coroutine
    def on_start(task):
        start.append(task)

    @asyncio.coroutine
    def on_finish(task, result):
        finish.append(result)

    p = concurrent(10)
    p.on('task.start', on_start)
    p.on('task.finish', on_finish)

    p.add(coro, 2)
    p.add(coro, 4)
    p.add(coro, 6)
    assert len(p.pool) == 3

    done, pending = run_in_loop(p.run())
    assert len(done) == 3
    assert len(pending) == 0

    # Assert event calls
    assert len(start) == 3
    assert len(finish) == 3

    results = [future.result() for future in done]
    results.sort()
    assert results == [4, 8, 12]

    finish.sort()
    assert finish == [4, 8, 12]


def test_concurrent_observe_exception():
    start = []
    error = []
    finish = []

    @asyncio.coroutine
    def coro(num):
        if num > 4:
            raise ValueError('invalid number')
        return num * 2

    @asyncio.coroutine
    def on_start(task):
        start.append(task)

    @asyncio.coroutine
    def on_error(task, err):
        error.append(err)

    @asyncio.coroutine
    def on_finish(task, result):
        finish.append(result)

    p = concurrent(1)
    p.on('task.start', on_start)
    p.on('task.error', on_error)
    p.on('task.finish', on_finish)

    p.add(coro, 2)
    p.add(coro, 4)
    p.add(coro, 6)
    assert len(p.pool) == 3

    with pytest.raises(ValueError):
        run_in_loop(p.run(return_exceptions=False))

    # Assert event calls
    assert len(start) == 3
    assert len(error) == 1
    assert len(finish) == 2

    finish.sort()
    assert finish == [4, 8]
