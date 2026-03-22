colors = ['black', 'white']
sizes = ['S', 'M', 'L']
# sorted by color and then size
tshirts = [(color, size) for color in colors for size in sizes]
print(tshirts)

for color in colors:
    for size in sizes:
        print((color, size))

# sorted by size, then color
tshirts = [(color, size) for size in sizes for color in colors]
print(tshirts)
