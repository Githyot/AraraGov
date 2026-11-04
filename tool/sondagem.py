import collections
import xml.etree.ElementTree as E

r = E.parse("/tmp/dep.xml").getroot()
print(len(r))
for c in r[0]:
    if c.tag != "Biografia":
        print(c.tag, (c.text or "")[:80].replace("\n", " "))
print(collections.Counter(x.findtext("Situacao") for x in r))
c = collections.Counter()
tags = set()
last = None
for ev, el in E.iterparse("/tmp/d.xml"):
    if el.tag == "despesa":
        tags |= {x.tag for x in el}
        c[el.findtext("Ano")] += 1
        last = E.tostring(el)[:600]
        el.clear()
print(sorted(tags))
print(sorted(c.items()))
print(last)
