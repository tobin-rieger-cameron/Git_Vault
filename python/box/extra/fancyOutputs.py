import math

# formatted string litterals

year = 2016
event = 'Referendum'
print(f'Results of the {year} {event}')


# str.format() method

yes_votes = 42_572_654
total_votes = 85_705_149
percentage = yes_votes / total_votes
print('{:-9} YES votes  {:2.2%}'.format(yes_votes, percentage))


# using str() or repr()

s = 'Hello, world.'
print(str(s))
print(repr(s))

print(str(1/7))
print(repr(1/7))

x = 10 * 3.25
y = 200 * 200
s = 'The value of x is ' + repr(x) + ', and y is ' + repr(y) + '...'
print(s)

hello = 'hello, world\n'
hellos = repr(hello)
print(hellos)

print(repr((x, y, ('spam', 'eggs'))))

print(f'The value of pi is approximately {math.pi:.5f}.')


table = {'Sjoerd': 4127, 'Jack': 4098, 'Dcab': 7678}
for name, phone in table.items():
    print(f'{name:10} ==> {phone:10d}')
