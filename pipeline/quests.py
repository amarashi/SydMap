"""Quests: short walks through Sydney as riddles. Three kinds of step, mixed within a quest:

  find    a riddle; the player finds the building on the map and clicks it. Hints first draw a circle around it,
          then add the written hints; "Show me" flies there for no marks.
  year    the map flies to a building and hides its age (colours and card); the player guesses the year it was built.
  choice  the map flies to a building; the player picks one of three answers (the right one first; the page shuffles).

Every claim rests on a Wikipedia article that must contain the given strings (pipeline/checks.py); s08_quests drops a
step whose checks fail. Where a step asks for a year, that year must also be the map's year for the building, so the
card the player opens next tells the same story.

`at` says where the step happens: "wd:<Q-id>" (the buildings linked to that Wikidata item) or "id:<building id>".
Levels: 1 easy, 2 medium, 3 hard.
"""

WP = "https://en.wikipedia.org/wiki/"


def find(at, riddle, hints, reveal, checks, photo=False, mode=None):
    return dict(kind="find", at=at, riddle=riddle, hints=hints, reveal=reveal, checks=checks, photo=photo, mode=mode)


def year(at, ask, answer, reveal, checks):
    return dict(kind="year", at=at, ask=ask, year=answer, reveal=reveal, checks=checks)


def choice(at, ask, options, reveal, checks):
    return dict(kind="choice", at=at, ask=ask, options=options, reveal=reveal, checks=checks)


