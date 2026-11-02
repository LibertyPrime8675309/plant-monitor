"""Uses, partners, deterrents, propagation and breeding for the species in Ethan's record (batch A9, 1.27.0).
Written by Claude from general horticultural references (extension services, botanic gardens, ASPCA), November 2026.
Evidence words: Tested (shown in trials), Traditional (gardeners' lore), Same needs (same light/water/soil), Different needs.
F(key, name, summary, uses, compost, good, bad, deters, attracts, prop, breed)"""
FACTS = []
def F(key, name, summary, uses=(), compost=('', ''), good=(), bad=(), deters=(), attracts=(), prop=(), breed=('', (), ''), same_genus=True, kind='plant'):
    FACTS.append({'key': key, 'name': name, 'kind': kind, 'data': {
        'summary': summary,
        'uses': [{'kind': k, 'text': t, 'caution': c} for k, t, c in uses],
        'compost': {'verdict': compost[0], 'why': compost[1]},
        'partners_good': [{'name': n, 'sci': s, 'why': w, 'evidence': e} for n, s, w, e in good],
        'partners_bad': [{'name': n, 'sci': s, 'why': w, 'evidence': e} for n, s, w, e in bad],
        'deters': [{'what': a, 'how': b, 'evidence': e} for a, b, e in deters],
        'attracts': [{'what': a, 'why': b} for a, b in attracts],
        'propagation': [{'method': m, 'when': w, 'how': h} for m, w, h in prop],
        'breeding': {'text': breed[0], 'cross_genera': list(breed[1]), 'patent': breed[2], 'same_genus': same_genus}}})

# shared wording
OX = 'Contains calcium oxalate crystals: chewing it burns the mouth. Keep it away from pets and children, and wear gloves when cutting it.'
TROP_GOOD = [('Aglaonema', 'Aglaonema', 'Same warm, bright-shade light and evenly moist soil, so they share a shelf or a big pot well.', 'Same needs'),
             ('Philodendron', 'Philodendron', 'Same light, water and humidity.', 'Same needs'),
             ('Peace lily', 'Spathiphyllum', 'Same shade and moisture; both like to be grouped for humidity.', 'Same needs')]
SUCC_BAD = [('Ferns, calatheas and peace lilies', 'Nephrolepis', 'They want moist soil and shade; a pot that suits them rots a succulent.', 'Different needs')]
TROP_BAD = [('Cacti and other succulents', 'Opuntia', 'They need full sun and dry soil between waterings, which this plant does not.', 'Different needs')]
COMPOST_TROP = ('Good', 'Soft green leaves rot quickly. The oxalate crystals break down in the pile; wear gloves when chopping it.')
COMPOST_SUCC = ('Fine in small amounts', 'The fleshy leaves are mostly water and can root in the pile. Chop them and let them dry for a few days first.')
AROID_BREED = ('Aroids flower with a spathe; the female part is ready a day before the pollen is shed, so crossing needs two plants flowering a day or two apart, '
               'or stored pollen. Berries take months to ripen, and seedlings of named hybrids vary a lot.')
PATENT_NEW = 'Many newer named varieties are patented (look for "PP" or "PPAF" on the tag). Propagating a patented plant is not allowed while the patent lasts, even for yourself.'

F('dieffenbachia seguine', 'Dieffenbachia seguine', 'A shade-tolerant foliage plant grown for its patterned leaves; it has no safe practical uses.',
  uses=[('Ornamental', 'Bold patterned leaves for low-light rooms.', OX + ' The common name "dumb cane" comes from the swelling it causes.')],
  compost=COMPOST_TROP, good=TROP_GOOD, bad=TROP_BAD,
  prop=[('Stem cuttings', 'Spring to summer', 'Cut a cane into pieces 2 to 3 inches long, each with a node, and lay them half-buried in moist mix. New shoots come from the nodes in 4 to 8 weeks.'),
        ('Top cutting', 'Spring to summer', 'Cut the top 6 inches off a leggy plant and root it in water or moist mix; the old stump sprouts again.')],
  breed=(AROID_BREED + ' Dieffenbachia rarely flowers indoors.', (), PATENT_NEW))

F('ficus carica', 'Ficus carica', 'The edible fig: sweet fruit in summer, and hardy enough to live outdoors in Round Rock.',
  uses=[('Food', 'The fruit is eaten fresh, dried or made into jam. Pick when soft and drooping; figs do not ripen after picking.', ''),
        ('Shade and screening', 'Grows into a large shrub or small tree in the ground.', 'The milky sap and leaves can cause a blistering rash in sunlight (phytophotodermatitis). Wear gloves and long sleeves when pruning.')],
  compost=('Good', 'Leaves break down well; chop the large ones.'),
  good=[('Rosemary', 'Salvia rosmarinus', 'Same full sun and well-drained soil, so they share a dry, sunny bed or large pot.', 'Same needs'),
        ('Comfrey', 'Symphytum', 'Grown under fruit trees as a mulch plant; its deep roots bring up nutrients and its leaves feed the soil.', 'Traditional')],
  bad=[('Lawn grass', 'Cynodon', 'Grass competes for water over the fig\'s shallow roots; keep a mulched circle instead.', 'Tested')],
  attracts=[('Birds', 'Ripe fruit is eaten by mockingbirds and other birds; net it if you want the crop.')],
  prop=[('Hardwood cuttings', 'Late winter (January to February), while dormant', 'Cut pencil-thick pieces 8 to 10 inches long and stand them two-thirds deep in moist mix or garden soil. Most root by spring.'),
        ('Layering', 'Spring', 'Bend a low branch to the ground, nick the bark, and pin it under soil. Cut it free once it has rooted, usually by autumn.')],
  breed=('Common figs set fruit without pollination, and their seeds are not viable. Crossing figs needs the fig wasp, which does not live in Texas, so they cannot be bred at home.', (), 'Some modern named figs are patented; older varieties such as Brown Turkey and Celeste are not.'),
  same_genus=False)

F('vitis mustangensis', 'Vitis mustangensis', 'The mustang grape, a vigorous native vine with very tart fruit, used for jelly and shade.',
  uses=[('Food', 'The grapes make tart jelly, juice and wine once well sweetened.', 'The juice can irritate bare hands; wear gloves when picking and crushing.'),
        ('Shade', 'Covers an arbor or fence in one or two summers.', ''),
        ('Food for wildlife', 'Birds, foxes and raccoons eat the fruit.', '')],
  compost=('Good', 'Leaves and soft prunings compost well. Keep out leaves with mildew or black rot.'),
  good=[('Clover', 'Trifolium', 'A cover of clover between vines adds nitrogen and protects the soil; used in vineyards.', 'Tested'),
        ('Hyssop', 'Hyssopus', 'Said to bring pollinators and deter some pests near grapes.', 'Traditional')],
  bad=[('Small shrubs and trees nearby', '', 'It climbs over and smothers whatever it can reach; give it its own support.', 'Tested')],
  attracts=[('Birds', 'A favorite autumn food for many birds.')],
  prop=[('Hardwood cuttings', 'Late winter', 'Take pieces with three or four buds, plant them with one bud above the soil, and keep them moist. Native grapes root readily.'),
        ('Layering', 'Spring to summer', 'Bury part of a long cane; it roots where it touches the soil.')],
  breed=('Mustang grape crosses with other Vitis species. Breeders have used it for rootstocks that resist drought and the Pierce\'s disease that kills most grapes in Central Texas. Seedlings take 3 or more years to fruit.', (), ''))

