"""Demo1: 同步 with — __enter__ 打开，__exit__ 关闭"""


class MyConnection:
    def __enter__(self):
        print("  [__enter__] 打开连接")
        return "pipe-123"  # as 后面拿到这个，不是 self

    def __exit__(self, exc_type, exc, tb):
        print("  [__exit__] 关闭连接")
        return False  # False = 不吞异常


if __name__ == "__main__":
    print("=== 正常结束 ===")
    with MyConnection() as conn:
        print(f"  [with 块内] 使用 {conn}")

    print("=== with 已结束 ===\n")

    print("=== 块内报错 ===")
    try:
        with MyConnection() as conn:
            print(f"  [with 块内] 使用 {conn}")
            raise ValueError("故意报错")
    except ValueError:
        print("  [外面] 捕获到异常")