QUESTS = [
    # ---------------------------------------------------------------- easy
    dict(id="quay", level=1, title="Around Circular Quay",
         intro="Five places within a few minutes' walk of the ferries. A gentle start.",
         steps=[
             find("wd:Q45178",
                  "Start with the city's signature: the performing arts centre whose roofs are a cluster of white shells.",
                  ["It occupies the whole of the point between Sydney Cove and Farm Cove."],
                  "The Sydney Opera House, by the Danish architect Jørn Utzon, formally opened by Queen Elizabeth II on "
                  "20 October 1973. It covers the whole of Bennelong Point.",
                  [("Sydney Opera House", ["Designed by Danish architect Jørn Utzon",
                                           "formally opened by Queen Elizabeth II on 20 October 1973",
                                           "occupy the whole of Bennelong Point on Sydney Harbour, between Sydney Cove and Farm Cove"])],
                  photo=True),
             year("id:sydney-harbour-bridge",
                  "They call it the Coathanger. In what year did the Harbour Bridge open?", 1932,
                  "1932. Built by Dorman Long of Middlesbrough under the direction of John Bradfield, the bridge was "
                  "formally opened on Saturday, 19 March 1932.",
                  [("Sydney Harbour Bridge", ['Nicknamed "the Coathanger"', "built by British firm Dorman Long of Middlesbrough",
                                              "formally opened on Saturday, 19 March 1932"])]),
             find("wd:Q1025284",
                  "Find the small sandstone house built in 1816 for the government's coxswains, once almost at the water's edge.",
                  ["It is at 110 George Street, The Rocks."],
                  "Cadmans Cottage. At high tide the water came within 2.4 metres of it; since the land was reclaimed "
                  "for Circular Quay, the shore is about 100 metres away.",
                  [("Cadmans Cottage", ["110 George Street", "built in 1816 for the use of the governmental coxswains",
                                        "within 2.4 metres (8 ft) of Cadmans Cottage",
                                        "the waterline has moved about 100 metres (330 ft) away since 1816"])]),
             choice("wd:Q690242",
                    "The Museum of Contemporary Art on Circular Quay moved into a building put up for whom?",
                    ["The Maritime Services Board", "The Royal Navy", "The Bank of New South Wales"],
                    "The Maritime Services Board. The museum, established in 1991, is housed in the board's former "
                    "Stripped Classical and Art Deco building on the western side of Circular Quay.",
                    [("Museum of Contemporary Art Australia", ["former Maritime Services Board (MSB) building",
                                                                "western side of Circular Quay",
                                                                "the Museum of Contemporary Art, Sydney was established in 1991"])]),
             year("wd:Q5196499",
                  "Customs House stands at the head of Circular Quay. When was it built?", 1845,
                  "1845, to designs by Mortimer Lewis. It housed the customs until 1988 and is now home to the City of "
                  "Sydney Library.",
                  [("Customs House, Sydney", ["The initial designs were by Mortimer Lewis", "built during 1845",
                                              "until 1988", "City of Sydney Library"])]),
         ]),
    dict(id="shops", level=1, title="Shops and stages",
         intro="The arcades, picture palaces and department stores of the city centre.",
         steps=[
             find("wd:Q54518",
                  "Find the Romanesque Revival marketplace that fills a whole city block.",
                  ["The block is bounded by George, Market, York and Druitt streets."],
                  "The Queen Victoria Building, designed by George McRae and built between 1893 and 1898: 30 metres "
                  "wide and 190 metres long.",
                  [("Queen Victoria Building", ["Designed by the architect George McRae", "constructed between 1893 and 1898",
                                                "30 metres (98 ft) wide by 190 metres (620 ft) long",
                                                "bounded by George, Market, York, and Druitt streets"])],
                  photo=True),
             year("wd:Q7766877",
                  "The Strand Arcade runs from Pitt Street Mall to George Street. When did it open?", 1892,
                  "1892, after two years of building. It is the only remaining arcade of its kind in Sydney.",
                  [("The Strand Arcade", ["built from 1890 to 1892", "When the arcade opened in 1892",
                                          "The only remaining arcade of its kind in Sydney"])]),
             find("wd:Q7603582",
                  "Find the picture palace on Market Street that has been home to the Sydney Film Festival since 1974.",
                  ["It seats 2,034."],
                  "The State Theatre, designed by Henry Eli White with John Eberson and built between 1926 and 1929.",
                  [("State Theatre (Sydney)", ["2,034 seat", "Market Street",
                                               "since 1974 it has been the home of the annual Sydney Film Festival",
                                               "built between 1926 and 1929"])]),
             choice("wd:Q5303192",
                    "The Downing Centre on Liverpool Street houses courts today. What was it built as?",
                    ["Mark Foy's department store", "A railway goods shed", "A wool store"],
                    "A department store: Mark Foy's Piazza Store, built for Mark Foy in 1908 to designs by Arthur "
                    "Anderson and much extended in 1927–1930.",
                    [("Downing Centre", ["originally known as Mark Foy's Piazza Store", "former department store",
                                         "built for Mark Foy in 1908, designed by Arthur Anderson"])]),
             find("wd:Q14935037",
                  "Finally, look up: find the tower that stands 309 metres above the city, the tallest structure in Sydney.",
                  ["It rises from a shopping centre between Pitt, Market and Castlereagh streets."],
                  "Sydney Tower, long known as Centrepoint Tower. It sits above the Westfield Sydney shopping centre.",
                  [("Sydney Tower", ["stands 309 m (1,014 ft)", "the tallest structure in Sydney",
                                     "between Pitt and Castlereagh Streets", "sits above the Westfield Sydney"])],
                  mode="floors"),
         ]),
    # ---------------------------------------------------------------- medium
    dict(id="macquarie", level=2, title="Macquarie Street and the park",
         intro="Convicts, rum and the oldest public buildings of the colony, along the street Governor Macquarie built.",
         steps=[
             find("wd:Q1577600",
                  "Find the brick barracks a convict architect designed to house convict men and boys.",
                  ["It is on Macquarie Street."],
                  "Hyde Park Barracks, built between 1817 and 1819 to designs by the convict architect Francis Greenway. "
                  "It is one of the eleven Australian Convict Sites on the UNESCO World Heritage List.",
                  [("Hyde Park Barracks, Sydney", ["constructed between 1817 and 1819", "convict architect Francis Greenway",
                                                   "located at Macquarie Street", "one of 11 pre-eminent Australian Convict Sites"])]),
             choice("wd:Q1641346",
                    "The Sydney Mint was built between 1811 and 1816 as one wing of a hospital. What was the hospital called?",
                    ["The Rum Hospital", "The Gin Hospital", "The Convict Infirmary"],
                    "The Rum Hospital: its builders were paid with 45,000 gallons of rum. The Mint, its southern wing, "
                    "is the oldest surviving public building in the city centre.",
                    [("Sydney Mint", ["Built between 1811 and 1816 as the southern wing of the Sydney Hospital",
                                      "paid with 45,000 gallons of rum hence the name Rum Hospital",
                                      "oldest surviving public building in the Sydney central business district"])]),
             year("wd:Q5600072",
                  "The Great Synagogue faces Hyde Park from Elizabeth Street. When was it finished?", 1878,
                  "1878, after four years' building to designs by Thomas Rowe. Its congregation is the oldest in Sydney's "
                  "Jewish community.",
                  [("Great Synagogue (Sydney)", ["designed by Thomas Rowe and constructed between 1874 and 1878",
                                                 "Situated opposite Hyde Park",
                                                 "The congregation is the oldest in the Sydney Jewish community"])]),
             find("wd:Q844556",
                  "Find the Art Deco war memorial in the southern half of Hyde Park.",
                  ["It is near Liverpool Street."],
                  "The Anzac Memorial, designed by C. Bruce Dellit with sculpture by Rayner Hoff, built from 1932 to "
                  "1934 and opened on 24 November 1934.",
                  [("Anzac Memorial", ["Hyde Park South near Liverpool Street", "designed by C. Bruce Dellit",
                                       "sculptures by Rayner Hoff", "built from 1932 to 1934",
                                       "opened on 24 November 1934"])],
                  photo=True),
             choice("wd:Q1088015",
                    "St Andrew's Cathedral stands beside the Town Hall. What does it claim?",
                    ["The oldest cathedral in Australia", "The tallest spire in Australia", "The first church in Sydney"],
                    "The oldest cathedral in Australia: designed mainly by Edmund Blacket, built from 1837 and "
                    "consecrated in 1868.",
                    [("St Andrew's Cathedral, Sydney", ["Designed primarily by Edmund Blacket",
                                                        "consecrated in 1868, making it the oldest cathedral in Australia"])]),
         ]),
    dict(id="rocks", level=2, title="Pubs of The Rocks",
         intro="Which is Sydney's oldest pub? Walk the ridge above the harbour and judge for yourself.",
         steps=[
             year("wd:Q58242651",
                  "The Lord Nelson in Millers Point is the oldest working licensed hotel in Sydney. When was it built?", 1815,
                  "Around 1814 to 1815, by the Irish-born stonemason James Dempsey.",
                  [("Lord Nelson Hotel, Millers Point", ["built by James Dempsey around 1814 to 1815",
                                                         "originally a stonemason born in Ireland",
                                                         "the oldest working licensed hotel in Sydney"])]),
             find("wd:Q58242738",
                  "Find the pub on Lower Fort Street, Millers Point, built from 1843 to 1844.",
                  ["Its name remembers Wellington's great battle."],
                  "The Hero of Waterloo Hotel, built from 1843 to 1844.",
                  [("Hero of Waterloo Hotel", ["Lower Fort Street", "built from 1843 to 1844"])]),
             choice("wd:Q58205259",
                    "The Fortune of War on George Street advertises itself as Sydney's oldest pub. Why is that contested?",
                    ["Its present building only dates from 1922", "It lost its licence for twenty years", "It moved from Parramatta"],
                    "The pub was first built in 1828, but the present building dates from 1922, so the Lord Nelson and "
                    "the Hero of Waterloo contest the title.",
                    [("Fortune of War Hotel", ['advertises itself as "Sydney\'s oldest pub"', "First built in 1828",
                                               "the present building only dates from 1922"])]),
             find("wd:Q7648734",
                  "Find the row of workers' cottages and a corner store on Gloucester Street, lived in until 1990 and now a museum.",
                  ["It was built in 1844."],
                  "Susannah Place: a grocery store and workers' cottages, built during 1844, with domestic occupants until 1990.",
                  [("Susannah Place", ["former grocery store and workers' cottages", "Gloucester Street",
                                       "built during 1844", "domestic occupants until 1990"])]),
             find("wd:Q18165591",
                  "End at church: find the first military church built in colonial Australia.",
                  ["It is on Argyle Street."],
                  "The Garrison Church, Holy Trinity, built from 1840 to 1846; Edmund Blacket designed its second stage.",
                  [("Garrison Church, Sydney", ["Argyle Street", "built from 1840 to 1846", "Edmund Blacket (2nd stage)",
                                                "the first military church built in colonial Australia"])]),
         ]),
    # ---------------------------------------------------------------- hard
    dict(id="skyline", level=3, title="Up and across the harbour",
         intro="The towers that broke Sydney's skyline, and the houses across the water. With the colours off, mostly.",
         steps=[
             year("wd:Q300206",
                  "The AWA Tower on York Street is a radio mast on an office building. When was it finished?", 1939,
                  "1939. It was Australia's tallest building until the 115-metre AMP Building was built in 1962.",
                  [("AWA Tower", ["built from 1937 to 1939",
                                  "Australia's tallest building from 1939 until the construction of the 115-metre-tall (377 ft) AMP Building, Sydney, in 1962"])]),
             find("wd:Q54490",
                  "Find the skyscraper that was the tallest building in Sydney from 1992 to 2019.",
                  ["It is 244 metres tall."],
                  "Chifley Tower, 53 storeys, designed by Kohn Pedersen Fox with Travis McEwen.",
                  [("Chifley Tower", ["53-storey skyscraper", "244 metres", "tallest building in Sydney from 1992 to 2019"])],
                  mode="floors"),
             find("wd:Q16890775",
                  "Now find the tower that overtook it in 2020, built on the paved-over wharves of Barangaroo.",
                  ["It is 271 metres tall, with 75 floors."],
                  "Crown Sydney, also known as One Barangaroo: 271.3 metres, the tallest building in Sydney.",
                  [("Crown Sydney", ["One Barangaroo", "271.3 m (890 ft) with 75 floors", "the tallest building in Sydney",
                                     "the site of former industrial wharves"])],
                  mode="floors"),
             find("wd:Q4930479",
                  "Cross the harbour: find the 83-metre apartment block at McMahons Point that some critics call one of "
                  "Sydney's ugliest buildings.",
                  ["It has 144 apartments over 24 levels."],
                  "Blues Point Tower, 83 metres tall with 144 apartments over 24 levels.",
                  [("Blues Point Tower", ["McMahons Point", "83 metres (272 ft) tall with 144 apartments over 24 levels",
                                          "one of the ugliest buildings in Sydney"])]),
             choice("wd:Q1369561",
                    "Two official residences share Kirribilli Point. Admiralty House is the Governor-General's; whose is "
                    "Kirribilli House?",
                    ["The Prime Minister's", "The Premier of New South Wales's", "The Lord Mayor of Sydney's"],
                    "The Prime Minister's: Kirribilli House is the secondary official residence of the prime minister, "
                    "beside Admiralty House, the governor-general's Sydney residence.",
                    [("Kirribilli House", ["secondary official residence of the prime minister of Australia"]),
                     ("Admiralty House, Sydney", ["official residence of the governor-general of Australia in Sydney",
                                                  "adjacent to Kirribilli House"])]),
         ]),
]