F('ipomoea hederacea', 'Ipomoea hederacea', 'An annual morning glory with blue flowers, fast to cover a fence.',
  uses=[('Screening', 'Covers a fence or trellis in one summer.', 'The seeds are toxic if eaten. Keep them away from children and pets.')],
  compost=('Keep it out', 'The hard seeds survive most compost piles and come up wherever the compost goes.'),
  good=[('A fence or trellis', 'Ipomoea', 'Grow it on a support of its own.', 'Same needs')],
  bad=[('Vegetable and flower beds', 'Cucurbitaceae', 'A serious farm weed: it twines over crops and smothers them, and self-sows heavily.', 'Tested')],
  attracts=[('Bees and hummingbirds', 'The morning flowers are visited by bees; hummingbirds visit sometimes.')],
  prop=[('Seed', 'After the last frost (late March in Round Rock)', 'Nick or soak the seeds overnight, then sow half an inch deep where they will grow. They do not like being moved.')],
  breed=('It crosses with other morning glories of the same species group, but it self-pollinates so readily that seed usually comes true.', (), ''))

F('ipomoea batatas', 'Ipomoea batatas', 'The sweet potato; ornamental forms are grown for their leaves and trail from pots.',
  uses=[('Food', 'Ornamental varieties do make edible tubers, but they are small and bland. The young leaves are eaten cooked as greens in many countries.', 'Only eat plants that have not been sprayed with garden chemicals.'),
        ('Ground cover', 'Covers bare ground or spills from pots quickly in summer heat.', '')],
  compost=('Fine in small amounts', 'Stems and roots sprout again in a moist pile; let them dry out first.'),
  good=[('Coleus', 'Plectranthus scutellarioides', 'A classic container partner: same water, and the colors contrast.', 'Same needs'),
        ('Petunia', 'Petunia', 'Same sun and water in a hanging basket or window box.', 'Same needs')],
  prop=[('Stem cuttings', 'Spring to late summer', 'Cuttings root in water in about a week. Keep a few indoors over winter to plant out again in spring.'),
        ('Tubers', 'Spring', 'Store a tuber over winter in a cool dry place, then lay it in moist mix; each sprout ("slip") becomes a plant.')],
  breed=('Sweet potatoes rarely set seed. Breeders cross them by hand in warm climates; seedlings vary a lot.', (), 'Most ornamental sweet potato vines (such as the Sweet Caroline and Illusion series) are patented.'))

F('caesalpinia mexicana', 'Caesalpinia mexicana (Erythrostemon mexicanus)', 'A tough, drought-tolerant flowering shrub with yellow blooms from spring to fall.',
  uses=[('Ornamental', 'Long flowering season in heat and drought.', 'The seeds and pods are toxic if eaten.')],
  compost=('Fine in small amounts', 'Leaves are fine; keep out the seed pods, which can sprout.'),
  good=[('Lantana', 'Lantana', 'Same full sun, heat and little water.', 'Same needs'),
        ('Esperanza', 'Tecoma stans', 'Same needs, and the two flower together all summer.', 'Same needs')],
  bad=SUCC_BAD[:0] + [('Thirsty plants', 'Hibiscus', 'Frequent watering for them makes this shrub weak and leggy.', 'Different needs')],
  attracts=[('Butterflies and bees', 'Nectar from spring to fall.'), ('Hummingbirds', 'Visit the flowers.')],
  prop=[('Seed', 'Spring', 'Nick the hard seed coat or soak overnight, then sow half an inch deep in warm soil.'),
        ('Softwood cuttings', 'Early summer', 'Possible but slow; seed is easier.')],
  breed=('Crosses with other Caesalpinia and Erythrostemon are uncommon. Seed from a single plant is usually much like the parent.', (), ''))

F('bougainvillea', 'Bougainvillea', 'A thorny tropical vine with bright bracts; it flowers best when kept a little dry and pot-bound.',
  uses=[('Ornamental', 'Long seasons of color in full sun.', 'Thorns scratch; the sap irritates some people\'s skin.'),
        ('Barrier hedge', 'Planted where it can live outdoors, the thorny canes make a hedge people and animals avoid.', ''),
        ('Dye', 'The bracts give pink to purple dye for fabric.', '')],
  compost=('Poor', 'Thorny canes break down slowly and are unpleasant to handle. The bracts and leaves are fine.'),
  good=[('Lantana', 'Lantana', 'Same heat, sun and dry soil.', 'Same needs')],
  bad=[('Plants watered often', 'Spathiphyllum', 'Frequent water means leaves instead of flowers.', 'Different needs')],
  deters=[('People and animals', 'The thorns make it a barrier along fences.', 'Tested')],
  attracts=[('Butterflies and hummingbirds', 'Visit the small white flowers inside the bracts.')],
  prop=[('Semi-hardwood cuttings', 'Late spring to summer', 'Take 6-inch pieces, dip in rooting hormone, and keep warm in a covered pot. They root in 4 to 8 weeks.'),
        ('Air layering', 'Summer', 'More reliable than cuttings for some varieties.')],
  breed=('Bougainvillea seldom sets seed, and named colors come from chance seedlings and sports, not home crosses.', (), PATENT_NEW))

F('philodendron', 'Philodendron', 'Easy tropical foliage plants for indoors; climbers and self-heading types.',
  uses=[('Ornamental', 'Tolerates lower light than most houseplants.', OX)],
  compost=COMPOST_TROP,
  good=[('Pothos', 'Epipremnum', 'Same light and water; good on the same shelf or moss pole.', 'Same needs'),
        ('Monstera', 'Monstera', 'Same needs; both climb a moss pole.', 'Same needs'),
        ('Aglaonema', 'Aglaonema', 'Same needs.', 'Same needs')],
  bad=TROP_BAD,
  prop=[('Stem cuttings', 'Spring to summer', 'Cut below a node with an aerial root, root it in water, moss or moist mix. Variegated forms (Pink Princess, Painted Lady) keep their look only if the cutting has the variegation.'),
        ('Division', 'Spring', 'Self-heading types (such as Birkin and Black Cardinal) can be split where they have made new crowns or pups.')],
  breed=(AROID_BREED + ' Philodendrons hybridize readily within the genus, which is how most of the named ones were made.', (), PATENT_NEW))

F('philodendron hederaceum', 'Philodendron hederaceum', 'The heartleaf philodendron, including the velvet "Micans" form: one of the easiest trailing houseplants.',
  uses=[('Ornamental', 'Trails from shelves and baskets or climbs a pole.', OX)],
  compost=COMPOST_TROP, good=TROP_GOOD[:2], bad=TROP_BAD,
  prop=[('Stem cuttings', 'Any time of year indoors', 'Cuttings with one or two nodes root in water in two weeks.')],
  breed=(AROID_BREED + ' It rarely flowers indoors.', (), ''))

F('spathiphyllum', 'Spathiphyllum', 'The peace lily: white flowers in low light, and it droops to tell you it needs water.',
  uses=[('Ornamental', 'Flowers in lower light than almost any other houseplant.', OX),
        ('Air', 'Famous from the NASA clean-air study, but a few plants do not measurably clean a room\'s air; good ventilation does more.', '')],
  compost=COMPOST_TROP,
  good=[('Ferns', 'Nephrolepis', 'Same shade and moist soil; grouped together they raise the humidity.', 'Same needs'),
        ('Calathea', 'Goeppertia', 'Same needs.', 'Same needs')] + TROP_GOOD[:1],
  bad=TROP_BAD,
  prop=[('Division', 'Spring', 'Tip it out of the pot and pull or cut the clump into pieces, each with several leaves and roots.')],
  breed=(AROID_BREED, (), PATENT_NEW))

