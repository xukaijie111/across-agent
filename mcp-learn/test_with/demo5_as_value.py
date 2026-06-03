"""Demo5: __enter__ / yield  return 什么，as 就是什么"""
from contextlib import contextmanager


@contextmanager
def outer():
    print("  打开 outer")
    yield "我是 yield 的值"
    print("  关闭 outer")


if __name__ == "__main__":
    with outer() as x:
        print(f"  as 后面 x = {x!r}")
