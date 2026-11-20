#!/usr/bin/env python3
"""Fetch clean HTML snippets from legislation.gov.uk and build JSON."""
import json, re, urllib.request, ssl, time

BASE = "https://www.legislation.gov.uk/ukpga/Eliz2/4-5/74"

def fetch(url):
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible)'})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
            return r.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"Error: {url} -> {e}")
        return ""

def strip_html(html):
    t = re.sub(r'<[^>]+>', ' ', html)
    for old, new in [('&amp;','&'),('&lt;','<'),('&gt;','>'),('&quot;','"'),
                      ('&#160;',' '),('&nbsp;',' '),('&mdash;','\u2014'),
                      ('&#8212;','\u2014'),('&#8220;','\u201c'),('&#8221;','\u201d'),
                      ('&#8216;','\u2018'),('&#8217;','\u2019'),('&apos;',"'")]:
        t = t.replace(old, new)
    t = re.sub(r'[ \t]+', ' ', t)
    lines = [l.strip() for l in t.split('\n') if l.strip()]
    return ' '.join(lines)

def get_part(n):
    if 1<=n<=11: return "PART I - Copyright in Original Works"
    if 12<=n<=16: return "PART II - Copyright in Sound Recordings, Cinematograph Films, Broadcasts, etc."
    if 17<=n<=22: return "PART III - Remedies for Infringements of Copyright"
    if 23<=n<=30: return "PART IV - Performing Right Tribunal"
    if 31<=n<=35: return "PART V - Extension or Restriction of Operation of Act"
    if 36<=n<=51: return "PART VI - Miscellaneous and Supplementary Provisions"
    return ""

TITLES = {
    1: "Nature of copyright under this Act",
    2: "Copyright in literary, dramatic and musical works",
    3: "Copyright in artistic works",
    4: "Ownership of copyright in certain cases",
    5: "Infringement by importation, sale and other dealings",
    6: "General exceptions from protection of literary, dramatic and musical works",
    7: "Special exceptions as respects libraries and archives",
    8: "Special exception in respect of records of musical works",
    9: "General exceptions from protection of artistic works",
    10: "Special exception in respect of industrial designs",
    11: "Provisions as to anonymous and pseudonymous works, and works of joint authorship",
    12: "Copyright in sound recordings",
    13: "Copyright in cinematograph films",
    14: "Copyright in television broadcasts and sound broadcasts",
    15: "Copyright in published editions of works",
    16: "Supplementary provisions for purposes of Part II",
    17: "Action by owner of copyright for infringement",
    18: "Rights of owner of copyright in respect of infringing copies, etc.",
    19: "Proceedings in case of copyright subject to exclusive licence",
    20: "Proof of facts in copyright actions",
    21: "Penalties and summary proceedings in respect of dealings which infringe copyright",
    22: "Provision for restricting importation of printed copies",
    23: "Establishment of tribunal",
    24: "General provisions as to jurisdiction of tribunal",
    25: "Reference of licence schemes to tribunal",
    26: "Further reference of scheme to tribunal",
    27: "Applications to tribunal",
    28: "Exercise of jurisdiction of tribunal in relation to diffusion of foreign broadcasts",
    29: "Effect of orders of tribunal, and supplementary provisions relating thereto",
    30: "Reference of questions of law to the court",
    31: "Extension of Act to Isle of Man, Channel Islands, colonies and dependencies",
    32: "Application of Act to countries to which it does not extend",
    33: "Provisions as to international organisations",
    34: "Extended application of provisions relating to broadcasts",
    35: "Denial of copyright to citizens of countries not giving adequate protection to British works",
    36: "Assignments and licences in respect of copyright",
    37: "Prospective ownership of copyright",
    38: "Copyright to pass under will with unpublished work",
    39: "Provisions as to Crown and Government departments",
    40: "Broadcasts of sound recordings and cinematograph films, and diffusion of broadcast programmes",
    41: "Use of copyright material for education",
    42: "Special provisions as to public records",
    43: "False attribution of authorship",
    44: "Amendments of Registered Designs Act, 1949",
    45: "Amendment of Dramatic and Musical Performers' Protection Act, 1925",
    46: "Savings",
    47: "General provisions as to Orders in Council, regulations, rules and orders, and as to Board of Trade",
    48: "Interpretation",
    49: "Supplementary provisions as to interpretation",
    50: "Transitional provisions, and repeals",
    51: "Short title, commencement and extent",
}