F('aeonium', 'Aeonium', 'Rosette succulents that grow in cool months and rest in summer heat.',
  uses=[('Ornamental', 'Sculptural rosettes for pots and dry gardens.', '')],
  compost=COMPOST_SUCC,
  good=[('Other succulents', 'Graptosedum', 'Same gritty soil and little water.', 'Same needs'),
        ('Elephant bush', 'Portulacaria', 'Same needs.', 'Same needs')],
  bad=SUCC_BAD,
  prop=[('Rosette cuttings', 'Autumn to early spring (its growing season)', 'Cut a rosette with an inch or two of stem, let it dry for a few days, then set it on dry gritty mix. Water lightly once roots form.')],
  breed=('Aeoniums cross easily with each other; many garden forms are hybrids. Each rosette dies after it flowers (the plant lives on through its branches), so let seed form on a flowering rosette if you want seedlings.', (), ''))

F('opuntia', 'Opuntia', 'Prickly pear: edible pads and fruit, very drought-hardy, and native to Texas in many forms.',
  uses=[('Food', 'Young pads (nopales) and the ripe fruit (tunas) are eaten across Texas and Mexico, cooked or raw, once every spine and glochid is removed.', 'The tiny glochids lodge in skin; handle with tongs and thick gloves, and burn or scrape them off. Be sure of the species before eating it.'),
        ('Dye', 'Cochineal insects that live on prickly pear give carmine red dye, and the fruit gives a pink one.', ''),
        ('Food for wildlife', 'Birds and many mammals eat the fruit.', '')],
  compost=('Keep it out', 'Spines and glochids survive composting and turn up in your hands later.'),
  good=[('Agave', 'Agave', 'Same sun, heat and dry soil.', 'Same needs'),
        ('Texas natives', 'Artemisia', 'Same dry, sunny conditions.', 'Same needs')],
  bad=SUCC_BAD,
  deters=[('People and animals', 'Planted along a boundary, it keeps out deer, dogs and trespassers.', 'Tested')],
  attracts=[('Bees', 'The big spring flowers are worked heavily by native bees.')],
  prop=[('Pad cuttings', 'Late spring to summer', 'Twist off a pad, let the cut end dry for a week, then stand it one-third deep in dry gritty soil. It roots in a few weeks.'),
        ('Seed', 'Spring', 'Slow; pads are much faster.')],
  breed=('Prickly pears hybridize freely, which is why so many are hard to name.', (), ''))

F('aloe vera', 'Aloe vera', 'The medicine-cabinet aloe: soothing gel, easy pups, and very little water.',
  uses=[('Skin and first aid', 'The clear inner gel is a traditional soothing treatment for minor burns, sunburn and dry skin; some studies support it for minor burns.', 'Use only the clear gel. The yellow sap (latex) just under the skin is a strong laxative and irritates skin. Do not eat it. Toxic to dogs and cats.'),
        ('Ornamental', 'Easy in a sunny window or outdoors in a sheltered spot.', '')],
  compost=COMPOST_SUCC,
  good=[('Haworthia', 'Haworthiopsis', 'Same gritty soil and light; good in a shallow bowl together.', 'Same needs'),
        ('Other aloes and succulents', 'Aloe', 'Same needs.', 'Same needs')],
  bad=SUCC_BAD,
  prop=[('Pups (offsets)', 'Spring to summer', 'Pull or cut off a pup with some roots once it is 3 to 4 inches tall, let it dry a day, and pot it in gritty mix. Your three aloes all make pups.'),
        ('Leaf cuttings', 'Not recommended', 'Aloe leaves usually rot instead of rooting.')],
  breed=('Aloe vera is mostly sterile and rarely sets seed. Other aloes cross with each other and with Gasteria, Haworthia and Astroloba (the hybrids are called ×Gasteraloe and similar).', ('Gasteria', 'Haworthia', 'Haworthiopsis', 'Aloiampelos'), ''))

F('aloe', 'Aloe', 'Aloes and aloe hybrids: rosette succulents, mostly from Africa, many with spotted or toothed leaves.',
  uses=[('Ornamental', 'Easy rosettes for sunny windows; many dwarf hybrids flower in winter.', 'Most aloes are toxic to pets if chewed.')],
  compost=COMPOST_SUCC, good=[('Haworthia', 'Haworthiopsis', 'Same gritty soil and bright light.', 'Same needs')], bad=SUCC_BAD,
  prop=[('Pups (offsets)', 'Spring to summer', 'Separate pups with roots and pot them in gritty mix.')],
  breed=('Aloes cross easily with each other and with Gasteria and Haworthia. Dwarf hybrids are often patented or named; their seedlings vary.', ('Gasteria', 'Haworthia', 'Haworthiopsis', 'Aloiampelos'), PATENT_NEW))

F('aloiampelos striatula', 'Aloiampelos striatula', 'A rambling, shrubby aloe hardy to about 10°F, one of the few aloes that lives outdoors all year in Central Texas.',
  uses=[('Ornamental', 'Yellow winter flowers on a sprawling shrub for dry beds.', 'Toxic to pets if chewed, like most aloes.')],
  compost=COMPOST_SUCC,
  good=[('Agave', 'Agave', 'Same dry, sunny bed.', 'Same needs'), ('Prickly pear', 'Opuntia', 'Same needs.', 'Same needs')], bad=SUCC_BAD,
  attracts=[('Hummingbirds', 'Visit the flowers in late winter and spring, when little else is blooming.')],
  prop=[('Stem cuttings', 'Spring to summer', 'Cut a stem 8 to 12 inches long, dry it for a few days, and plant it in gritty soil. It roots easily.')],
  breed=('It was moved from Aloe into its own small genus, but it can still cross with true aloes.', ('Aloe',), ''))

F('haworthiopsis attenuata', 'Haworthiopsis attenuata', 'The zebra plant: a small striped rosette that tolerates less light than most succulents.',
  uses=[('Ornamental', 'Small enough for a windowsill; non-toxic to pets (ASPCA).', '')],
  compost=COMPOST_SUCC,
  good=[('Aloe', 'Aloe', 'Same soil and water; often sold in the same pot.', 'Same needs'), ('Gasteria', 'Gasteria', 'Same needs.', 'Same needs')], bad=SUCC_BAD,
  prop=[('Offsets', 'Spring or autumn', 'Separate offsets with a few roots and pot them in gritty mix.'),
        ('Leaf cuttings', 'Spring', 'Twist off a whole leaf, dry it for a few days, and lay it on dry mix. Slow, but it works.')],
  breed=('Crosses within Haworthiopsis and Haworthia, and with Aloe and Gasteria. Most are self-sterile: you need two different plants flowering together.', ('Haworthia', 'Aloe', 'Gasteria'), ''))

F('ravenea rivularis', 'Ravenea rivularis', 'The majesty palm: a large indoor palm that needs bright light, steady moisture and humidity.',
  uses=[('Ornamental', 'A tall palm for bright rooms or summer patios; non-toxic to pets.', '')],
  compost=('Fine in small amounts', 'Fronds are tough and fibrous; shred them first.'),
  good=[('Ferns', 'Nephrolepis', 'Same moist soil and humidity.', 'Same needs'), ('Peace lily', 'Spathiphyllum', 'Same needs, under the palm.', 'Same needs')],
  bad=TROP_BAD,
  prop=[('Seed', 'Spring and summer, in warmth', 'The only practical way. Sow fresh seed in warm, moist mix; germination takes 1 to 3 months.')],
  breed=('Majesty palms are male or female. Two of your three would need to be one of each and to flower at the same time, which is rare indoors.', (), ''))

