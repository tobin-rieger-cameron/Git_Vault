def fixed(o):
    try:
        hash(o)
    except TypeError:
        return False
    return True


a = (10, "alpha", (1, 2))
b = (10, "alpha", [1, 2])

print("a is: ", {fixed(a)}, " and b is: ", {fixed(b)})


lax_coordinates = (33.9425, -118.408056)
latitude, longitude = lax_coordinates  # unpacking

print("latitude is: ", {latitude})
print("longitude is: ", {longitude})
