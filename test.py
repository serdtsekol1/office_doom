items = [
    [1, 2, 'dsfsdf', 1.44],
    [54, 'sdf', 'dsfsdf', 1.44],
    [12, 22, 'sdfsdfdsf', 2.44],
]
# qty, id, name, sum

qty = {"coordinate": "0", "int" : True, "Str" : False}

qty = {'can_be': (int, float), 'cant_be': (str,)}
id = {'can_be': (int,), 'cant_be': (str, float)}
name = {'can_be': (str,), 'cant_be': (int, float)}
sum = {'can_be': (int, float), 'cant_be': (str,)}

for item in items:
    if isinstance(item[0], (qty['can_be'])) and isinstance(item[1], (id['can_be'])) and isinstance(item[2], (name['can_be'])) and isinstance(item[3], (sum['can_be'])):
        print(item)
