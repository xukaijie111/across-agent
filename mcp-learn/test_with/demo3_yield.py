"""Demo3: @contextmanager — yield 前=enter，yield 后=exit"""
from contextlib import contextmanager


@contextmanager
def my_pipe():
    print("  [yield 前] spawn 子进程、接管道")
    read, write = "READ", "WRITE"
   
    print("  [yield 后] 关管道、杀进程")
    return read, write


if __name__ == "__main__":
    print("=== 使用管道 ===")
    with my_pipe() as (read, write):
        print(f"  [块内] read={read}, write={write}")

    print("=== 结束 ===")
