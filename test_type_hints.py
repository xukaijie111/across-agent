


def test():
    print("test")
    yield 1
    print("test2")
    yield 2
    print("test3")
    yield 3
    


aa = test();
print(next(aa))
print(next(aa)) 
print(next(aa))
print(next(aa))
# print(next(aa))