F('graptosedum', '×Graptosedum', 'A hybrid of Graptopetalum and Sedum: easy blushing rosettes for sunny pots.',
  uses=[('Ornamental', 'Colors up pink and bronze in full sun and cool weather.', '')],
  compost=COMPOST_SUCC,
  good=[('Aeonium', 'Aeonium', 'Same soil and light.', 'Same needs'), ('Elephant bush', 'Portulacaria', 'Same needs.', 'Same needs')], bad=SUCC_BAD,
  prop=[('Leaf cuttings', 'Spring to autumn', 'Twist off whole leaves, let them callus, and lay them on dry mix; tiny rosettes appear in weeks.'),
        ('Stem cuttings', 'Spring to autumn', 'Cut rosettes with a short stem, dry for a few days, and plant.')],
  breed=('It is already a cross between two genera. Its relatives also cross with Echeveria (making ×Graptoveria).', ('Graptopetalum', 'Sedum', 'Echeveria'), ''))

F('portulacaria afra', 'Portulacaria afra', 'Elephant bush or spekboom: a tough succulent shrub, popular as a bonsai.',
  uses=[('Food', 'In South Africa the sour leaves are eaten raw in salads and stews.', 'Only eat leaves from plants that have not been sprayed.'),
        ('Food for wildlife', 'Browsed by elephants and tortoises in the wild.', ''),
        ('Bonsai', 'Takes pruning well and makes a thick trunk.', '')],
  compost=COMPOST_SUCC,
  good=[('Aeonium', 'Aeonium', 'Same needs.', 'Same needs'), ('Jade plant', 'Crassula', 'Same needs.', 'Same needs')], bad=SUCC_BAD,
  prop=[('Stem cuttings', 'Spring to summer', 'Cut 3 to 4 inch tips, dry for a few days, and plant in gritty mix. Variegated forms root a little more slowly.')],
  breed=('It rarely flowers in pots, so crossing is not practical at home.', (), ''), same_genus=False)

F('ficus lyrata', 'Ficus lyrata', 'The fiddle-leaf fig: big leaves for a bright room, fussy about moves and drafts.',
  uses=[('Ornamental', 'A dramatic indoor tree.', 'The milky sap irritates skin and is mildly toxic to pets.')],
  compost=('Good', 'The leathery leaves break down slowly; shred them.'),
  good=[('Rubber plant', 'Ficus elastica', 'Same bright light and watering.', 'Same needs'), ('Monstera', 'Monstera', 'Same needs.', 'Same needs')],
  bad=TROP_BAD,
  prop=[('Stem cuttings', 'Spring to summer', 'Cut a tip with two or three leaves, let the sap stop, and root it in water or moist mix in warmth.'),
        ('Air layering', 'Spring to summer', 'Roots a branch while still attached; best for a tall stem.')],
  breed=('Like all figs it needs its own wasp to set seed, so it cannot be bred at home.', (), ''), same_genus=False)

F('adenium obesum', 'Adenium obesum', 'The desert rose: a fat-trunked succulent with big flowers, easy from seed.',
  uses=[('Ornamental and bonsai', 'Grown for the swollen trunk (caudex) and long flowering.', 'The sap is very poisonous: it was once used for arrow poison. Wear gloves, wash your hands, and keep it away from pets and children.')],
  compost=('Keep it out', 'The toxic sap is not worth the risk in compost used on food plants.'),
  good=[('Bougainvillea', 'Bougainvillea', 'Same heat, sun and dry soil.', 'Same needs'), ('Other succulents', 'Euphorbia', 'Same needs.', 'Same needs')],
  bad=SUCC_BAD,
  attracts=[('Butterflies', 'Visit the flowers outdoors in summer.')],
  prop=[('Seed', 'Spring to summer', 'Sow fresh seed on the surface of warm mix; seed-grown plants make the fattest trunks.'),
        ('Stem cuttings', 'Summer', 'Root easily but rarely form a big caudex.')],
  breed=('Easy to cross by hand: open a flower, take pollen from inside the tube with a fine brush, and place it on the stigma of another plant\'s flower. Pods take 2 to 3 months, and seedlings vary in color, which is half the fun with your six.', (), ''))

F('rosa', 'Rosa', 'Roses: flowers for cutting and scent; floribundas and minis flower in flushes from spring to fall.',
  uses=[('Cut flowers', 'Cut in the cool morning, just as the buds open.', ''),
        ('Food', 'Petals from unsprayed roses are edible in salads, jellies and syrups; the hips are rich in vitamin C, though modern floribundas make few.', 'Never eat petals from roses treated with systemic insecticides.'),
        ('Rose water and potpourri', 'Fragrant petals are dried or steeped.', '')],
  compost=('Fine in small amounts', 'Petals and leaves are good. Keep out leaves with black spot, and chop thorny canes.'),
  good=[('Garlic and chives', 'Allium', 'Said to deter aphids and black spot; the evidence is weak, but they do no harm.', 'Traditional'),
        ('Lavender', 'Lavandula', 'Brings pollinators and is said to keep aphids off.', 'Traditional'),
        ('Marigolds', 'Tagetes', 'Bring hoverflies, whose larvae eat aphids.', 'Traditional')],
  bad=[('Shading neighbors', '', 'Roses need at least six hours of sun to flower and resist disease.', 'Different needs')],
  attracts=[('Bees', 'Open, single flowers feed bees more than full doubles.')],
  prop=[('Softwood cuttings', 'Late spring to early summer', 'Take 6-inch pieces from a stem that just flowered, dip in rooting hormone, and keep them covered and moist. About half root in 4 to 8 weeks.'),
        ('Layering', 'Spring', 'Pin a low cane into the soil.')],
  breed=('Roses are easy to cross by hand: remove the petals and stamens of a flower before it opens, brush on pollen from another rose, and label it. Hips ripen in autumn; seeds need about 6 weeks in the fridge before they sprout, and every seedling is new.', (),
         'Queen of Elegance (WEKjucstokol) is a patented Weeks rose: propagating it by cuttings is not allowed while the patent lasts. Seedlings from it are yours.'))

F('cosmos', 'Cosmos', 'Easy annual flowers that self-sow and bring beneficial insects to the garden.',
  uses=[('Cut flowers', 'Long stems for vases; picking keeps them flowering.', ''),
        ('Dye', 'Orange Cosmos sulphureus flowers give strong yellow and orange dyes.', ''),
        ('Pest control', 'A favorite insectary plant: it feeds the lacewings, hoverflies and parasitic wasps that eat aphids and caterpillars.', '')],
  compost=('Good', 'Soft stems and leaves rot fast. Seed heads will sprout where the compost goes.'),
  good=[('Tomatoes and squash', 'Cucurbitaceae', 'Brings the beneficial insects and pollinators that vegetables need.', 'Tested'),
        ('Zinnias', 'Zinnia', 'Same sun and lean soil.', 'Same needs')],
  bad=[('Rich, heavily fed beds', '', 'Rich soil makes cosmos tall and floppy with few flowers.', 'Different needs')],
  attracts=[('Bees, butterflies and beneficial insects', 'Open flowers are easy for many insects to use.'), ('Goldfinches', 'Eat the seeds in autumn.')],
  prop=[('Seed', 'Spring to midsummer', 'Scatter seed on bare soil and rake it in lightly. Yours are volunteers, so they will keep self-sowing.')],
  breed=('The two common species (C. bipinnatus and C. sulphureus) do not cross with each other, but each crosses freely within its species, so volunteers drift in color.', (), ''))

