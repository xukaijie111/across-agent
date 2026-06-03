


gen = (x for x in range(3))

print(gen)
print(gen.__iter__)

print(gen.__iter__() == gen)
print(next(gen))
print(next(gen))
print(next(gen))
print(next(gen))