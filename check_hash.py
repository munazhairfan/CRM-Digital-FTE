import hashlib
id1 = 'sara@test.com'
id2 = '15550000001'
for i in [id1, id2]:
    h = hashlib.md5(i.encode()).hexdigest()
    uuid = f'{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}'
    print(f'{i} -> {uuid}')