F('nephrolepis exaltata', 'Nephrolepis exaltata', 'The Boston fern: lush fronds for humid, bright shade; safe for pets.',
  uses=[('Ornamental', 'Hanging baskets and shady porches; non-toxic to pets (ASPCA).', '')],
  compost=('Good', 'Fronds rot down well.'),
  good=[('Peace lily', 'Spathiphyllum', 'Same shade and moisture.', 'Same needs'), ('Calathea', 'Goeppertia', 'Same humidity.', 'Same needs')],
  bad=[('Succulents', 'Aloe', 'They want dry soil and full sun.', 'Different needs')],
  prop=[('Runners', 'Spring to summer', 'Pin a runner\'s tip onto moist mix in a small pot; cut it free once it has roots and fronds.'),
        ('Division', 'Spring', 'Cut the clump into pieces with roots and fronds.')],
  breed=('Ferns reproduce from spores, not flowers. Most Boston fern varieties, including Emina, are sterile sports and do not make good spores, so they are grown from runners.', (), ''))

F('begonia', 'Begonia', 'A huge genus of foliage and flowering plants for bright shade and humidity.',
  uses=[('Ornamental', 'Patterned leaves and long flowering in shade.', 'The roots and tubers are toxic to dogs and cats (oxalates).')],
  compost=COMPOST_TROP,
  good=[('Coleus', 'Plectranthus scutellarioides', 'Same shade and moisture.', 'Same needs'), ('Ferns', 'Nephrolepis', 'Same humidity.', 'Same needs')],
  bad=[('Succulents', 'Aloe', 'They need sun and dry soil.', 'Different needs')],
  prop=[('Leaf and stem cuttings', 'Spring to summer', 'Cane and rex types root from stem tips, and many from a leaf laid on moist mix with its veins nicked.'),
        ('Division', 'Spring', 'Rhizomatous types split easily.')],
  breed=('Begonias are one of the easiest plants to cross by hand: plants have separate male and female flowers. The dust-fine seed is sown on the surface.', (), PATENT_NEW + ' Leafjoy begonias such as Obsidian are sold as patented or patent-pending.'))

F('plectranthus scutellarioides', 'Plectranthus scutellarioides', 'Coleus: bright leaves for shade or sun, and the easiest plant to root.',
  uses=[('Ornamental', 'Leaf color all summer.', 'Mildly toxic to pets (ASPCA).')],
  compost=('Good', 'Soft stems rot fast; pieces may root in a wet pile.'),
  good=[('Sweet potato vine', 'Ipomoea batatas', 'A classic container pair.', 'Same needs'), ('Begonia', 'Begonia', 'Same shade.', 'Same needs')],
  attracts=[('Bees', 'If you let it flower, bees visit the blue spikes (pinch them off to keep the leaves at their best).')],
  prop=[('Stem cuttings', 'Any time it is growing', 'Cuttings root in a glass of water in about a week. Take some in autumn to keep over winter indoors.')],
  breed=('Seed from named varieties does not come true; seedlings are a mix of colors.', (), PATENT_NEW))

F('aglaonema', 'Aglaonema', 'Chinese evergreens: tough, colorful leaves for low light.',
  uses=[('Ornamental', 'One of the best plants for dim rooms.', OX)],
  compost=COMPOST_TROP, good=[('Dieffenbachia', 'Dieffenbachia', 'Same needs.', 'Same needs'), ('Philodendron', 'Philodendron', 'Same needs.', 'Same needs')], bad=TROP_BAD,
  prop=[('Division', 'Spring', 'Separate the shoots at the base, each with roots.'), ('Stem cuttings', 'Spring to summer', 'Root in water or moist mix.')],
  breed=(AROID_BREED + ' The red and pink varieties were bred this way in Thailand and Indonesia.', (), PATENT_NEW))

F('goeppertia', 'Goeppertia', 'Calatheas (now Goeppertia): patterned leaves that fold up at night; safe for pets.',
  uses=[('Ornamental', 'Striking patterns; non-toxic to pets (ASPCA).', '')],
  compost=('Good', 'Leaves rot down well.'),
  good=[('Ferns', 'Nephrolepis', 'Same humidity and moisture.', 'Same needs'), ('Peace lily', 'Spathiphyllum', 'Same needs.', 'Same needs')],
  bad=[('Succulents', 'Aloe', 'They need dry soil and sun.', 'Different needs')],
  prop=[('Division', 'Spring', 'The only practical way: split the clump into pieces, each with roots and several leaves, and keep them warm and humid while they settle.')],
  breed=('Calatheas rarely flower or set seed indoors.', (), ''), same_genus=False)

F('phalaenopsis', 'Phalaenopsis', 'Moth orchids: months of flowers in a bright window; safe for pets.',
  uses=[('Ornamental', 'Flower spikes last 2 to 3 months; non-toxic to pets (ASPCA).', '')],
  compost=('Good', 'Old bark potting mix is a good addition to compost or mulch.'),
  good=[('Vanilla orchid', 'Vanilla', 'Same warmth, light and humidity.', 'Same needs'), ('Ferns', 'Nephrolepis', 'Raise the humidity around it.', 'Same needs')],
  bad=[('Cacti', 'Opuntia', 'Need far more sun and drier air.', 'Different needs')],
  prop=[('Keikis', 'Whenever they appear', 'A baby plant may grow on a flower spike; cut it off once it has 2 or 3 roots an inch or two long.')],
  breed=('Orchids are crossed by moving the pollen packet (pollinia) with a toothpick onto another flower. The seeds are dust and need sterile lab flasks to sprout, so home breeding usually means sending pods to a lab.', ('Doritis',), ''))

F('zamioculcas zamiifolia', 'Zamioculcas zamiifolia', 'The ZZ plant: survives low light and missed waterings, stores water in its roots.',
  uses=[('Ornamental', 'Nearly indestructible in dim offices and rooms.', OX)],
  compost=COMPOST_TROP,
  good=[('Snake plant', 'Dracaena', 'Same low light and infrequent watering.', 'Same needs')],
  bad=[('Plants watered often', 'Nephrolepis', 'The water they need would rot its rhizomes.', 'Different needs')],
  prop=[('Division', 'Spring', 'Separate the potato-like rhizomes with stems attached.'),
        ('Leaf cuttings', 'Spring to summer', 'Single leaflets pushed into moist mix make a tiny rhizome in a few months; be patient.')],
  breed=('ZZ rarely flowers indoors, and is the only species in its genus.', (), ''), same_genus=False)

F('euphorbia milii', 'Euphorbia milii', 'Crown of thorns: flowers almost all year in sun, and its thorny stems make a barrier.',
  uses=[('Ornamental', 'Flowers for most of the year in bright light.', 'The milky sap irritates skin and eyes and is toxic if eaten; wear gloves and eye protection when pruning.'),
        ('Barrier', 'Grown as a thorny hedge where it can live outdoors.', ''),
        ('Snail control (research)', 'Its sap kills water snails and has been studied as a cheap way to fight snail-borne disease.', 'Not something to try at home.')],
  compost=('Fine in small amounts', 'Let pieces dry first; handle with gloves because of the sap.'),
  good=[('Other succulents', 'Adenium', 'Same sun and dry soil.', 'Same needs')], bad=SUCC_BAD,
  deters=[('Pets and animals', 'The thorns keep them away.', 'Tested')],
  prop=[('Stem cuttings', 'Spring to summer', 'Cut 3 to 4 inch tips, rinse the sap off in water, dry for several days, then plant in gritty mix.')],
  breed=('Thai growers make many hybrids by hand-crossing the tiny flowers; seed is ready in about a month.', (), PATENT_NEW))