SCHED_TITLES = {
    "FIRST": "False Registration of Industrial Designs",
    "SECOND": "Duration of Copyright in Anonymous and Pseudonymous Works",
    "THIRD": "Works of Joint Authorship",
    "FOURTH": "Provisions as to Performing Right Tribunal",
    "FIFTH": "Appointment of Television Copyright Organisations by BBC and ITA",
    "SIXTH": "Amendment of Dramatic and Musical Performers' Protection Act, 1925",
    "SEVENTH": "Transitional Provisions",
    "EIGHTH": "Provisions of Copyright Act, 1911, and Rules, referred to in Seventh Schedule",
    "NINTH": "Enactments Repealed",
}

# Pre-provided sections 1-9 and introduction
PROVIDED_INTRO = "An Act to make new provision in respect of copyright and related matters, in substitution for the provisions of the Copyright Act, 1911, and other enactments relating thereto; to amend the Registered Designs Act, 1949, with respect to designs related to artistic works in which copyright subsists, and to amend the Dramatic and Musical Performers' Protection Act, 1925; and for purposes connected with the matters aforesaid. [5th November, 1956] Be it enacted by the Queen's most Excellent Majesty, by and with the advice and consent of the Lords Spiritual and Temporal, and Commons, in this present Parliament assembled, and by the authority of the same, as follows:\u2014"

PROVIDED_S1 = '(1)In this Act "copyright" in relation to a work (except where the context otherwise requires) means the exclusive right, by virtue and subject to the provisions of this Act, to do, and to authorise other persons to do, certain acts in relation to that work in the United Kingdom or in any other country to which the relevant provision of this Act extends. The said acts, in relation to a work of any description, are those acts which, in the relevant provision of this Act, are designated as the acts restricted by the copyright in a work of that description. (2)In accordance with the preceding subsection, but subject to the following provisions of this Act, the copyright in a work is infringed by any person who, not being the owner of the copyright, and without the licence of the owner thereof, does, or authorises another person to do, any of the said acts in relation to the work in the United Kingdom or in any other country to which the relevant provision of this Act extends. (3)In the preceding subsections references to the relevant provision of this Act, in relation to a work of any description, are references to the provision of this Act whereby it is provided that (subject to compliance with the conditions specified therein) copyright shall subsist in works of that description. (4)The preceding provisions of this section shall apply, in relation to any subject-matter (other than a work) of a description to which any provision of Part II of this Act relates, as they apply in relation to a work. (5)For the purposes of any provision of this Act which specifies the conditions under which copyright may subsist in any description of work or other subject-matter, "qualified person"\u2014 (a)in the case of an individual, means a person who is a British subject or British protected person or a citizen of the Republic of Ireland or (not being a British subject or British protected person or a citizen of the Republic of Ireland) is domiciled or resident in the United Kingdom or in another country to which that provision extends, and (b)in the case of a body corporate, means a body incorporated under the laws of any part of the United Kingdom or of another country to which that provision extends. In this subsection "British protected person" has the same meaning as in the British Nationality Act, 1948.'

results = []

# Introduction
results.append({
    "id": "introduction",
    "part": "",
    "title": "Introduction",
    "section_number": None,
    "text": PROVIDED_INTRO,
    "url": f"{BASE}/introduction/enacted"
})

# Section 1 (provided)
results.append({
    "id": "section-1",
    "part": get_part(1),
    "title": TITLES[1],
    "section_number": 1,
    "text": PROVIDED_S1,
    "url": f"{BASE}/section/1/enacted"
})

# Sections 2-51: fetch from data.xht
for n in range(2, 52):
    url = f"{BASE}/section/{n}/enacted"
    xht_url = f"{url}/data.xht"
    print(f"Fetching section {n}...")
    html = fetch(xht_url)
    text = strip_html(html) if html else ""
    results.append({
        "id": f"section-{n}",
        "part": get_part(n),
        "title": TITLES.get(n, ""),
        "section_number": n,
        "text": text,
        "url": url
    })
    time.sleep(0.3)

# Schedules
for name in ["FIRST","SECOND","THIRD","FOURTH","FIFTH","SIXTH","SEVENTH","EIGHTH","NINTH"]:
    url = f"{BASE}/schedule/{name}/enacted"
    xht_url = f"{url}/data.xht"
    print(f"Fetching schedule {name}...")
    html = fetch(xht_url)
    text = strip_html(html) if html else ""
    results.append({
        "id": f"schedule-{name}",
        "part": "SCHEDULES",
        "title": SCHED_TITLES.get(name, ""),
        "section_number": None,
        "text": text,
        "url": url
    })
    time.sleep(0.3)

with open("data/copyright_act_1956_sections.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\nDone! Wrote {len(results)} entries to data/copyright_act_1956_sections.json")
