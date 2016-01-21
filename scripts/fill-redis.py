# Fill redis DB with autocomplete values.
#
# For each entry  <NORMALIZED-VALUE>(<KEY>)&&<VALUE> in a file
# "term.txt" we do:
#
# - ZADD gnd-autocomplete 0 <NORMALIZED-VALUE>&&<KEY>
# - SET <KEY> <VALUE>
#
# (we do the Python equivalent, of course). Files of this format
# can be generated with the local `normalize.py` script.
#
# Example:
# Let "terms.txt" contain the two lines:
#
#   1&&foo&&Foo
#   2&&bar&&Bar
#
# then we will:
#
#   ZADD gnd-autocomplete 0 foo&&1
#   SET 1 Foo
#   ZADD gnd-autocomplete 0 bar&&2
#   SET 2 Bar
#
# This way we can please autocomplete widgets (looking for "a" can
# provide "bar&&2", "foo&&1" in that order) and asking for "1" then
# will provide "Foo".
#
import re
import redis

ENTRY_FORM = re.compile("^(.+)\&\&(.+)\&\&(.+)\n$")


client = redis.StrictRedis(host='localhost', port=6379, db=0)
print("Flushing any old redis contents...")
client.flushall()
print("Done")


with open("terms.txt", "r") as fd:
    cnt = 0
    for line in fd:
        match = ENTRY_FORM.match(line)
        if not match:
            continue
        key, normalized, content = match.groups()
        cnt += 1
        if cnt % 100000 == 0:
            print("CNT: %s" % cnt)
        try:
            result = client.zadd(
                "gnd-autocomplete", 0, "%s (%s)&&%s" % (
                    normalized, key, key))
            if not result:
                print("PROBLEM")
                print(cnt, key, content)
                print("--------")
            else:
                client.set(key, content)

        except:
            print("EXCEPT")
            print(cnt, key)
            print("++++++")

print client.zcard('gnd-autocomplete')
print(client.zcount('gnd-autocomplete', 0, 1))