F('gymnocalycium mihanovichii', 'Gymnocalycium mihanovichii', 'Moon cactus: a colorful mutant with no green, grafted onto a green cactus that feeds it.',
  uses=[('Ornamental', 'A bright novelty for a sunny windowsill.', '')],
  compost=('Keep it out', 'Spines persist in compost.'),
  good=[('Other cacti', 'Myrtillocactus', 'Same light and soil.', 'Same needs')], bad=SUCC_BAD,
  prop=[('Grafting', 'Spring to summer', 'The colored top cannot live on its own roots. Pups that form on it can be cut off and grafted onto a fresh green cactus (Hylocereus or similar), cut faces pressed together and held with rubber bands for two weeks.')],
  breed=('The red form cannot make food, so it lives only by grafting. Green Gymnocalycium cross readily, but need two genetically different plants.', (), ''))

F('agave', 'Agave', 'Tough rosette succulents for dry, sunny beds; most flower once after many years and then die.',
  uses=[('Fiber', 'Several species give strong fiber (sisal and others) from the leaves.', ''),
        ('Food', 'Some species are cooked for food or sweet sap (the source of agave syrup and mezcal).', 'The raw sap causes a painful rash in many people; wear gloves and long sleeves. Know the species before using it.'),
        ('Landscaping', 'Dramatic and drought-proof in the ground.', 'The leaf tips are sharp: keep it away from paths.')],
  compost=('Keep it out', 'The fibrous leaves barely break down, and the spines and sap are hazards.'),
  good=[('Prickly pear', 'Opuntia', 'Same dry, sunny ground.', 'Same needs'), ('Hardy aloe', 'Aloiampelos', 'Same needs.', 'Same needs')], bad=SUCC_BAD,
  deters=[('People and animals', 'The spined leaves form a barrier.', 'Tested')],
  attracts=[('Hummingbirds, bats and bees', 'The huge flower stalk feeds them when it finally blooms.')],
  prop=[('Pups', 'Spring to summer', 'Dig up the offsets around the base and replant them; let the cut root dry first.'),
        ('Bulbils', 'After flowering', 'Some species make small plants on the flower stalk.')],
  breed=('Agaves cross readily, and with Manfreda (making ×Mangave). Because most flower once and die, crossing usually means catching a neighbor\'s plant in bloom.', ('Manfreda',), PATENT_NEW))

F('myrtillocactus geometrizans', 'Myrtillocactus geometrizans', 'The bilberry cactus; the "Fukurokuryuzinboku" form has odd, bulging rib patterns.',
  uses=[('Food', 'The small purple fruits (garambullos) are eaten fresh or dried in Mexico.', 'Indoor plants and this cultivar rarely flower.'),
        ('Ornamental', 'A sculptural cactus for a sunny window.', '')],
  compost=('Keep it out', 'Spines persist.'),
  good=[('Other cacti', 'Gymnocalycium', 'Same needs.', 'Same needs')], bad=SUCC_BAD,
  prop=[('Stem cuttings', 'Spring to summer', 'Cut a branch, let it dry for one to two weeks, and plant in dry gritty mix.'),
        ('As a rootstock', 'Spring', 'Its green stems are a common grafting base for other cacti.')],
  breed=('Rarely flowers in pots, so crossing is unlikely at home.', (), ''), same_genus=False)

F('vanilla planifolia', 'Vanilla planifolia', 'The vanilla orchid: a climbing vine that makes real vanilla beans once it is big enough to flower.',
  uses=[('Food', 'The cured seed pods are vanilla beans. A vine usually needs to be several years old and 10 feet or more of stem before it flowers.', 'Fresh green pods have no flavor; they must be cured for months.')],
  compost=('Good', 'Soft stems rot well.'),
  good=[('Moth orchid', 'Phalaenopsis', 'Same warmth and humidity.', 'Same needs'), ('A moss pole', 'Philodendron', 'It climbs like a philodendron and grows best on a support.', 'Same needs')],
  bad=TROP_BAD,
  prop=[('Stem cuttings', 'Spring to summer', 'Cut a piece with at least 3 nodes, lay the bottom nodes on moist moss or bark, and keep it warm and humid. Aerial roots appear in weeks.')],
  breed=('Every flower must be hand-pollinated within the few hours it is open: lift the flap (rostellum) with a toothpick and press the pollen onto the stigma. That is also how you get beans. Pods ripen in about 9 months.', (), ''))

F('tradescantia', 'Tradescantia', 'Spiderworts and wandering dudes: fast trailing plants that root from every piece.',
  uses=[('Ground cover and baskets', 'Fills pots and shady beds fast.', 'The sap gives some people and dogs an itchy rash.')],
  compost=('Poor', 'Every stem piece can root and spread from the compost; dry it out completely first.'),
  good=[('Coleus', 'Plectranthus scutellarioides', 'Same needs in shady pots.', 'Same needs')],
  bad=[('Bearded iris', 'Iris', 'It creeps over iris rhizomes, which need sun on their tops to flower.', 'Different needs')],
  prop=[('Stem cuttings', 'Any time it is growing', 'Pieces root in water in days. Pinch the tips to keep it bushy.')],
  breed=('Spiderworts cross readily within the genus.', (), ''))

F('tradescantia pallida', 'Tradescantia pallida', 'Purple heart: a tough purple ground cover, hardy in Round Rock (it dies back in frost and returns).',
  uses=[('Ground cover', 'Purple color in hot, dry spots where little else grows.', 'The sap can cause an itchy rash on skin and in dogs.'),
        ('Pollution monitoring (research)', 'Its flower cells show damage from air pollution, so it is used in a standard test of air quality (the Tradescantia micronucleus test).', '')],
  compost=('Poor', 'Stem pieces root and spread from compost; dry it out completely first.'),
  good=[('Zexmenia', 'Wedelia', 'Same heat and drought.', 'Same needs'), ('Lantana', 'Lantana', 'Same needs; the colors contrast.', 'Same needs')],
  bad=[('Bearded iris', 'Iris', 'It creeps over iris rhizomes, which need sun on their tops to flower.', 'Different needs')],
  attracts=[('Bees', 'Small pink flowers in summer.')],
  prop=[('Stem cuttings', 'Spring to autumn', 'Any piece roots in water or soil within days.')],
  breed=('Crosses within Tradescantia; it is rarely grown from seed.', (), ''))

F('syngonium', 'Syngonium', 'Arrowhead plants: easy trailing aroids whose leaves change shape as they climb.',
  uses=[('Ornamental', 'Colorful leaves for medium light.', OX)],
  compost=COMPOST_TROP, good=TROP_GOOD, bad=TROP_BAD,
  prop=[('Stem cuttings', 'Any time it is growing', 'Cuttings with a node root in water in one to two weeks.')],
  breed=(AROID_BREED + ' It seldom flowers indoors.', (), PATENT_NEW))

F('monstera deliciosa', 'Monstera deliciosa', 'The Swiss cheese plant: split leaves, aerial roots, and, outdoors in the tropics, an edible fruit.',
  uses=[('Ornamental', 'A large climber for bright indoor light.', OX),
        ('Food', 'The fruit is eaten in the tropics once fully ripe, when its scales lift off by themselves; it tastes like pineapple and banana. Indoor plants almost never fruit.', 'Unripe fruit is full of the irritating oxalate crystals.'),
        ('Crafts', 'The long aerial roots have been used for rope and baskets.', '')],
  compost=COMPOST_TROP,
  good=[('Philodendron', 'Philodendron', 'Same needs; both climb a moss pole.', 'Same needs'), ('Fiddle-leaf fig', 'Ficus lyrata', 'Same bright light.', 'Same needs')],
  bad=TROP_BAD,
  prop=[('Stem cuttings', 'Spring to summer', 'Each cutting needs a node, ideally with an aerial root; a leaf alone never grows a new plant. Root in water or moss.'),
        ('Air layering', 'Spring to summer', 'Wrap moist moss around a node on the plant; cut below it once roots fill the moss.')],
  breed=(AROID_BREED + ' Indoor monsteras rarely flower.', (), 'Thai Constellation and some other variegated forms are patented or tissue-culture only.'))

F('gardenia jasminoides', 'Gardenia jasminoides', 'Gardenia: heavily scented white flowers in early summer; wants acid soil.',
  uses=[('Fragrance', 'Flowers for vases and scent.', 'Mildly toxic to pets (ASPCA).'),
        ('Dye', 'The orange fruit is a traditional yellow dye in East Asia, for fabric and food.', '')],
  compost=('Good', 'Leaves compost well.'),
  good=[('Azaleas and camellias', 'Camellia', 'Same acid soil and light shade.', 'Same needs')],
  bad=[('Plants that need lime', 'Iris', 'Alkaline soil turns gardenia leaves yellow; Round Rock\'s soil and tap water are already alkaline.', 'Different needs')],
  attracts=[('Moths', 'The night scent draws moths.')],
  prop=[('Softwood cuttings', 'Late spring to early summer', 'Take 4 to 5 inch tips, use rooting hormone, and keep them warm and covered in acid mix (peat or bark).')],
  breed=('Gardenias can be crossed by hand but rarely set seed in pots.', (), PATENT_NEW))

F('cucurbitaceae', 'Cucurbitaceae (gourd family)', 'The gourd family: melons, squash, cucumbers and gourds. Yours is not identified to species yet.',
  uses=[('Food', 'Melons, squash and cucumbers are edible.', 'Do not eat a fruit that tastes bitter: bitter gourd-family fruit can contain cucurbitacins that cause severe illness. Ornamental gourds are not for eating.'),
        ('Crafts', 'Hard-shelled gourds dry into bowls, birdhouses and rattles.', '')],
  compost=('Good', 'Vines and leaves compost well. Leave out leaves with powdery mildew.'),
  good=[('Corn and beans', 'Zea', 'The "Three Sisters": corn gives support, beans add nitrogen, squash shades out weeds.', 'Traditional'),
        ('Nasturtium', 'Tropaeolum', 'Said to deter squash bugs.', 'Traditional'),
        ('Bee balm', 'Monarda', 'Brings in the bees that pollinate the flowers.', 'Traditional')],
  bad=[('Potatoes', 'Solanum', 'Compete for space and share some diseases.', 'Traditional')],
  attracts=[('Bees', 'Needed to pollinate the female flowers.')],
  prop=[('Seed', 'After the soil warms (April to June)', 'Sow 1 inch deep where it will grow; it dislikes transplanting.')],
  breed=('Plants of the same species cross freely through bees, so saved seed may not come true if other squash or gourds of that species grow nearby. Hand-pollinate and tape the flowers shut to keep a line pure.', (), ''))

F('pennisetum advena', 'Pennisetum advena (Cenchrus advena)', "Purple fountain grass: burgundy leaves and plumes; 'Rubrum' is sterile, so it does not spread like its weedy relative.",
  uses=[('Ornamental', 'Summer color and movement.', ''), ('Dried arrangements', 'The plumes dry well.', '')],
  compost=('Good', 'Chop the grass blades; no viable seed.'),
  good=[('Lantana', 'Lantana', 'Same sun and heat.', 'Same needs'), ('Celosia', 'Celosia', 'Same needs; good together in pots.', 'Same needs')],
  prop=[('Division', 'Spring', 'Split the clump with a sharp spade. It is not hardy in hard freezes, so keep a division indoors over winter.')],
  breed=("'Rubrum' is sterile and does not set seed.", (), ''), same_genus=False)

F('alocasia', 'Alocasia', 'Elephant ears: dramatic leaves that need warmth, bright light and humidity.',
  uses=[('Ornamental', 'Bold foliage.', OX + ' Alocasias are more irritating than most aroids.')],
  compost=COMPOST_TROP, good=TROP_GOOD, bad=TROP_BAD,
  prop=[('Corms', 'Spring to summer', 'Small corms form around the base. Peel and set them half-buried in moist moss or mix in warmth; they sprout in weeks.'),
        ('Division', 'Spring', 'Separate offsets with roots.')],
  breed=(AROID_BREED + ' Many named alocasias are hybrids.', (), PATENT_NEW))

F('celosia', 'Celosia', 'Cockscomb and plume celosia: long-lasting summer color, good for drying.',
  uses=[('Cut and dried flowers', 'Plumes and combs dry well and keep their color.', ''),
        ('Food', 'Young leaves of Celosia argentea are eaten as a cooked green in West Africa and Asia (Lagos spinach).', 'Only eat plants that have not been sprayed.')],
  compost=('Good', 'Soft annual stems compost well; seed heads may sprout.'),
  good=[('Zinnias and marigolds', 'Zinnia', 'Same sun and heat.', 'Same needs'), ('Purple fountain grass', 'Pennisetum', 'Same needs.', 'Same needs')],
  attracts=[('Bees and butterflies', 'Feed on the flowers.')],
  prop=[('Seed', 'Spring after frost', 'Sow on the surface in warmth. Save seed from dried heads in autumn.')],
  breed=('Kelos and Glorious are F1 series: seed you save will not look like the parents. Plume and crested forms cross with each other.', (), ''))

F('pachira aquatica', 'Pachira aquatica', 'The money tree: an easy indoor tree, often sold with braided trunks; safe for pets.',
  uses=[('Ornamental', 'Easy in bright, indirect light; non-toxic to pets (ASPCA).', ''),
        ('Food', 'In its native wetlands the large seeds are roasted and eaten (the Guiana chestnut). Indoor trees rarely flower.', 'Eat only roasted seeds; raw seeds are not advised.')],
  compost=('Good', 'Leaves compost well.'),
  good=[('Fiddle-leaf fig', 'Ficus lyrata', 'Same light and watering.', 'Same needs')], bad=TROP_BAD,
  prop=[('Stem cuttings', 'Spring to summer', 'Root 6-inch tips in water or moist mix. Cuttings grow as normal stems; braiding uses several young trunks.')],
  breed=('It rarely flowers indoors.', (), ''), same_genus=False)

F('iris germanica', 'Iris germanica', 'The bearded iris: spring flowers from rhizomes, hardy and drought-tolerant once settled.',
  uses=[('Cut flowers', 'Spring flowers for the vase.', ''),
        ('Perfume', 'Dried, aged rhizomes become orris root, a fixative in perfumes and potpourri.', 'The rhizomes are toxic if eaten and can irritate skin.')],
  compost=('Fine in small amounts', 'Leaves are fine. Rhizome pieces resprout; chop and dry them first.'),
  good=[('Salvias', 'Salvia', 'Same sun and drainage.', 'Same needs')],
  bad=[('Ground covers and mulch over the rhizomes', 'Tradescantia', 'The rhizomes need sun on their tops; covering them stops flowering and invites rot.', 'Different needs')],
  deters=[('Deer', 'Deer usually leave irises alone.', 'Traditional')],
  attracts=[('Bees', 'Bumblebees work the flowers.')],
  prop=[('Division', 'Late summer (August to September)', 'Lift the clump every 3 to 4 years, cut healthy rhizomes with a fan of leaves, trim the leaves to 6 inches, and replant with the tops showing.')],
  breed=('Easy to cross: move pollen from one flower\'s anthers onto the stigma lip of another. Seeds take about 2 years to flower, and every seedling is new; this is how most named irises were made.', (), 'Some recent iris introductions are patented; most are not.'))

F('ficus elastica', 'Ficus elastica', 'The rubber plant: glossy leaves on a tough indoor tree.',
  uses=[('Ornamental', 'A forgiving indoor tree.', 'The milky sap irritates skin and is mildly toxic to pets.'),
        ('History', 'Its latex was an early source of rubber, before the Pará rubber tree took over.', '')],
  compost=('Good', 'Shred the thick leaves.'),
  good=[('Fiddle-leaf fig', 'Ficus lyrata', 'Same light and water.', 'Same needs')], bad=TROP_BAD,
  prop=[('Stem cuttings', 'Spring to summer', 'Let the sap stop, then root tips in water or moist mix in warmth.'),
        ('Air layering', 'Spring to summer', 'The surest way for a tall plant.')],
  breed=('Like all figs it needs its own wasp to set seed, so it cannot be bred at home.', (), ''), same_genus=False)

F('petunia', 'Petunia', 'Petunias: summer color in pots and beds; Ray Black is a near-black variety.',
  uses=[('Ornamental', 'Flowers from spring to fall; safe for pets (ASPCA).', '')],
  compost=('Good', 'Soft stems compost well.'),
  good=[('Tomatoes and beans', 'Solanum', 'Petunias are said to deter aphids, tomato hornworms and asparagus beetles.', 'Traditional'),
        ('Sweet potato vine', 'Ipomoea batatas', 'A classic basket pair.', 'Same needs')],
  deters=[('Aphids and some beetles', 'Sticky hairs trap small insects.', 'Traditional')],
  attracts=[('Hummingbirds and moths', 'Visit the trumpet flowers.')],
  prop=[('Stem cuttings', 'Spring to summer', 'Tips root in a week or two.')],
  breed=('Garden petunias are hybrids; seed from them gives a mix. Crossing by hand is easy.', (), PATENT_NEW + ' Ray Black is a patented series.'))

F('artemisia ludoviciana', 'Artemisia ludoviciana', 'Prairie sage or white sagebrush: a silver, aromatic Texas native. (The "white sage" of smudge sticks is usually Salvia apiana, a different plant.)',
  uses=[('Ceremonial and aromatic', 'Bundles are burned for smudging in many Native American traditions, and it is used in dried arrangements and wreaths.', ''),
        ('Ground cover', 'Spreads into a silver mat in dry, sunny spots.', 'It spreads aggressively by underground runners; edge it or grow it in a pot.')],
  compost=('Fine in small amounts', 'Its aromatic oils slow the growth of some seedlings; let it break down fully before using that compost on seed beds.'),
  good=[('Zexmenia', 'Wedelia', 'Same dry, sunny ground.', 'Same needs'), ('Prickly pear', 'Opuntia', 'Same needs.', 'Same needs')],
  bad=[('Small plants it can overrun', 'Celosia', 'Its runners crowd them out.', 'Tested')],
  deters=[('Deer and rabbits', 'The strong smell makes it unappealing to browsers.', 'Traditional'),
          ('Moths in stored clothes', 'Dried bundles are a traditional moth repellent.', 'Traditional')],
  prop=[('Division', 'Spring', 'Dig up rooted pieces of runner and replant.'), ('Stem cuttings', 'Spring', 'Root easily.')],
  breed=('It spreads mostly by runners; crossing is rarely done.', (), ''))

F('monarda fistulosa', 'Monarda fistulosa', 'Wild bergamot: a native mint with lavender flowers that feed bees and hummingbirds.',
  uses=[('Tea and herbs', 'The leaves make a minty, oregano-like tea and seasoning; they are rich in thymol.', 'Use small amounts; avoid in pregnancy.'),
        ('Skin and first aid', 'Leaves were used by many Native American nations on wounds and skin infections, thanks to the antiseptic thymol.', 'A traditional use, not medical advice.')],
  compost=('Good', 'Leaves compost well; leave out mildewed ones.'),
  good=[('Tomatoes and squash', 'Cucurbitaceae', 'Brings bees to the vegetable garden.', 'Traditional'), ('Coneflowers', 'Echinacea', 'Same native prairie conditions.', 'Same needs')],
  deters=[('Deer', 'The strong scent puts deer off.', 'Traditional')],
  attracts=[('Bees, butterflies and hummingbirds', 'One of the best native nectar plants.')],
  prop=[('Division', 'Spring', 'Split clumps every 2 to 3 years to keep them vigorous.'), ('Seed', 'Autumn or early spring', 'Surface-sow; it needs light to sprout.'),
        ('Stem cuttings', 'Spring', 'Root easily.')],
  breed=('Crosses with other Monarda species; garden bee balms are mostly hybrids.', (), ''))

F('wedelia acapulcensis', 'Wedelia acapulcensis var. hispida (zexmenia)', 'Zexmenia: a tough, drought-proof Texas native with orange-yellow daisies from spring to fall.',
  uses=[('Ground cover', 'Covers hot, dry spots with flowers and no watering once settled.', '')],
  compost=('Good', 'Soft stems compost well.'),
  good=[('Purple heart', 'Tradescantia pallida', 'Same heat and drought.', 'Same needs'), ('Prairie sage', 'Artemisia', 'Same needs.', 'Same needs')],
  bad=[('Thirsty plants', 'Spathiphyllum', 'Extra water makes it floppy and short-lived.', 'Different needs')],
  deters=[('Deer', 'Deer seldom eat it.', 'Traditional')],
  attracts=[('Butterflies', 'A favorite nectar plant.'), ('Birds', 'Eat the seeds.')],
  prop=[('Seed', 'Spring', 'Sow fresh seed; it self-sows lightly.'), ('Softwood cuttings', 'Late spring', 'Root fairly easily.')],
  breed=('Rarely bred; seed from one plant is much like it.', (), ''))

F('hibiscus coccineus', 'Hibiscus coccineus', 'Texas star hibiscus: a tall native of wet ground with brilliant red, star-shaped flowers; it dies back in winter and returns.',
  uses=[('Ornamental', 'Big red flowers through summer, by ponds and in rain gardens.', '')],
  compost=('Good', 'Stems are woody by autumn; chop them.'),
  good=[('Other moist-soil natives', 'Lobelia', 'Same wet, sunny ground.', 'Same needs')],
  bad=[('Dry-garden plants', 'Agave', 'It needs far more water than they want.', 'Different needs')],
  attracts=[('Hummingbirds and butterflies', 'The red flowers are made for hummingbirds.')],
  prop=[('Seed', 'Spring', 'Nick the seed coat and sow in warm soil; it flowers in its second year.'), ('Stem cuttings', 'Late spring to summer', 'Root easily in moist mix.')],
  breed=('Crosses with the other hardy hibiscus (H. moscheutos and H. laevis); some large-flowered garden hybrids come from these crosses.', (), PATENT_NEW))

# plants whose scientific name does not say which facts are theirs
LINKS = {'P-080': 'aloe'}
